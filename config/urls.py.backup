from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("", TemplateView.as_view(template_name="dashboard.html"), name="dashboard"),
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/ixc/", include("apps.ixc_integration.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
