from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("network_map", "0020_container_equipment"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContainerEquipmentPort",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("port_type", models.CharField(choices=[("pon", "PON"), ("dio", "Porta de DIO"), ("network", "Porta de rede")], max_length=20)),
                ("number", models.PositiveSmallIntegerField()),
                ("card_number", models.PositiveSmallIntegerField(default=0)),
                ("port_number", models.PositiveSmallIntegerField(default=0)),
                ("label", models.CharField(max_length=100)),
                ("enabled", models.BooleanField(default=True)),
                ("equipment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ports", to="network_map.containerequipment")),
            ],
            options={"ordering": ["equipment", "number"]},
        ),
        migrations.AddConstraint(
            model_name="containerequipmentport",
            constraint=models.UniqueConstraint(fields=("equipment", "number"), name="unique_port_number_per_container_equipment"),
        ),
        migrations.CreateModel(
            name="ContainerPortLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("notes", models.CharField(blank=True, max_length=180)),
                ("cable", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="container_port_links", to="network_map.fibercable")),
                ("container", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="internal_port_links", to="network_map.networkelement")),
                ("destination_port", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="incoming_link", to="network_map.containerequipmentport")),
                ("source_port", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="outgoing_link", to="network_map.containerequipmentport")),
            ],
            options={"ordering": ["container", "source_port__equipment", "source_port__number"]},
        ),
    ]
