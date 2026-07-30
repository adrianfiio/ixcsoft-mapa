import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0008_company_company_type")]

    operations = [
        migrations.CreateModel(
            name="CompanyEmailConfiguration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("host", models.CharField(max_length=255, verbose_name="Servidor SMTP")),
                ("port", models.PositiveIntegerField(default=587, verbose_name="Porta")),
                ("username", models.CharField(blank=True, max_length=255, verbose_name="Usuário")),
                ("password_encrypted", models.TextField(blank=True, editable=False)),
                ("use_tls", models.BooleanField(default=True, verbose_name="Usar TLS")),
                ("from_email", models.EmailField(max_length=254, verbose_name="E-mail remetente")),
                ("enabled", models.BooleanField(default=True, verbose_name="Integração ativa")),
                (
                    "company",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_configuration",
                        to="core.company",
                    ),
                ),
            ],
            options={
                "verbose_name": "Configuração de e-mail (SMTP)",
                "verbose_name_plural": "Configurações de e-mail (SMTP)",
            },
        ),
    ]
