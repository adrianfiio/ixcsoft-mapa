from django.contrib import admin
from .models import AlertRule, AlertEvent, AlertNotification


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "scope", "severity", "enabled", "persistence_seconds", "recovery_seconds")
    list_filter = ("scope", "severity", "enabled")


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = ("title", "scope", "severity", "state", "opened_at", "cto", "route", "olt")
    list_filter = ("scope", "severity", "state")
    search_fields = ("title", "message", "fingerprint")
    date_hierarchy = "opened_at"


@admin.register(AlertNotification)
class AlertNotificationAdmin(admin.ModelAdmin):
    list_display = ("alert", "channel", "status", "attempts", "sent_at")
    list_filter = ("channel", "status")
