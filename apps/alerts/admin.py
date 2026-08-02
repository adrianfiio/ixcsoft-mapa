from django.contrib import admin
from .models import AlertRule, AlertEvent, AlertNotification


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "scope", "severity", "enabled", "persistence_seconds", "recovery_seconds")
    list_filter = ("scope", "severity", "enabled")


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = (
        "title", "company", "scope", "severity", "state", "opened_at",
        "monitored_link", "container_equipment", "equipment_port", "cto", "route", "olt",
    )
    list_filter = ("company", "scope", "severity", "state")
    search_fields = ("title", "message", "fingerprint", "monitored_link__name", "container_equipment__name")
    date_hierarchy = "opened_at"
    readonly_fields = ("fingerprint", "opened_at", "created_at", "updated_at")


@admin.register(AlertNotification)
class AlertNotificationAdmin(admin.ModelAdmin):
    list_display = ("alert", "channel", "status", "attempts", "sent_at")
    list_filter = ("channel", "status")
