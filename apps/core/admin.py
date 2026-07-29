from django.contrib import admin

from .forms import MapBaseConfigurationAdminForm
from .models import Company, MapBaseConfiguration


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "trade_name", "document", "slug", "active")
    list_filter = ("active",)
    search_fields = ("name", "trade_name", "document", "slug")


@admin.register(MapBaseConfiguration)
class MapBaseConfigurationAdmin(admin.ModelAdmin):
    form = MapBaseConfigurationAdminForm
    list_display = ("name", "google_tiles_enabled", "default_layer", "updated_at")
    readonly_fields = ("created_at", "updated_at")

    def has_add_permission(self, request):
        return not MapBaseConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
