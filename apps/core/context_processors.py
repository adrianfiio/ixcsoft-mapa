from django.conf import settings
from django.db.models import Q

from .access import has_any_edit_access
from .models import Company, CompanyMembership


def app_version(request):
    # app_version é alias de platform_version — ver config/settings.py.
    return {
        "app_version": settings.APP_VERSION,
        "platform_version": settings.PLATFORM_VERSION,
        "map_version": settings.MAP_VERSION,
    }


def _topbar_alerts(company):
    """Alertas ativos da empresa no sino superior, incluindo ocorrências
    SNMP de equipamentos e enlaces para empresas com ou sem ERP."""
    from apps.alerts.models import AlertEvent

    active_states = [
        AlertEvent.State.OPEN,
        AlertEvent.State.ACKNOWLEDGED,
        AlertEvent.State.RECOVERING,
    ]
    alerts = (
        AlertEvent.objects.filter(
            Q(company_id=company.id)
            | Q(cto__company_id=company.id)
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
    if current_company and not current_company.is_designer:
        topbar_alerts = _topbar_alerts(current_company)
    return {
        "show_erp_navigation": show_erp,
        "can_edit_company_assets": has_any_edit_access(request.user),
        # Whitelabel (logo/cor) aplicado em templates/base.html — None pra
        # superusuário, que nunca tem membership e sempre vê a marca padrão.
        "current_company": current_company,
        "topbar_alerts": topbar_alerts,
        # Papel VIEW na empresa atual: menu lateral e atalhos do dashboard
        # ficam restritos a Visão geral + Mapa operacional (o mapa em si já
        # bloqueia edição via can_edit_map/can_edit_company no backend).
        "is_view_only_member": bool(
            membership and membership.role == CompanyMembership.Role.VIEW
        ),
    }
