import csv
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.crypto import SecretCipher
from apps.core.models import Company, CompanyMembership

from . import services
from .forms import (
    GatewaySettingsForm,
    ManualInvoiceForm,
    PaymentRecordForm,
    SubscriptionForm,
)
from .models import CompanyPaymentGatewayConfiguration, CompanySubscription, Invoice


def _editable_company(request):
    """Empresa do primeiro vínculo EDIT ativo do usuário logado (mesma
    resolução de company_team/company_alerts). Financeiro é sensível o
    bastante pra seguir essa mesma regra restrita — VIEW nunca entra."""
    membership = (
        CompanyMembership.objects.filter(
            user=request.user, active=True, role=CompanyMembership.Role.EDIT
        )
        .select_related("company")
        .first()
    )
    return membership.company if membership else None


def _invoice_summary(company):
    today = timezone.localdate()
    open_invoices = Invoice.objects.filter(
        company=company, status__in=[Invoice.Status.PENDING, Invoice.Status.OVERDUE]
    )
    return {
        "overdue_count": open_invoices.filter(status=Invoice.Status.OVERDUE).count(),
        "pending_count": open_invoices.filter(status=Invoice.Status.PENDING).count(),
        "received_month": Invoice.objects.filter(
            company=company, status=Invoice.Status.PAID, reference_month=today.replace(day=1)
        ).count(),
    }


# ---------------------------------------------------------------------
# Painel do cliente (Provedor ISP / Projetista) — só consulta os
# próprios dados. Nenhum cadastro de cliente aqui: quem é cobrado é a
# própria empresa, não um assinante dela.
# ---------------------------------------------------------------------

@login_required
def company_financial_overview(request):
    company = _editable_company(request)
    if company is None:
        messages.info(
            request,
            "Somente um usuário com permissão de edição pode ver o financeiro da empresa.",
        )
        return redirect("account-panel")

    subscription = CompanySubscription.objects.filter(company=company).first()
    invoices = Invoice.objects.filter(company=company).prefetch_related("payments").order_by("-reference_month")
    summary = _invoice_summary(company)
    trust_release_available = not services.has_trust_release_this_month(
        list(company.trust_releases.values_list("created_at", flat=True))
    )

    return render(
        request,
        "billing/company_overview.html",
        {
            "company": company,
            "subscription": subscription,
            "invoices": invoices,
            "summary": summary,
            "trust_release_available": trust_release_available,
        },
    )


@login_required
def request_trust_release_view(request):
    company = _editable_company(request)
    if company is None or request.method != "POST":
        return redirect("billing-overview")
    try:
        services.request_trust_release(company, request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Liberação de confiança concedida — mais 2 dias de acesso.")
    return redirect("billing-overview")


@login_required
def company_financial_export(request):
    company = _editable_company(request)
    if company is None:
        return redirect("account-panel")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="financeiro-{company.slug}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Mês de referência", "Valor", "Vencimento", "Status", "Pago"])
    for invoice in Invoice.objects.filter(company=company).order_by("-reference_month"):
        writer.writerow([
            invoice.reference_month.strftime("%m/%Y"),
            invoice.amount,
            invoice.due_date.strftime("%d/%m/%Y"),
            invoice.get_status_display(),
            invoice.paid_amount,
        ])
    return response


def company_blocked(request):
    company = _editable_company(request) if request.user.is_authenticated else None
    trust_release_available = False
    if company is not None:
        trust_release_available = not services.has_trust_release_this_month(
            list(company.trust_releases.values_list("created_at", flat=True))
        )
    return render(
        request,
        "billing/company_blocked.html",
        {"company": company, "trust_release_available": trust_release_available, "hide_sidebar": True},
    )


# ---------------------------------------------------------------------
# Painel Superadmin — único lugar que cadastra/gerencia empresas,
# lança cobrança manual, registra pagamento e controla status de
# acesso (desativar/bloquear/cancelar).
# ---------------------------------------------------------------------

def _require_superuser(request):
    if not request.user.is_superuser:
        raise PermissionDenied


@login_required
def platform_company_billing(request, company_id):
    _require_superuser(request)
    company = get_object_or_404(Company, pk=company_id)
    subscription, _created = CompanySubscription.objects.get_or_create(company=company)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_subscription":
            form = SubscriptionForm(request.POST, instance=subscription)
            if form.is_valid():
                form.save()
                messages.success(request, "Assinatura atualizada.")
            else:
                messages.error(request, "Não foi possível salvar — confira os dados.")
        elif action == "create_invoice":
            invoice_form = ManualInvoiceForm(request.POST)
            if invoice_form.is_valid():
                Invoice.objects.create(
                    company=company,
                    reference_month=invoice_form.cleaned_data["due_date"].replace(day=1),
                    amount=invoice_form.cleaned_data["amount"],
                    due_date=invoice_form.cleaned_data["due_date"],
                    notes=invoice_form.cleaned_data["notes"],
                )
                messages.success(request, "Cobrança lançada.")
            else:
                messages.error(request, "Não foi possível lançar a cobrança — confira os dados.")
        elif action == "record_payment":
            invoice = get_object_or_404(Invoice, pk=request.POST.get("invoice_id"), company=company)
            payment_form = PaymentRecordForm(request.POST)
            if payment_form.is_valid():
                services.record_payment(
                    invoice,
                    amount=payment_form.cleaned_data["amount"],
                    method=payment_form.cleaned_data["method"],
                    note=payment_form.cleaned_data["note"],
                    user=request.user,
                )
                messages.success(request, "Pagamento registrado.")
            else:
                messages.error(request, "Não foi possível registrar o pagamento — confira os dados.")
        elif action == "set_status":
            new_status = request.POST.get("status")
            if new_status in CompanySubscription.Status.values:
                subscription.status = new_status
                if new_status == CompanySubscription.Status.ACTIVE:
                    subscription.access_grace_until = None
                subscription.save(update_fields=["status", "access_grace_until", "updated_at"])
                messages.success(request, "Status da assinatura atualizado.")
        elif action == "toggle_company_active":
            company.active = not company.active
            company.save(update_fields=["active"])
            messages.success(request, "Empresa atualizada." if company.active else "Empresa desativada.")
        elif action == "delete_company":
            # Sem exclusão física de verdade — desativa a empresa e
            # cancela a assinatura junto, mesma filosofia não-destrutiva
            # já usada no resto do sistema (nunca apaga cadastro,
            # equipamento, cabo etc.). Dá pra reverter pela mesma tela.
            company.active = False
            company.save(update_fields=["active"])
            subscription.status = CompanySubscription.Status.CANCELED
            subscription.save(update_fields=["status", "updated_at"])
            messages.success(request, "Empresa excluída (desativada e assinatura cancelada — nada foi apagado do banco).")
        return redirect("platform-company-billing", company_id=company.id)

    subscription_form = SubscriptionForm(instance=subscription)
    invoice_form = ManualInvoiceForm()
    payment_form = PaymentRecordForm()
    invoices = Invoice.objects.filter(company=company).prefetch_related("payments").order_by("-reference_month")

    return render(
        request,
        "billing/platform_company_billing.html",
        {
            "company": company,
            "subscription": subscription,
            "subscription_form": subscription_form,
            "invoice_form": invoice_form,
            "payment_form": payment_form,
            "invoices": invoices,
            "summary": _invoice_summary(company),
        },
    )


@login_required
def platform_financial_export(request):
    _require_superuser(request)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="financeiro-plataforma.csv"'
    writer = csv.writer(response)
    writer.writerow(["Empresa", "Mês de referência", "Valor", "Vencimento", "Status", "Pago"])
    invoices = Invoice.objects.select_related("company").order_by("company__name", "-reference_month")
    for invoice in invoices:
        writer.writerow([
            invoice.company.trade_name or invoice.company.name,
            invoice.reference_month.strftime("%m/%Y"),
            invoice.amount,
            invoice.due_date.strftime("%d/%m/%Y"),
            invoice.get_status_display(),
            invoice.paid_amount,
        ])
    return response


@login_required
def platform_gateway_settings(request, company_id):
    """Só o Superadmin gerencia credencial de gateway — centralizado,
    fora do Django Admin. Nenhuma chamada real ao gateway acontece aqui,
    só armazenamento criptografado (ver docstring do model)."""
    _require_superuser(request)
    company = get_object_or_404(Company, pk=company_id)
    configuration = CompanyPaymentGatewayConfiguration.objects.filter(company=company).first()

    initial = {}
    if configuration:
        initial = {
            "provider": configuration.provider,
            "sandbox_mode": configuration.sandbox_mode,
            "enabled": configuration.enabled,
        }
    form = GatewaySettingsForm(request.POST or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        cipher = SecretCipher()
        current = {}
        if configuration and configuration.credentials_encrypted:
            try:
                current = json.loads(cipher.decrypt(configuration.credentials_encrypted))
            except (ValueError, json.JSONDecodeError):
                current = {}
        credentials = {
            "client_id": form.cleaned_data["client_id"] or current.get("client_id", ""),
            "client_secret": form.cleaned_data["client_secret"] or current.get("client_secret", ""),
            "access_token": form.cleaned_data["access_token"] or current.get("access_token", ""),
        }
        if configuration is None:
            configuration = CompanyPaymentGatewayConfiguration(company=company)
        configuration.provider = form.cleaned_data["provider"]
        configuration.sandbox_mode = form.cleaned_data["sandbox_mode"]
        configuration.enabled = form.cleaned_data["enabled"]
        configuration.credentials_encrypted = cipher.encrypt(json.dumps(credentials))
        configuration.save()
        messages.success(request, "Configuração de gateway salva.")
        return redirect("platform-gateway-settings", company_id=company.id)

    return render(
        request,
        "billing/gateway_settings.html",
        {"company": company, "form": form, "configuration": configuration},
    )
