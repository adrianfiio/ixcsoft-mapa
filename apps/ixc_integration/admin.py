from django.contrib import admin
from .models import IXCConfiguration, IXCSyncExecution
from .customer_models import IXCCustomer, IXCLogin


@admin.register(IXCConfiguration)
class IXCConfigurationAdmin(admin.ModelAdmin):
    list_display = ("name", "base_url", "enabled", "sync_interval_minutes", "last_sync_at", "last_sync_status")


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
