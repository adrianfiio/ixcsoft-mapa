from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import NetworkRoute, NetworkElement, CTO, FiberCable, NetworkDependency


@admin.register(NetworkRoute)
class NetworkRouteAdmin(GISModelAdmin):
    list_display = ("name", "code", "status", "enabled")
    list_filter = ("status", "enabled")
    search_fields = ("name", "code")


@admin.register(NetworkElement)
class NetworkElementAdmin(GISModelAdmin):
    list_display = ("name", "code", "element_type", "status", "enabled")
    list_filter = ("element_type", "status", "enabled")
    search_fields = ("name", "code")


@admin.register(CTO)
class CTOAdmin(GISModelAdmin):
    list_display = ("name", "ixc_box_id", "route", "status", "capacity", "enabled")
    list_filter = ("status", "route", "enabled")
    search_fields = ("name", "code", "ixc_box_id")


@admin.register(FiberCable)
class FiberCableAdmin(GISModelAdmin):
    list_display = ("name", "code", "cable_type", "fiber_count", "used_fibers", "status")
    list_filter = ("cable_type", "status", "route")
    search_fields = ("name", "code")


admin.site.register(NetworkDependency)
