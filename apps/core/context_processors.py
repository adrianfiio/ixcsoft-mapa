from django.conf import settings
from django.db.models import Q

from .access import has_any_edit_access
from .models import Company, CompanyMembership


def app_version(request):
    return {"app_version": settings.APP_VERSION}


def _topbar_alerts(company):
    """Alertas ativos da empresa pro sino no topo (só provedora com ERP —
    ver `company_navigation`). Consulta leve, com índice em
    (state, severity, -opened_at); só roda quando há empresa elegível."""
    from apps.alerts.models import AlertEvent

    active_states = [
        AlertEvent.State.OPEN,
        AlertEvent.State.ACKNOWLEDGED,
        AlertEvent.State.RECOVERING,
    ]
    alerts = (
        AlertEvent.objects.filter(
            Q(cto__company_id=company.id)
            | Q(olt__cpd__company_id=company.id)
            | Q(route__company_id=company.id),
            state__in=active_states,
        )
        .distinct()
        .order_by("-opened_at")
    )
    return {"enabled": True, "count": alerts.count(), "items": list(alerts[:5])}


def company_navigation(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    memberships = CompanyMembership.objects.filter(
        user=request.user,
        active=True,
    ).select_related("company")
    show_erp = request.user.is_superuser or memberships.filter(
        data_source=CompanyMembership.DataSource.ERP,
        company__integration_mode=Company.IntegrationMode.ERP,
    ).exists()
    membership = memberships.first()
    current_company = membership.company if membership else None
    topbar_alerts = {"enabled": False, "count": 0, "items": []}
    if show_erp and current_company and not current_company.is_designer:
        topbar_alerts = _topbar_alerts(current_company)
    return {
        "show_erp_navigation": show_erp,
        "can_edit_company_assets": has_any_edit_access(request.user),
        # Whitelabel (logo/cor) aplicado em templates/base.html — None pra
        # superusuário, que nunca tem membership e sempre vê a marca padrão.
        "current_company": current_company,
        "topbar_alerts": topbar_alerts,
    }
