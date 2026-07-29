from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("network_map", "0014_cpd_and_pole_attachments"),
        ("olt_integration", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="olt",
            name="cpd",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="olts", to="network_map.pop", verbose_name="CPD / POP"),
        ),
        migrations.AddField(
            model_name="olt",
            name="provisioning_mode",
            field=models.CharField(choices=[("manual", "Cadastro manual"), ("snmp", "Descoberta e coleta SNMP")], default="manual", max_length=10, verbose_name="Forma de cadastro"),
        ),
        migrations.CreateModel(
            name="OLTCard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("frame", models.PositiveSmallIntegerField(default=0)),
                ("slot", models.PositiveSmallIntegerField()),
                ("name", models.CharField(blank=True, max_length=120)),
                ("model", models.CharField(blank=True, max_length=120)),
                ("serial_number", models.CharField(blank=True, max_length=120)),
                ("pon_port_count", models.PositiveSmallIntegerField(default=16)),
                ("enabled", models.BooleanField(default=True)),
                ("olt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cards", to="olt_integration.olt")),
            ],
            options={"ordering": ["olt", "frame", "slot"], "verbose_name": "Placa da OLT", "verbose_name_plural": "Placas da OLT"},
        ),
        migrations.AddField(
            model_name="ponport",
            name="card",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pon_ports", to="olt_integration.oltcard"),
        ),
        migrations.AddField(
            model_name="ponport",
            name="tx_power_dbm",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name="Potência de saída (dBm)"),
        ),
        migrations.AddConstraint(
            model_name="oltcard",
            constraint=models.UniqueConstraint(fields=("olt", "frame", "slot"), name="unique_olt_card_slot"),
        ),
    ]
