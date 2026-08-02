from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.models import CompanyMembership

from . import services
from .forms import CustomerForm, PaymentRecordForm
from .models import Customer, Invoice


def _billing_company(request):
    """Mesma resolução usada em company_team/company_alerts: a empresa
    do primeiro vínculo EDIT ativo do usuário. Financeiro é sensível o
    bastante pra seguir a mesma regra restrita da gestão de equipe —
    somente EDIT (ou superusuário) entra."""
    if request.user.is_superuser:
        return None
    membership = (
        CompanyMembership.objects.filter(
            user=request.user, active=True, role=CompanyMembership.Role.EDIT
        )
        .select_related("company")
        .first()
    )
    return membership.company if membership else None


def _require_billing_company(request):
    if request.user.is_superuser:
        messages.info(
            request,
            "Financeiro é gerenciado dentro de cada empresa — acesse como um usuário da empresa.",
        )
        return None
    company = _billing_company(request)
    if company is None:
        messages.info(
            request,
            "Somente um usuário com permissão de edição pode gerenciar o financeiro da empresa.",
        )
        return None
    return company


@login_required
def customer_list(request):
    company = _require_billing_company(request)
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

    return render(
        request,
        "billing/customer_list.html",
        {"company": company, "customers": customers, "query": query, "summary": summary},
    )


@login_required
def customer_create(request):
    company = _require_billing_company(request)
    if company is None:
        return redirect("account-panel")

    form = CustomerForm(request.POST or None, company=company)
    if request.method == "POST" and form.is_valid():
        customer = form.save(commit=False)
        customer.company = company
        customer.save()
        messages.success(request, f"Cliente {customer.name} cadastrado.")
        return redirect("billing-customer-detail", pk=customer.pk)

    return render(request, "billing/customer_form.html", {"company": company, "form": form, "customer": None})


@login_required
def customer_update(request, pk):
    company = _require_billing_company(request)
    if company is None:
        return redirect("account-panel")
    customer = get_object_or_404(Customer, pk=pk, company=company)

    form = CustomerForm(request.POST or None, instance=customer, company=company)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cadastro atualizado.")
        return redirect("billing-customer-detail", pk=customer.pk)

    return render(request, "billing/customer_form.html", {"company": company, "form": form, "customer": customer})


@login_required
def customer_detail(request, pk):
    company = _require_billing_company(request)
    if company is None:
        return redirect("account-panel")
    customer = get_object_or_404(Customer, pk=pk, company=company)
    invoices = customer.invoices.prefetch_related("payments").order_by("-reference_month")
    payment_form = PaymentRecordForm()

    return render(
        request,
        "billing/customer_detail.html",
        {
            "company": company,
            "customer": customer,
            "invoices": invoices,
            "payment_form": payment_form,
        },
    )


@login_required
def record_payment(request, pk, invoice_id):
    company = _require_billing_company(request)
    if company is None:
        return redirect("account-panel")
    customer = get_object_or_404(Customer, pk=pk, company=company)
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
