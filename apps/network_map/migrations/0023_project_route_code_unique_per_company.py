from django.db import migrations, models


class Migration(migrations.Migration):
    """Corrige NetworkProject.code e NetworkRoute.code, que eram únicos
    globalmente (entre todas as empresas) em vez de únicos por empresa —
    o que impedia uma empresa de usar um código já usado por outra.

    A troca de `unique=True` para `UniqueConstraint(company, code)` é segura
    sem limpeza de dados: como o campo já era único globalmente, não podem
    existir hoje dois registros com o mesmo código, então a constraint por
    empresa (mais permissiva) nunca falhará ao ser aplicada.
    """

    dependencies = [("network_map", "0022_equipment_cards_and_network_ports")]

    operations = [
        migrations.AlterField(
            model_name="networkproject",
            name="code",
            field=models.CharField(db_index=True, max_length=100),
        ),
        migrations.AddConstraint(
            model_name="networkproject",
            constraint=models.UniqueConstraint(
                fields=("company", "code"),
                name="unique_project_code_per_company",
            ),
        ),
        migrations.AlterField(
            model_name="networkroute",
            name="code",
            field=models.CharField(max_length=80),
        ),
        migrations.AddConstraint(
            model_name="networkroute",
            constraint=models.UniqueConstraint(
                fields=("company", "code"),
                name="unique_route_code_per_company",
            ),
        ),
    ]
