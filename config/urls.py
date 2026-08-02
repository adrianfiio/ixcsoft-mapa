from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.views.static import serve as serve_media
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import (
    AccountPanelView,
    DashboardLayoutEditorView,
    DashboardLayoutListView,
    DashboardView,
    LoadingView,
    PlatformOverviewView,
    company_alerts,
    company_branding,
    company_email_settings,
    company_onboarding,
    company_provider_mode,
    company_search,
    company_team,
    create_company_asset,
    erp_onboarding,
    platform_company_create,
)
from apps.billing.views import (
    company_blocked,
    company_financial_export,
    company_financial_overview,
    platform_company_billing,
    platform_financial_export,
    platform_gateway_settings,
    request_trust_release_view,
)


urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("carregando/", LoadingView.as_view(), name="loading"),
    path("", DashboardView.as_view(), name="dashboard"),
    path("mapa/", DashboardView.as_view(template_name="map.html"), name="map"),
    path("painel/", AccountPanelView.as_view(), name="account-panel"),
    path("painel/primeiro-acesso/", company_onboarding, name="company-onboarding"),
    path("painel/modo-operacao/", company_provider_mode, name="company-provider-mode"),
    path("painel/equipe/", company_team, name="company-team"),
    path("painel/email/", company_email_settings, name="company-email-settings"),
    path("painel/marca/", company_branding, name="company-branding"),
    path("painel/buscar/", company_search, name="company-search"),
    path("painel/alertas/", company_alerts, name="company-alerts"),
    path("painel/novo/<str:asset_type>/", create_company_asset, name="company-asset-create"),
    path("painel/integracao/", erp_onboarding, name="erp-onboarding"),
    path("painel/dashboards/", DashboardLayoutListView.as_view(), name="dashboard-layouts"),
    path(
        "painel/dashboards/<int:company_id>/",
        DashboardLayoutEditorView.as_view(),
        name="dashboard-layout-editor",
    ),
    path("painel/plataforma/", PlatformOverviewView.as_view(), name="platform-overview"),
    path("painel/plataforma/empresas/novo/", platform_company_create, name="platform-company-create"),
    path(
        "painel/plataforma/empresas/<int:company_id>/gateway/",
        platform_gateway_settings,
        name="platform-gateway-settings",
    ),
    path(
        "painel/plataforma/empresas/<int:company_id>/financeiro/",
        platform_company_billing,
        name="platform-company-billing",
    ),
    path("painel/plataforma/financeiro/exportar/", platform_financial_export, name="platform-financial-export"),
    path("painel/financeiro/", company_financial_overview, name="billing-overview"),
    path("painel/financeiro/liberacao-confianca/", request_trust_release_view, name="billing-request-trust-release"),
    path("painel/financeiro/exportar/", company_financial_export, name="billing-export"),
    path("conta-bloqueada/", company_blocked, name="company-blocked"),
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/ixc/", include("apps.ixc_integration.api.urls")),
    path("api/monitoring/", include("apps.snmp_monitoring.urls")),
    path("api/map/", include("apps.network_map.api.urls")),
    path("", include("apps.network_map.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

# Sem nginx/CDN dedicado pra mídia neste deploy (container único atrás de um
# proxy simples) — servir MEDIA_ROOT pelo próprio processo é suficiente pro
# volume esperado (logos de empresa), mesmo raciocínio já usado com o
# WhiteNoise para estáticos.
#
# NÃO usar `django.conf.urls.static.static()` aqui: essa função só gera a
# rota quando `DEBUG=True` (é um no-op silencioso em produção) — foi
# exatamente por isso que o upload de logo "salvava" mas a imagem nunca
# carregava (a URL /media/... batia em lugar nenhum). `serve` direto não
# tem essa checagem.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve_media, {"document_root": settings.MEDIA_ROOT}),
]
