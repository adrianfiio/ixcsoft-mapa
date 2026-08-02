import django.db.models.deletion
import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0013_dashboard_widget_layout"),
        ("access", "0002_add_ftth_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=180, verbose_name="Nome")),
                ("document", models.CharField(blank=True, max_length=30, verbose_name="CPF/CNPJ")),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=40, verbose_name="Telefone")),
                ("address", models.CharField(blank=True, max_length=255, verbose_name="Endereço")),
                ("status", models.CharField(choices=[("active", "Ativo"), ("inactive", "Inativo"), ("suspended", "Suspenso")], default="active", max_length=20)),
                ("monthly_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="Mensalidade")),
                ("due_day", models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(28)], verbose_name="Dia de vencimento")),
                ("billing_active", models.BooleanField(default=True, verbose_name="Gerar mensalidade automaticamente")),
                ("notes", models.TextField(blank=True, verbose_name="Observações")),
                ("access_point", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="access.accesspoint", verbose_name="Ponto de acesso vinculado")),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="+", to="core.company")),
            ],
            options={
                "verbose_name": "Cliente",
                "verbose_name_plural": "Clientes",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Invoice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reference_month", models.DateField(help_text="Sempre o dia 1 do mês cobrado.", verbose_name="Mês de referência")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("due_date", models.DateField(verbose_name="Vencimento")),
                ("status", models.CharField(choices=[("pending", "Pendente"), ("paid", "Paga"), ("overdue", "Atrasada"), ("canceled", "Cancelada")], default="pending", max_length=20)),
                ("payment_method", models.CharField(blank=True, choices=[("cash", "Dinheiro"), ("pix", "PIX"), ("transfer", "Transferência"), ("card", "Cartão"), ("gateway", "Gateway de pagamento"), ("other", "Outro")], max_length=20)),
                ("gateway_provider", models.CharField(choices=[("none", "Nenhum (cobrança manual)"), ("efi", "Efí"), ("inter", "Inter"), ("mercado_pago", "Mercado Pago")], default="none", max_length=20)),
                ("gateway_charge_id", models.CharField(blank=True, max_length=120)),
                ("notes", models.TextField(blank=True, verbose_name="Observações")),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="+", to="core.company")),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invoices", to="billing.customer")),
            ],
            options={
                "verbose_name": "Fatura",
                "verbose_name_plural": "Faturas",
                "ordering": ["-reference_month"],
            },
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("paid_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("method", models.CharField(choices=[("cash", "Dinheiro"), ("pix", "PIX"), ("transfer", "Transferência"), ("card", "Cartão"), ("gateway", "Gateway de pagamento"), ("other", "Outro")], max_length=20)),
                ("note", models.TextField(blank=True)),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to="billing.invoice")),
                ("recorded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Pagamento",
                "verbose_name_plural": "Pagamentos",
                "ordering": ["-paid_at"],
            },
        ),
        migrations.AddIndex(
            model_name="customer",
            index=models.Index(fields=["company", "status"], name="billing_customer_status_idx"),
        ),
        migrations.AddIndex(
            model_name="customer",
            index=models.Index(fields=["company", "billing_active"], name="billing_customer_active_idx"),
        ),
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(fields=["company", "status"], name="billing_invoice_status_idx"),
        ),
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(fields=["customer", "status"], name="billing_invoice_customer_idx"),
        ),
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(fields=["status", "due_date"], name="billing_invoice_due_idx"),
        ),
        migrations.AddConstraint(
            model_name="invoice",
            constraint=models.UniqueConstraint(fields=("customer", "reference_month"), name="unique_invoice_customer_month"),
        ),
    ]
