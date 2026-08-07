from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from apps.core.access import is_technician_only


class TechnicianAppOnlyMiddleware:
    """Mantém usuários exclusivamente TÉCNICO dentro do aplicativo de campo."""

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    # MAP_V084_TECHNICIAN_MIDDLEWARE: nomes de rota reais deste projeto —
    # é "/sair/" (não "/logout/") que faz logout (config/urls.py). Também
    # inclui "/conta-bloqueada/": esse middleware roda depois do
    # SubscriptionAccessMiddleware (config/settings.py) de propósito, pra
    # esse deixar passar primeiro qualquer bloqueio de assinatura -- sem
    # isso, redirect daquele middleware pra "/conta-bloqueada/" seria
    # imediatamente revertido de volta pro "/app/" aqui, criando loop.
    ALLOWED_PREFIXES = (
        "/app/",
        "/api/map/",
        "/assets/static/",
        "/media/",
        "/login/",
        "/sair/",
        "/conta-bloqueada/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and is_technician_only(user):
            path = request.path

            if path.startswith("/api/map/") and request.method not in self.SAFE_METHODS:
                return JsonResponse(
                    {"success": False, "error": "Perfil técnico possui acesso somente leitura."},
                    status=403,
                )

            if not any(path.startswith(prefix) for prefix in self.ALLOWED_PREFIXES):
                return redirect(reverse("technician-app"))

        return self.get_response(request)
