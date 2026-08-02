import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.crypto import SecretCipher
from apps.core.models import Company, CompanyMembership
from apps.ixc_integration.models import IXCCustomer

from . import services
from .forms import CustomerForm, GatewaySettingsForm, PaymentRecordForm
from .models import CompanyPaymentGatewayConfiguration, Customer, Invoice


def _editable_company(request):
    """Empresa do primeiro vínculo EDIT ativo do usuário logado (mesma
    resolução de company_team/company_alerts)."""
    membership = (
        CompanyMembership.objects.filter(
            user=request.user, active=True, role=CompanyMembership.Role.EDIT
        )
        .select_related("company")
        .first()
    )
    return membership.company if membership else None


def _require_list_company(request):
    """Resolução de empresa pras telas sem cliente ainda escolhido (lista
    e criação). Usuário normal usa o próprio vínculo EDIT — só isso já
    bloqueia VIEW por completo, mesma regra restrita de company_team.
    Superusuário não tem uma "própria" empresa: precisa escolher uma
    pelo link da Visão da plataforma (`?empresa=<id>`)."""
    if request.user.is_superuser:
        company_id = request.GET.get("empresa")
        company = Company.objects.filter(pk=company_id).first() if company_id else None
        if company is None:
            messages.info(
                request,
                "Escolha uma empresa na Visão da plataforma para ver o financeiro dela.",
            )
        return company
    company = _editable_company(request)
    if company is None:
        messages.info(
            request,
            "Somente um usuário com permissão de edição pode gerenciar o financeiro da empresa.",
        )
    return company


def _customer_for_request(request, pk):
    """Resolução pras telas que já têm um cliente (detalhe, edição,
    pagamento). Superusuário vê o financeiro de qualquer empresa; usuário
    normal só o da própria empresa (o filtro `company=` no
    `get_object_or_404` faz o cliente de outra empresa dar 404 — igual a
    "não existe", sem revelar que pertence a outra empresa)."""
    if request.user.is_superuser:
        return get_object_or_404(Customer, pk=pk)
    company = _editable_company(request)
    if company is None:
        return None
    return get_object_or_404(Customer, pk=pk, company=company)


@login_required
def customer_list(request):
    company = _require_list_company(request)
    if company is None:
        return redirect("account-panel")

    query = request.GET.get("q", "").strip()
    customers = Customer.objects.filter(company=company).order_by("name")
    if query:
        customers = customers.filter(name__icontains=query)

    today = timezone.localdate()
    open_invoices = Invoice.objects.filter(
        company=company, status__in=[Invoice.Status.PENDING, Invoice.Status.OVERDUE]
    )
    summary = {
        "overdue_count": open_invoices.filter(status=Invoice.Status.OVERDUE).count(),
        "pending_count": open_invoices.filter(status=Invoice.Status.PENDING).count(),
        "received_month": Invoice.objects.filter(
            company=company, status=Invoice.Status.PAID, reference_month=today.replace(day=1)
        ).count(),
    }

    # Clientes já sincronizados do IXCSoft que ainda não têm nenhum
    # cadastro financeiro — sem isso, uma empresa com ERP via Financeiro
    # vazio mesmo já tendo milhares de clientes reais no sistema.
    unconfigured = (
        IXCCustomer.objects.filter(company=company, active=True, billing_customer__isnull=True)
        .order_by("name")
    )
    if query:
        unconfigured = unconfigured.filter(name__icontains=query)
    unconfigured_page = Paginator(unconfigured, 25).get_page(request.GET.get("pagina_erp"))

    return render(
        request,
        "billing/customer_list.html",
        {
            "company": company,
            "customers": customers,
            "query": query,
            "summary": summary,
            "unconfigured_page": unconfigured_page,
        },
    )


@login_required
def customer_create(request):
    company = _require_list_company(request)
    if company is None:
        return redirect("account-panel")

    ixc_customer = None
    ixc_customer_id = request.GET.get("ixc_customer")
    if ixc_customer_id:
        ixc_customer = IXCCustomer.objects.filter(pk=ixc_customer_id, company=company).first()
        if ixc_customer and hasattr(ixc_customer, "billing_customer"):
            messages.info(request, "Este cliente do ERP já tem um cadastro financeiro.")
            return redirect("billing-customer-detail", pk=ixc_customer.billing_customer.pk)

    initial = None
    if ixc_customer and request.method != "POST":
        initial = {
            "name": ixc_customer.name,
            "document": ixc_customer.document,
            "email": ixc_customer.email,
            "phone": ixc_customer.phone,
        }
    form = CustomerForm(request.POST or None, company=company, initial=initial)
    if request.method == "POST" and form.is_valid():
        customer = form.save(commit=False)
        customer.company = company
        customer.ixc_customer = ixc_customer
        customer.save()
        messages.success(request, f"Cliente {customer.name} cadastrado.")
        return redirect("billing-customer-detail", pk=customer.pk)

    return render(request, "billing/customer_form.html", {"company": company, "form": form, "customer": None})


@login_required
def customer_update(request, pk):
    customer = _customer_for_request(request, pk)
    if customer is None:
        messages.info(request, "Somente um usuário com permissão de edição pode gerenciar o financeiro da empresa.")
        return redirect("account-panel")

    form = CustomerForm(request.POST or None, instance=customer, company=customer.company)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cadastro atualizado.")
        return redirect("billing-customer-detail", pk=customer.pk)

    return render(request, "billing/customer_form.html", {"company": customer.company, "form": form, "customer": customer})


@login_required
def customer_detail(request, pk):
    customer = _customer_for_request(request, pk)
    if customer is None:
        messages.info(request, "Somente um usuário com permissão de edição pode gerenciar o financeiro da empresa.")
        return redirect("account-panel")
    invoices = customer.invoices.prefetch_related("payments").order_by("-reference_month")
    payment_form = PaymentRecordForm()

    return render(
        request,
        "billing/customer_detail.html",
        {
            "company": customer.company,
            "customer": customer,
            "invoices": invoices,
            "payment_form": payment_form,
        },
    )


@login_required
def record_payment(request, pk, invoice_id):
    customer = _customer_for_request(request, pk)
    if customer is None:
        messages.info(request, "Somente um usuário com permissão de edição pode gerenciar o financeiro da empresa.")
        return redirect("account-panel")
    invoice = get_object_or_404(Invoice, pk=invoice_id, customer=customer)

    if request.method != "POST":
        return redirect("billing-customer-detail", pk=customer.pk)

    form = PaymentRecordForm(request.POST)
    if form.is_valid():
        services.record_payment(
            invoice,
            amount=form.cleaned_data["amount"],
            method=form.cleaned_data["method"],
            note=form.cleaned_data["note"],
            user=request.user,
        )
        messages.success(request, "Pagamento registrado.")
    else:
        messages.error(request, "Não foi possível registrar o pagamento — confira os dados.")
    return redirect("billing-customer-detail", pk=customer.pk)


@login_required
def platform_gateway_settings(request, company_id):
    """Só o Superadmin gerencia credencial de gateway — centralizado,
    fora do Django Admin. Nenhuma chamada real ao gateway acontece aqui,
    só armazenamento criptografado (ver docstring do model)."""
    if not request.user.is_superuser:
        raise PermissionDenied
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
