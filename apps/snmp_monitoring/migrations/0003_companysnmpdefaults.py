import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0013_dashboard_widget_layout"),
        ("snmp_monitoring", "0002_link_monitoring"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanySNMPDefaults",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("community_encrypted", models.TextField(blank=True)),
                (
                    "company",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="snmp_defaults",
                        to="core.company",
                    ),
                ),
            ],
            options={
                "verbose_name": "Community SNMP padrão",
                "verbose_name_plural": "Communities SNMP padrão",
            },
        ),
    ]
