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
            # database_operations era [] — o campo "company" nunca era
            # criado de verdade em FiberCable/NetworkElement/NetworkRoute
            # num banco novo (só existia no estado do Django). Isso quebra
            # qualquer `migrate` do zero (ex.: disaster recovery) na
            # primeira query que toque nesses campos, com "column ... does
            # not exist". Em produção não muda nada: a coluna já existe lá
            # (foi criada por fora, antes desta migration ser reescrita) e
            # esta migration já está registrada como aplicada — o `migrate`
            # não reexecuta migrations já aplicadas, então isto só afeta
            # bancos novos.
            database_operations=[
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
