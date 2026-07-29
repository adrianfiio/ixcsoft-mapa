from django.db.models import Q

from .models import CompanyMembership


EDIT_ROLES = (CompanyMembership.Role.EDIT,)


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


def has_any_edit_access(user):
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or CompanyMembership.objects.filter(
        user=user, active=True, role__in=EDIT_ROLES
    ).exists()
