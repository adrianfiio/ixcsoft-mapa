from django.db.models import Q

from .models import CompanyMembership


EDIT_ROLES = (CompanyMembership.Role.EDIT, CompanyMembership.Role.ADMIN)
ADMIN_ROLES = (CompanyMembership.Role.ADMIN,)
TECHNICIAN_ROLES = (CompanyMembership.Role.TECHNICIAN, CompanyMembership.Role.ADMIN, CompanyMembership.Role.EDIT)


def accessible_company_ids(user):
    if not user or not user.is_authenticated:
        return []
    if user.is_superuser:
        return None
    return list(
        CompanyMembership.objects.filter(user=user, active=True).values_list(
            "company_id", flat=True
        )
    )


def editable_company_ids(user):
    if not user or not user.is_authenticated:
        return []
    if user.is_superuser:
        return None
    return list(
        CompanyMembership.objects.filter(
            user=user,
            active=True,
            role__in=EDIT_ROLES,
        ).values_list("company_id", flat=True)
    )


def admin_company_ids(user):
    if not user or not user.is_authenticated:
        return []
    if user.is_superuser:
        return None
    return list(
        CompanyMembership.objects.filter(
            user=user,
            active=True,
            role__in=ADMIN_ROLES,
        ).values_list("company_id", flat=True)
    )


def scope_company_queryset(queryset, user, field="company_id"):
    company_ids = accessible_company_ids(user)
    if company_ids is None:
        return queryset
    return queryset.filter(**{f"{field}__in": company_ids})


def can_view_company(user, company_id):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return CompanyMembership.objects.filter(
        user=user, company_id=company_id, active=True
    ).exists()


def can_edit_company(user, company_id):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return CompanyMembership.objects.filter(
        user=user,
        company_id=company_id,
        active=True,
        role__in=EDIT_ROLES,
    ).exists()


def user_can_admin_company(user, company_id):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return CompanyMembership.objects.filter(
        user=user,
        company_id=company_id,
        active=True,
        role__in=ADMIN_ROLES,
    ).exists()


def onboarding_redirect_name(user):
    """Nome da url de onboarding pendente para o usuário, ou None se já completo."""
    from apps.ixc_integration.models import IXCConfiguration

    if not user or not user.is_authenticated or user.is_superuser:
        return None
    membership = CompanyMembership.objects.filter(
        user=user, active=True
    ).select_related("company").first()
    if membership and membership.role == CompanyMembership.Role.ADMIN:
        company = membership.company
        if company.needs_type_choice:
            return "company-onboarding"
        if company.needs_provider_mode_choice:
            return "company-provider-mode"
    if (
        has_any_edit_access(user)
        and CompanyMembership.objects.filter(
            user=user, active=True, company__integration_mode="erp"
        ).exists()
        and not IXCConfiguration.objects.filter(
            company_id__in=editable_company_ids(user), enabled=True
        ).exists()
    ):
        return "erp-onboarding"
    return None


def has_any_edit_access(user):
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or CompanyMembership.objects.filter(
        user=user, active=True, role__in=EDIT_ROLES
    ).exists()


def has_any_admin_access(user):
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or CompanyMembership.objects.filter(
        user=user, active=True, role__in=ADMIN_ROLES
    ).exists()


def is_technician_only(user):
    """Verdadeiro só quando o usuário não tem NENHUM vínculo ativo que não
    seja TÉCNICO -- alguém que é Técnico numa empresa e ADMIN/EDIT/VIEW em
    outra não é bloqueado globalmente no /app/ por isso."""
    if not user or not user.is_authenticated or user.is_superuser:
        return False
    memberships = CompanyMembership.objects.filter(user=user, active=True)
    return memberships.exists() and not memberships.exclude(
        role=CompanyMembership.Role.TECHNICIAN
    ).exists()


def has_technician_access(user, company_id=None):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    qs = CompanyMembership.objects.filter(
        user=user,
        active=True,
        role__in=TECHNICIAN_ROLES,
    )
    if company_id:
        qs = qs.filter(company_id=company_id)
    return qs.exists()
