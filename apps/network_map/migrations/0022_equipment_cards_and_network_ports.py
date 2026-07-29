import django.db.models.deletion
from django.db import migrations, models


def migrate_uniform_olt_cards(apps, schema_editor):
    Equipment = apps.get_model("network_map", "ContainerEquipment")
    Card = apps.get_model("network_map", "ContainerEquipmentCard")
    Port = apps.get_model("network_map", "ContainerEquipmentPort")
    for equipment in Equipment.objects.filter(equipment_type="olt"):
        for slot in range(1, equipment.card_count + 1):
            card = Card.objects.create(
                equipment=equipment,
                slot=slot,
                name=f"Placa {slot}",
                pon_count=equipment.pons_per_card or 8,
            )
            Port.objects.filter(equipment=equipment, card_number=slot).update(card=card)


class Migration(migrations.Migration):
    dependencies = [("network_map", "0021_container_equipment_ports")]
    operations = [
        migrations.CreateModel(
            name="ContainerEquipmentCard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("slot", models.PositiveSmallIntegerField()),
                ("name", models.CharField(blank=True, max_length=100)),
                ("model", models.CharField(blank=True, max_length=120)),
                ("serial_number", models.CharField(blank=True, max_length=120)),
                ("pon_count", models.PositiveSmallIntegerField(default=8)),
                ("enabled", models.BooleanField(default=True)),
                ("equipment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cards", to="network_map.containerequipment")),
            ],
            options={"ordering": ["equipment", "slot"]},
        ),
        migrations.AddConstraint(
            model_name="containerequipmentcard",
            constraint=models.UniqueConstraint(fields=("equipment", "slot"), name="unique_card_slot_per_container_equipment"),
        ),
        migrations.AddField(
            model_name="containerequipmentport",
            name="card",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="ports", to="network_map.containerequipmentcard"),
        ),
        migrations.AlterField(
            model_name="containerequipmentport",
            name="port_type",
            field=models.CharField(
                choices=[
                    ("pon", "PON"), ("dio", "Porta de DIO"), ("rj45_100m", "RJ45 100 Mb"),
                    ("rj45_1g", "RJ45 1 Gb"), ("sfp_1g", "SFP 1 Gb"),
                    ("sfp_plus_10g", "SFP+ 10 Gb"), ("wireless", "Interface wireless"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="containerportlink",
            name="link_type",
            field=models.CharField(
                choices=[("fiber", "Fibra óptica"), ("copper", "Cabo de rede"), ("wireless", "Enlace wireless")],
                default="fiber",
                max_length=20,
            ),
        ),
        migrations.RunPython(migrate_uniform_olt_cards, migrations.RunPython.noop),
    ]
