import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_dashboard_widget_layout"),
        ("billing", "0003_customer_ixc_customer"),
    ]

    operations = [
        # A empresa cliente (Provedor ISP / Projetista) é quem é cobrada
        # — não os assinantes de cada provedor. `Customer` representava o
        # modelo errado (um cadastro por assinante final); removido sem
        # migração de dados porque não havia nenhum registro real de
        # produção ainda (funcionalidade lançada há poucos dias, todas as
        # telas mostravam "nenhum cliente cadastrado" nos prints).
        migrations.RemoveConstraint(
            model_name="invoice",
            name="unique_invoice_customer_month",
        ),
        migrations.RemoveIndex(
            model_name="invoice",
            name="billing_invoice_customer_idx",
        ),
        migrations.RemoveField(
            model_name="invoice",
            name="customer",
        ),
        migrations.AddConstraint(
            model_name="invoice",
            constraint=models.UniqueConstraint(fields=("company", "reference_month"), name="unique_invoice_company_month"),
        ),
        migrations.DeleteModel(
            name="Customer",
        ),
        migrations.CreateModel(
            name="CompanySubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("monthly_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="Mensalidade")),
                ("due_day", models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(28)], verbose_name="Dia de vencimento")),
                ("billing_active", models.BooleanField(default=True, verbose_name="Gerar mensalidade automaticamente")),
                ("status", models.CharField(choices=[("active", "Ativa"), ("blocked", "Bloqueada"), ("canceled", "Cancelada")], default="active", max_length=20)),
                ("access_grace_until", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, verbose_name="Observações")),
                ("company", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="subscription", to="core.company")),
            ],
            options={
                "verbose_name": "Assinatura da empresa",
                "verbose_name_plural": "Assinaturas das empresas",
            },
        ),
        migrations.CreateModel(
            name="TrustRelease",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("granted_until", models.DateTimeField()),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="trust_releases", to="core.company")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Liberação de confiança",
                "verbose_name_plural": "Liberações de confiança",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="trustrelease",
            index=models.Index(fields=["company", "created_at"], name="billing_trust_company_idx"),
        ),
    ]
