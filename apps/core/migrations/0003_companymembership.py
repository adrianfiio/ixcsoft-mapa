import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_mapbaseconfiguration"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("role", models.CharField(choices=[("view", "VIEW — somente visualizar"), ("edit", "EDIT — visualizar e editar"), ("admin", "ADMIN — administrar a empresa")], default="view", max_length=10, verbose_name="Nível de acesso")),
                ("active", models.BooleanField(default=True, verbose_name="Acesso ativo")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="core.company", verbose_name="Empresa")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="company_memberships", to=settings.AUTH_USER_MODEL, verbose_name="Usuário")),
            ],
            options={
                "verbose_name": "Acesso à empresa",
                "verbose_name_plural": "Acessos às empresas",
                "ordering": ("company__name", "user__username"),
            },
        ),
        migrations.AddConstraint(
            model_name="companymembership",
            constraint=models.UniqueConstraint(fields=("company", "user"), name="core_unique_company_user_membership"),
        ),
    ]
