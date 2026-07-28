import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        (
            "network_map",
            "0002_fibercolor_fibercable_company_networkelement_company_and_more",
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="fibercable",
                    name="company",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="core.company",
                    ),
                ),
                migrations.AddField(
                    model_name="networkelement",
                    name="company",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="core.company",
                    ),
                ),
                migrations.AddField(
                    model_name="networkroute",
                    name="company",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="core.company",
                    ),
                ),
            ],
        ),
    ]
