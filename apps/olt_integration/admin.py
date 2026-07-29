from django.contrib import admin
from .models import OLT, OLTCard, PONPort, ONU, ONUSignalHistory


class OLTCardInline(admin.TabularInline):
    model = OLTCard
    extra = 1


@admin.register(OLT)
class OLTAdmin(admin.ModelAdmin):
    list_display = ("name", "cpd", "provisioning_mode", "management_ip", "vendor", "model", "status", "enabled", "last_poll_at")
    list_filter = ("cpd", "provisioning_mode", "vendor", "status", "enabled")
    search_fields = ("name", "management_ip", "hostname", "model", "serial_number")
    inlines = [OLTCardInline]


@admin.register(OLTCard)
class OLTCardAdmin(admin.ModelAdmin):
    list_display = ("olt", "frame", "slot", "name", "model", "pon_port_count", "enabled")
    list_filter = ("olt", "enabled")


@admin.register(PONPort)
class PONPortAdmin(admin.ModelAdmin):
    list_display = ("olt", "card", "frame", "slot", "port", "tx_power_dbm", "status", "capacity", "last_seen_at")
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
