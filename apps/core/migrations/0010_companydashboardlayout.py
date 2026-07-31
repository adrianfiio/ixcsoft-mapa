import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_companyemailconfiguration"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyDashboardLayout",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "widget_order",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Lista ordenada das chaves de widget do dashboard dessa empresa.",
                    ),
                ),
                (
                    "hidden_widgets",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Chaves de widget ocultas nesse dashboard.",
                    ),
                ),
                (
                    "banner_text",
                    models.CharField(blank=True, max_length=280, verbose_name="Mensagem no topo do dashboard"),
                ),
                (
                    "company",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dashboard_layout",
                        to="core.company",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Layout de dashboard da empresa",
                "verbose_name_plural": "Layouts de dashboard das empresas",
            },
        ),
    ]
