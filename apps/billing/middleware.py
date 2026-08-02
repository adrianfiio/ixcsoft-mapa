from django.shortcuts import redirect
from django.urls import reverse

from apps.core.models import CompanyMembership

from . import services
from .models import CompanySubscription

# Nunca intercepta essas rotas — login/logout/estáticos/admin/API já têm
# a própria checagem de autenticação, e bloquear a própria tela de
# "conta bloqueada" travaria o usuário sem saída.
ALLOWED_PATH_PREFIXES = (
    "/static/",
    "/assets/",
    "/media/",
    "/admin/",
    "/login/",
    "/sair/",
    "/api/",
    "/carregando/",
)


class SubscriptionAccessMiddleware:
    """Bloqueia o acesso às telas normais quando a assinatura da empresa
    (`CompanySubscription`) está bloqueada/cancelada e não há liberação
    de confiança em vigor. Superusuário nunca é afetado. Empresa sem
    `CompanySubscription` cadastrada (ainda a maioria, já que o recurso
    é novo) nunca é bloqueada — só entra em vigor quando o Superadmin
    explicitamente bloqueia/cancela pela Visão da plataforma."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        company = self._blocked_company(request)
        if company is not None:
            blocked_path = reverse("company-blocked")
            if request.path != blocked_path:
                return redirect(blocked_path)
        return self.get_response(request)

    def _blocked_company(self, request):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or user.is_superuser:
            return None
        if any(request.path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES):
            return None
        membership = (
            CompanyMembership.objects.filter(user=user, active=True)
            .select_related("company")
            .first()
        )
        if membership is None:
            return None
        subscription = CompanySubscription.objects.filter(company=membership.company).first()
        if services.is_access_blocked(subscription):
            return membership.company
        return None
