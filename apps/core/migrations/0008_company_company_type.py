from django.db import migrations, models


def backfill_company_type(apps, schema_editor):
    """Empresas que já concluíram o cadastro sempre operaram como provedor —
    o conceito de projetista (sem clientes) só existe a partir desta versão."""
    Company = apps.get_model("core", "Company")
    Company.objects.filter(
        onboarding_completed=True,
        company_type="",
    ).update(company_type="provider")


class Migration(migrations.Migration):
    dependencies = [("core", "0007_membership_edit_default")]

    operations = [
        migrations.AddField(
            model_name="company",
            name="company_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("provider", "Provedor (ISP, com clientes)"),
                    ("designer", "Projetista (sem clientes)"),
                ],
                help_text=(
                    "Definido pela empresa no primeiro acesso. Depois de definido, "
                    "só o suporte da plataforma pode alterar (planos possuem custos "
                    "diferentes)."
                ),
                max_length=20,
                verbose_name="Tipo de empresa",
            ),
        ),
        migrations.RunPython(
            backfill_company_type,
            migrations.RunPython.noop,
        ),
    ]
