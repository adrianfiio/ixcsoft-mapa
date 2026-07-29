import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_company_onboarding"),
        ("network_map", "0019_network_element_wireless_types"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContainerEquipment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(db_index=True, max_length=180)),
                ("description", models.TextField(blank=True)),
                ("equipment_type", models.CharField(choices=[("olt", "OLT"), ("dio", "DIO"), ("switch", "Switch"), ("access_point", "Access point"), ("ptp", "Rádio PTP"), ("other", "Outro")], max_length=30)),
                ("management_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("provisioning_mode", models.CharField(choices=[("manual", "Cadastro manual"), ("snmp", "Descoberta e coleta SNMP")], default="manual", max_length=10)),
                ("vendor", models.CharField(blank=True, max_length=80)),
                ("model", models.CharField(blank=True, max_length=120)),
                ("serial_number", models.CharField(blank=True, max_length=120)),
                ("card_count", models.PositiveSmallIntegerField(default=0)),
                ("pons_per_card", models.PositiveSmallIntegerField(default=0)),
                ("dio_port_capacity", models.PositiveSmallIntegerField(default=0)),
                ("enabled", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="+", to="core.company")),
                ("container", models.ForeignKey(limit_choices_to={"element_type__in": ["rack", "tower"]}, on_delete=django.db.models.deletion.CASCADE, related_name="internal_equipments", to="network_map.networkelement")),
            ],
            options={"ordering": ["container", "equipment_type", "name"]},
        ),
        migrations.AddConstraint(
            model_name="containerequipment",
            constraint=models.UniqueConstraint(fields=("container", "name"), name="unique_equipment_name_per_map_container"),
        ),
    ]
