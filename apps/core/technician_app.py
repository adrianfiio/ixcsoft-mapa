from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.core.access import accessible_company_ids


class TechnicianAppView(LoginRequiredMixin, TemplateView):
    """Mapa de campo, somente leitura, usando a mesma sessão e API do AFService Map."""

    template_name = "technician_app.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_superuser:
            if not accessible_company_ids(request.user):
                raise PermissionDenied("Usuário sem empresa ativa.")
        return super().dispatch(request, *args, **kwargs)


@require_GET
def technician_service_worker(request):
    """Serve o service worker em /app/sw.js para que o escopo possa ser /app/."""

    response: HttpResponse = render(
        request,
        "pwa/technician-sw.js",
        content_type="application/javascript; charset=utf-8",
    )
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Service-Worker-Allowed"] = "/app/"
    return response
