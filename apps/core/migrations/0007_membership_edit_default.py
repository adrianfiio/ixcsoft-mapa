from django.db import migrations, models


def promote_incomplete_manual_accounts(apps, schema_editor):
    Membership = apps.get_model("core", "CompanyMembership")
    Membership.objects.filter(
        data_source="manual",
        role="view",
        company__onboarding_completed=False,
    ).update(role="edit")


class Migration(migrations.Migration):
    dependencies = [("core", "0006_companymembership_data_source")]

    operations = [
        migrations.AlterField(
            model_name="companymembership",
            name="role",
            field=models.CharField(
                choices=[
                    ("view", "VIEW — somente visualizar"),
                    ("edit", "EDIT — visualizar e editar"),
                ],
                default="edit",
                max_length=10,
                verbose_name="Nível de acesso",
            ),
        ),
        migrations.RunPython(
            promote_incomplete_manual_accounts,
            migrations.RunPython.noop,
        ),
    ]
