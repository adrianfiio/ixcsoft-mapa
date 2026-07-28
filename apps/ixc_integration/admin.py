from django.contrib import admin
from .forms import IXCConfigurationAdminForm
from .models import IXCConfiguration, IXCSyncExecution
from .customer_models import IXCCustomer, IXCLogin
from .fiber_models import IXCFiberAssignment


@admin.register(IXCConfiguration)
class IXCConfigurationAdmin(admin.ModelAdmin):
    form = IXCConfigurationAdminForm
    list_display = ("company", "name", "base_url", "enabled", "sync_interval_minutes", "last_sync_at", "last_sync_status")
    list_filter = ("company", "enabled", "verify_ssl")
    search_fields = ("company__name", "company__trade_name", "name", "base_url")


@admin.register(IXCSyncExecution)
class IXCSyncExecutionAdmin(admin.ModelAdmin):
    list_display = ("configuration", "status", "started_at", "finished_at", "records_received", "records_failed")
    list_filter = ("status",)
    date_hierarchy = "started_at"


@admin.register(IXCCustomer)
class IXCCustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "ixc_customer_id", "active", "phone", "email")
    list_filter = ("active",)
    search_fields = ("name", "ixc_customer_id", "document")


@admin.register(IXCLogin)
class IXCLoginAdmin(admin.ModelAdmin):
    list_display = ("username", "customer", "cto", "onu", "online", "status", "last_synced_at")
    list_filter = ("online", "status")
    search_fields = ("username", "ixc_login_id", "customer__name")


@admin.register(IXCFiberAssignment)
class IXCFiberAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "name", "ixc_id", "ixc_login_id", "ixc_cto_id",
        "mac_address", "pon_id", "onu_number", "rx_power", "last_synced_at",
    )
    list_filter = ("ixc_project_id", "city")
    search_fields = (
        "name", "ixc_id", "ixc_login_id", "ixc_cto_id",
        "mac_address", "pon_id", "address",
    )
