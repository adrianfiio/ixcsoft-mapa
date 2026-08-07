from django.db import migrations, models


def migrate_roles_forward(apps, schema_editor):
    CompanyMembership = apps.get_model("core", "CompanyMembership")
    # Promovemos todos os antigos 'edit' para 'admin' para manter compatibilidade com administradores existentes
    CompanyMembership.objects.filter(role="edit").update(role="admin")


def migrate_roles_backward(apps, schema_editor):
    CompanyMembership = apps.get_model("core", "CompanyMembership")
    CompanyMembership.objects.filter(role="admin").update(role="edit")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_dashboard_widget_layout"),
    ]

    operations = [
        migrations.RunPython(migrate_roles_forward, migrate_roles_backward),
        migrations.AlterField(
            model_name="companymembership",
            name="role",
            field=models.CharField(
                choices=[
                    ("view", "VIEW — somente visualizar"),
                    ("edit", "EDIT — visualizar e editar"),
                    ("admin", "ADMIN — administrar a empresa"),
                    ("technician", "Técnico — aplicativo de campo"),
                ],
                default="edit",
                max_length=15,
                verbose_name="Nível de acesso",
            ),
        ),
    ]
