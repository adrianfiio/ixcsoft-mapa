from django.db import migrations, models


def convert_company_admin_to_edit(apps, schema_editor):
    membership = apps.get_model("core", "CompanyMembership")
    membership.objects.filter(role="admin").update(role="edit")


class Migration(migrations.Migration):
    dependencies = [("core", "0003_companymembership")]

    operations = [
        migrations.RunPython(convert_company_admin_to_edit, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="companymembership",
            name="role",
            field=models.CharField(
                choices=[
                    ("view", "VIEW — somente visualizar"),
                    ("edit", "EDIT — visualizar e editar"),
                ],
                default="view",
                max_length=10,
                verbose_name="Nível de acesso",
            ),
        ),
    ]
