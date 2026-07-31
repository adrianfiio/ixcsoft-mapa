from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import (
    AccountPanelView,
    DashboardLayoutEditorView,
    DashboardLayoutListView,
    DashboardView,
    PlatformOverviewView,
    company_alerts,
    company_email_settings,
    company_onboarding,
    company_provider_mode,
    company_search,
    company_team,
    create_company_asset,
    erp_onboarding,
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
    path("", DashboardView.as_view(), name="dashboard"),
    path("mapa/", DashboardView.as_view(template_name="map.html"), name="map"),
    path("painel/", AccountPanelView.as_view(), name="account-panel"),
    path("painel/primeiro-acesso/", company_onboarding, name="company-onboarding"),
    path("painel/modo-operacao/", company_provider_mode, name="company-provider-mode"),
    path("painel/equipe/", company_team, name="company-team"),
    path("painel/email/", company_email_settings, name="company-email-settings"),
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
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/ixc/", include("apps.ixc_integration.api.urls")),
    path("api/map/", include("apps.network_map.api.urls")),
    path("", include("apps.network_map.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
