from django.conf import settings

from .access import has_any_edit_access
from .models import Company, CompanyMembership


def app_version(request):
    return {"app_version": settings.APP_VERSION}


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
    return {
        "show_erp_navigation": show_erp,
        "can_edit_company_assets": has_any_edit_access(request.user),
        # Whitelabel (logo/cor) aplicado em templates/base.html — None pra
        # superusuário, que nunca tem membership e sempre vê a marca padrão.
        "current_company": membership.company if membership else None,
    }
