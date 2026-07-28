from django.contrib import admin
from .models import OLT, PONPort, ONU, ONUSignalHistory


@admin.register(OLT)
class OLTAdmin(admin.ModelAdmin):
    list_display = ("name", "management_ip", "vendor", "model", "status", "enabled", "last_poll_at")
    list_filter = ("vendor", "status", "enabled")
    search_fields = ("name", "management_ip", "hostname", "model", "serial_number")


@admin.register(PONPort)
class PONPortAdmin(admin.ModelAdmin):
    list_display = ("olt", "frame", "slot", "port", "status", "capacity", "last_seen_at")
    list_filter = ("olt", "status")
    search_fields = ("olt__name", "interface_name", "description")


@admin.register(ONU)
class ONUAdmin(admin.ModelAdmin):
    list_display = ("pon_port", "onu_id", "serial_number", "operational_status", "los", "rx_power", "last_collected_at")
    list_filter = ("operational_status", "los", "registration_status", "pon_port__olt")
    search_fields = ("serial_number", "mac_address", "model")


@admin.register(ONUSignalHistory)
class ONUSignalHistoryAdmin(admin.ModelAdmin):
    list_display = ("onu", "collected_at", "operational_status", "los", "rx_power", "tx_power")
    list_filter = ("operational_status", "los")
    date_hierarchy = "collected_at"
