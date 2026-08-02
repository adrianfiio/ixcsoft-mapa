import calendar

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Customer, Invoice, Payment


def clamp_due_day(year, month, day):
    """Garante um dia válido dentro do mês (evita "31 de fevereiro")."""
    last_day = calendar.monthrange(year, month)[1]
    return min(day, last_day)


def reference_month_for(today=None):
    today = today or timezone.localdate()
    return today.replace(day=1)


def due_date_for(reference_month, due_day):
    day = clamp_due_day(reference_month.year, reference_month.month, due_day)
    return reference_month.replace(day=day)


def generate_monthly_invoices(today=None):
    """Cria a fatura do mês corrente para cada cliente com mensalidade
    ativa que ainda não tem fatura nesse mês. Idempotente — pode ser
    chamada quantas vezes for, nunca duplica (UniqueConstraint em
    customer+reference_month)."""
    reference_month = reference_month_for(today)
    created = []
    customers = Customer.objects.filter(
        billing_active=True,
        monthly_amount__isnull=False,
        due_day__isnull=False,
    )
    for customer in customers:
        due_date = due_date_for(reference_month, customer.due_day)
        try:
            with transaction.atomic():
                invoice = Invoice.objects.create(
                    company_id=customer.company_id,
                    customer=customer,
                    reference_month=reference_month,
                    amount=customer.monthly_amount,
                    due_date=due_date,
                )
            created.append(invoice)
        except IntegrityError:
            continue
    return created


def mark_overdue_invoices(today=None):
    today = today or timezone.localdate()
    return Invoice.objects.filter(
        status=Invoice.Status.PENDING, due_date__lt=today
    ).update(status=Invoice.Status.OVERDUE)


def record_payment(invoice, amount, method, note="", user=None, paid_at=None):
    """Registra um pagamento (parcial ou total) contra uma fatura e
    atualiza o status dela quando o total pago atinge o valor devido."""
    payment = Payment.objects.create(
        invoice=invoice,
        amount=amount,
        method=method,
        note=note,
        recorded_by=user if user and user.is_authenticated else None,
        paid_at=paid_at or timezone.now(),
    )
    if invoice.paid_amount >= invoice.amount and invoice.status != Invoice.Status.CANCELED:
        invoice.status = Invoice.Status.PAID
        invoice.payment_method = method
        invoice.save(update_fields=["status", "payment_method", "updated_at"])
    return payment
