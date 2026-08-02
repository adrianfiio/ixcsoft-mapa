from django.contrib import admin

from .models import Customer, Invoice, Payment


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "status", "monthly_amount", "due_day", "billing_active")
    list_filter = ("company", "status", "billing_active")
    search_fields = ("name", "document", "email", "phone")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("customer", "company", "reference_month", "amount", "due_date", "status")
    list_filter = ("company", "status", "gateway_provider")
    search_fields = ("customer__name", "customer__document")
    date_hierarchy = "due_date"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "method", "paid_at", "recorded_by")
    list_filter = ("method",)
