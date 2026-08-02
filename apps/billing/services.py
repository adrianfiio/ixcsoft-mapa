import calendar
import datetime

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from .models import CompanySubscription, Invoice, Payment, TrustRelease

TRUST_RELEASE_BONUS_DAYS = 2


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


def is_access_blocked(subscription, now=None):
    """Função pura (sem banco): decide se o acesso da empresa deve ficar
    bloqueado. Sem assinatura cadastrada = nunca bloqueia (fail-safe —
    toda empresa que já existia antes deste recurso não pode ficar presa
    fora do sistema por engano)."""
    if subscription is None:
        return False
    if subscription.status == CompanySubscription.Status.ACTIVE:
        return False
    now = now or timezone.now()
    if subscription.access_grace_until and subscription.access_grace_until > now:
        return False
    return True


def generate_monthly_invoices(today=None):
    """Cria a fatura do mês corrente pra cada empresa com mensalidade
    ativa que ainda não tem fatura nesse mês. Idempotente — pode ser
    chamada quantas vezes for, nunca duplica (UniqueConstraint em
    company+reference_month)."""
    reference_month = reference_month_for(today)
    created = []
    subscriptions = CompanySubscription.objects.filter(
        billing_active=True,
        monthly_amount__isnull=False,
        due_day__isnull=False,
    ).exclude(status=CompanySubscription.Status.CANCELED)
    for subscription in subscriptions:
        due_date = due_date_for(reference_month, subscription.due_day)
        try:
            with transaction.atomic():
                invoice = Invoice.objects.create(
                    company_id=subscription.company_id,
                    reference_month=reference_month,
                    amount=subscription.monthly_amount,
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


def has_trust_release_this_month(dates, now=None):
    """Função pura (sem banco): recebe uma lista de `datetime` de pedidos
    já feitos e diz se algum caiu no mês corrente."""
    now = now or timezone.now()
    return any(dt.year == now.year and dt.month == now.month for dt in dates)


def request_trust_release(company, user):
    """"Liberação de confiança": concede mais 2 dias de acesso mesmo com
    a assinatura bloqueada/cancelada. No máximo 1 vez por mês corrente —
    validado aqui, contra o banco, na hora do pedido (a função pura
    `has_trust_release_this_month` faz a mesma checagem sem banco, usada
    nos testes)."""
    now = timezone.now()
    already_used = TrustRelease.objects.filter(
        company=company, created_at__year=now.year, created_at__month=now.month
    ).exists()
    if already_used:
        raise ValueError("Este mês a liberação de confiança já foi usada.")

    granted_until = now + datetime.timedelta(days=TRUST_RELEASE_BONUS_DAYS)
    with transaction.atomic():
        release = TrustRelease.objects.create(
            company=company,
            requested_by=user if user and user.is_authenticated else None,
            granted_until=granted_until,
        )
        subscription, _ = CompanySubscription.objects.get_or_create(company=company)
        subscription.access_grace_until = granted_until
        subscription.save(update_fields=["access_grace_until", "updated_at"])
    return release


def _shift_month(reference, delta):
    """Função pura (sem banco): desloca uma data (sempre dia 1) em `delta`
    meses — positivo ou negativo, tratando virada de ano."""
    month_index = reference.month - 1 + delta
    year = reference.year + month_index // 12
    month = month_index % 12 + 1
    return reference.replace(year=year, month=month, day=1)


def platform_financial_summary(today=None):
    """Visão financeira agregada de toda a plataforma (todas as empresas),
    pro painel Superadmin. Só somas diretas (`aggregate`) — diferente de
    `apps.core.platform_overview`, que faz uma consulta por empresa porque
    precisa de dados não-financeiros por linha; aqui os números são
    globais, então dá pra somar direto sem loop."""
    today = today or timezone.localdate()
    month_start = today.replace(day=1)

    mrr = CompanySubscription.objects.filter(
        status=CompanySubscription.Status.ACTIVE, billing_active=True
    ).aggregate(total=Sum("monthly_amount"))["total"] or 0

    received_month = Invoice.objects.filter(
        status=Invoice.Status.PAID, reference_month=month_start
    ).aggregate(total=Sum("amount"))["total"] or 0

    pending_amount = Invoice.objects.filter(
        status=Invoice.Status.PENDING
    ).aggregate(total=Sum("amount"))["total"] or 0

    overdue_amount = Invoice.objects.filter(
        status=Invoice.Status.OVERDUE
    ).aggregate(total=Sum("amount"))["total"] or 0

    open_count = Invoice.objects.filter(
        status__in=[Invoice.Status.PENDING, Invoice.Status.OVERDUE]
    ).count()
    overdue_count = Invoice.objects.filter(status=Invoice.Status.OVERDUE).count()
    default_rate = round((overdue_count / open_count) * 100, 1) if open_count else 0

    blocked_subscriptions = list(
        CompanySubscription.objects.filter(
            status__in=[CompanySubscription.Status.BLOCKED, CompanySubscription.Status.CANCELED]
        )
        .select_related("company")
        .order_by("company__name")
    )

    revenue_history = []
    for offset in range(5, -1, -1):
        month = _shift_month(month_start, -offset)
        total = Invoice.objects.filter(
            status=Invoice.Status.PAID, reference_month=month
        ).aggregate(total=Sum("amount"))["total"] or 0
        revenue_history.append({"month": month, "total": total})
    peak = max((entry["total"] for entry in revenue_history), default=0)
    for entry in revenue_history:
        entry["pct"] = round((entry["total"] / peak) * 100, 1) if peak else 0

    aging_invoices = list(
        Invoice.objects.filter(status=Invoice.Status.OVERDUE)
        .select_related("company")
        .order_by("due_date")
    )
    for invoice in aging_invoices:
        invoice.days_overdue = (today - invoice.due_date).days

    recent_payments = list(
        Payment.objects.select_related("invoice__company", "recorded_by").order_by("-paid_at")[:20]
    )

    recent_trust_releases = list(
        TrustRelease.objects.select_related("company", "requested_by").order_by("-created_at")[:20]
    )

    return {
        "metric_mrr": mrr,
        "metric_received_month": received_month,
        "metric_pending_amount": pending_amount,
        "metric_overdue_amount": overdue_amount,
        "metric_default_rate": default_rate,
        "metric_blocked_companies": len(blocked_subscriptions),
        "revenue_history": revenue_history,
        "aging_invoices": aging_invoices,
        "blocked_subscriptions": blocked_subscriptions,
        "recent_payments": recent_payments,
        "recent_trust_releases": recent_trust_releases,
    }
