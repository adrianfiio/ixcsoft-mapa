from django.contrib import admin

from .models import (
    CompanyPaymentGatewayConfiguration,
    CompanySubscription,
    Invoice,
    Payment,
    TrustRelease,
)


@admin.register(CompanySubscription)
class CompanySubscriptionAdmin(admin.ModelAdmin):
    list_display = ("company", "status", "monthly_amount", "due_day", "billing_active", "access_grace_until")
    list_filter = ("status", "billing_active")
    search_fields = ("company__name", "company__trade_name")


@admin.register(TrustRelease)
class TrustReleaseAdmin(admin.ModelAdmin):
    list_display = ("company", "created_at", "granted_until", "requested_by")
    list_filter = ("company",)
    date_hierarchy = "created_at"


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("company", "reference_month", "amount", "due_date", "status")
    list_filter = ("company", "status", "gateway_provider")
    search_fields = ("company__name", "company__trade_name")
    date_hierarchy = "due_date"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "method", "paid_at", "recorded_by")
    list_filter = ("method",)


@admin.register(CompanyPaymentGatewayConfiguration)
class CompanyPaymentGatewayConfigurationAdmin(admin.ModelAdmin):
    list_display = ("company", "provider", "sandbox_mode", "enabled", "updated_at")
    list_filter = ("provider", "enabled", "sandbox_mode")
    readonly_fields = ("credentials_encrypted",)
