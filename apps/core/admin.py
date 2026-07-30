from django.contrib import admin

from .forms import CompanyEmailConfigurationForm, MapBaseConfigurationAdminForm
from .models import Company, CompanyEmailConfiguration, CompanyMembership, MapBaseConfiguration

admin.site.site_header = "AFService Map"
admin.site.site_title = "Administração AFService Map"
admin.site.index_title = "Central de controle"
# O painel técnico é exclusivo do proprietário da plataforma. Usuários VIEW/EDIT
# trabalham pelas telas operacionais, nunca pelo Django Admin.
admin.site.has_permission = lambda request: (
    request.user.is_active and request.user.is_superuser
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "trade_name", "document", "company_type", "integration_mode", "slug", "active")
    list_filter = ("company_type", "integration_mode", "active")
    search_fields = ("name", "trade_name", "document", "slug")


@admin.register(CompanyMembership)
class CompanyMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "role", "data_source", "erp_provider", "active", "updated_at")
    list_filter = ("role", "data_source", "erp_provider", "active", "company")
    search_fields = ("user__username", "user__email", "company__name", "company__trade_name")
    autocomplete_fields = ("user", "company")
    fieldsets = (
        ("Acesso", {"fields": ("company", "user", "role", "active")}),
        (
            "Perfil de dados",
            {
                "fields": ("data_source", "erp_provider", "erp_configuration_id"),
                "description": (
                    "Usuário padrão trabalha manualmente. Para usuário ERP, informe "
                    "o provedor e o ID da configuração da própria empresa."
                ),
            },
        ),
    )
    actions = ("activate_access", "deactivate_access")

    @admin.action(description="Ativar acessos selecionados")
    def activate_access(self, request, queryset):
        queryset.update(active=True)

    @admin.action(description="Desativar acessos selecionados")
    def deactivate_access(self, request, queryset):
        queryset.update(active=False)


@admin.register(CompanyEmailConfiguration)
class CompanyEmailConfigurationAdmin(admin.ModelAdmin):
    form = CompanyEmailConfigurationForm
    list_display = ("company", "host", "port", "from_email", "enabled", "updated_at")
    list_filter = ("enabled", "use_tls")
    search_fields = ("company__name", "company__trade_name", "host", "from_email")
    autocomplete_fields = ("company",)


@admin.register(MapBaseConfiguration)
class MapBaseConfigurationAdmin(admin.ModelAdmin):
    form = MapBaseConfigurationAdminForm
    list_display = ("name", "google_tiles_enabled", "default_layer", "updated_at")
    readonly_fields = ("created_at", "updated_at")

    def has_add_permission(self, request):
        return not MapBaseConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
