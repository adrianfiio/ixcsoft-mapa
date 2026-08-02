"""Agregação de dados pra "Visão da plataforma" (superadmin): um resumo
por empresa ativa, mais os totais somados. Um módulo pequeno e separado
de `views.py` pelo mesmo motivo de `dashboard_widgets.py` — é uma peça de
lógica independente, mais fácil de ler isolada.

As consultas rodam uma vez por empresa (não usam annotate/subquery
agregada) — tranquilo pra uma página admin-only de uso ocasional com um
número pequeno de empresas. Se o número de empresas crescer muito, isso
merece ser reescrito com `annotate`/`Prefetch` pra evitar N+1.
"""

from datetime import timedelta

from django.contrib.gis.db.models.functions import Length, Transform
from django.db.models import FloatField, Q, Sum
from django.utils import timezone

from apps.alerts.models import AlertEvent
from apps.billing.models import Invoice
from apps.ixc_integration.models import IXCConfiguration, IXCCustomer
from apps.network_map.models import CTO, FiberCable, NetworkElement

from .models import Company, CompanyMembership

ACTIVE_ALERT_STATES = [
    AlertEvent.State.OPEN,
    AlertEvent.State.ACKNOWLEDGED,
    AlertEvent.State.RECOVERING,
]

SYNC_STALE_AFTER = timedelta(hours=24)


def _cable_km(company):
    length = (
        FiberCable.objects.filter(company=company, geometry__isnull=False)
        .annotate(length=Length(Transform("geometry", 3857), output_field=FloatField()))
        .aggregate(total=Sum("length"))["total"]
    )
    return round((length or 0) / 1000, 2)


def _sync_state(company, config):
    if company.integration_mode != Company.IntegrationMode.ERP:
        return "sem_erp"
    if not config or not config.last_sync_at:
        return "nunca_sincronizou"
    if config.last_sync_status == "failed":
        return "falhou"
    if timezone.now() - config.last_sync_at > SYNC_STALE_AFTER:
        return "atrasada"
    return "ok"


def _company_row(company):
    config = (
        IXCConfiguration.objects.filter(company=company)
        .order_by("-last_sync_at")
        .first()
    )
    alert_count = (
        AlertEvent.objects.filter(
            Q(cto__company=company) | Q(olt__cpd__company=company) | Q(route__company=company),
            state__in=ACTIVE_ALERT_STATES,
        )
        .distinct()
        .count()
    )
    sync_state = _sync_state(company, config)
    open_invoices = Invoice.objects.filter(
        company=company, status__in=[Invoice.Status.PENDING, Invoice.Status.OVERDUE]
    )
    return {
        "company": company,
        "client_count": IXCCustomer.objects.filter(company=company).count(),
        "element_count": NetworkElement.objects.filter(company=company).count(),
        "cto_count": CTO.objects.filter(company=company).count(),
        "cable_km": _cable_km(company),
        "alert_count": alert_count,
        "overdue_count": open_invoices.filter(status=Invoice.Status.OVERDUE).count(),
        "pending_count": open_invoices.filter(status=Invoice.Status.PENDING).count(),
        "team_count": CompanyMembership.objects.filter(company=company, active=True).count(),
        "provider_name": config.get_provider_display() if config else "",
        "last_sync_at": config.last_sync_at if config else None,
        "sync_state": sync_state,
        "needs_attention": (
            not company.onboarding_completed
            or sync_state in {"nunca_sincronizou", "atrasada", "falhou"}
        ),
    }


def platform_overview_summary():
    companies = Company.objects.filter(active=True).order_by("name")
    rows = [_company_row(company) for company in companies]

    received_month = Invoice.objects.filter(
        status=Invoice.Status.PAID, reference_month=timezone.localdate().replace(day=1)
    ).aggregate(total=Sum("amount"))["total"] or 0

    return {
        "companies_summary": rows,
        "attention_rows": [row for row in rows if row["needs_attention"]],
        "metric_companies": len(rows),
        "metric_new_companies": Company.objects.filter(
            active=True, created_at__gte=timezone.now() - timedelta(days=30)
        ).count(),
        "metric_platform_clients": sum(row["client_count"] for row in rows),
        "metric_platform_cables": round(sum(row["cable_km"] for row in rows), 2),
        "metric_platform_elements": sum(row["element_count"] for row in rows),
        "metric_platform_alerts": sum(row["alert_count"] for row in rows),
        "metric_sync_issues": sum(
            1 for row in rows if row["sync_state"] in {"atrasada", "falhou", "nunca_sincronizou"}
        ),
        "metric_platform_received_month": received_month,
    }
