import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_dashboard_widget_layout"),
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyPaymentGatewayConfiguration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("provider", models.CharField(choices=[("none", "Nenhum (cobrança manual)"), ("efi", "Efí"), ("inter", "Inter"), ("mercado_pago", "Mercado Pago")], default="none", max_length=20)),
                ("credentials_encrypted", models.TextField(blank=True, editable=False)),
                ("sandbox_mode", models.BooleanField(default=True, verbose_name="Ambiente de testes (sandbox)")),
                ("enabled", models.BooleanField(default=False, verbose_name="Integração ativa")),
                ("company", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="payment_gateway", to="core.company")),
            ],
            options={
                "verbose_name": "Configuração de gateway de pagamento",
                "verbose_name_plural": "Configurações de gateway de pagamento",
            },
        ),
    ]
