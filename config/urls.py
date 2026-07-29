from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import AccountPanelView, DashboardView, company_alerts, company_onboarding, create_company_asset, erp_onboarding


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
    path("painel/alertas/", company_alerts, name="company-alerts"),
    path("painel/novo/<str:asset_type>/", create_company_asset, name="company-asset-create"),
    path("painel/integracao/", erp_onboarding, name="erp-onboarding"),
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
