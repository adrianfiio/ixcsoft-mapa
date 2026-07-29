from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import (
    CableModel,
    CTO,
    CTOSplitter,
    CTOSplitterPort,
    FiberCable,
    FiberColor,
    FiberColorStandard,
    FiberColorStandardItem,
    FiberStrand,
    FiberSplice,
    SpliceTray,
    FiberTube,
    NetworkDependency,
    NetworkElement,
    NetworkProject,
    NetworkRoute,
    POP,
    Rack,
    RackEquipment,
)


@admin.register(NetworkProject)
class NetworkProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "status", "company", "enabled", "updated_at")
    list_filter = ("status", "enabled", "company")
    search_fields = ("name", "code", "description")
    readonly_fields = ("created_at", "updated_at")


class CTOSplitterPortInline(admin.TabularInline):
    model = CTOSplitterPort
    extra = 0


@admin.register(CTOSplitter)
class CTOSplitterAdmin(admin.ModelAdmin):
    list_display = (
        "name", "cto", "ratio", "output_ports",
        "input_cable", "input_fiber", "position", "enabled",
    )
    list_filter = ("ratio", "enabled")
    search_fields = ("name", "cto__name", "cto__code")
    autocomplete_fields = ("cto", "input_cable", "input_fiber")
    inlines = [CTOSplitterPortInline]


# ==========================
# Inlines
# ==========================

class RackEquipmentInline(admin.TabularInline):
    model = RackEquipment
    extra = 0


class FiberColorStandardItemInline(admin.TabularInline):
    model = FiberColorStandardItem
    extra = 0


class FiberTubeInline(admin.TabularInline):
    model = FiberTube
    extra = 0


class FiberStrandInline(admin.TabularInline):
    model = FiberStrand
    extra = 0


# ==========================
# Rede existente
# ==========================

@admin.register(NetworkRoute)
class NetworkRouteAdmin(GISModelAdmin):
    list_display = (
        "name",
        "code",
        "status",
        "enabled",
    )

    list_filter = (
        "status",
        "enabled",
    )

    search_fields = (
        "name",
        "code",
    )


@admin.register(NetworkElement)
class NetworkElementAdmin(GISModelAdmin):
    list_display = (
        "name",
        "code",
        "element_type",
        "status",
        "enabled",
    )

    list_filter = (
        "element_type",
        "status",
        "enabled",
    )

    search_fields = (
        "name",
        "code",
    )


@admin.register(CTO)
class CTOAdmin(GISModelAdmin):
    list_display = (
        "name",
        "ixc_box_id",
        "route",
        "capacity",
        "status",
        "enabled",
    )

    list_filter = (
        "status",
        "route",
        "enabled",
    )

    search_fields = (
        "name",
        "code",
        "ixc_box_id",
    )


@admin.register(FiberCable)
class FiberCableAdmin(GISModelAdmin):
    list_display = (
        "name",
        "code",
        "cable_type",
        "cable_model",
        "fiber_count",
        "used_fibers",
        "status",
    )

    list_filter = (
        "cable_type",
        "status",
        "route",
        "cable_model",
    )

    search_fields = (
        "name",
        "code",
    )

    autocomplete_fields = (
        "origin",
        "destination",
        "route",
        "cable_model",
    )

    inlines = [
        FiberTubeInline,
        FiberStrandInline,
    ]


admin.site.register(NetworkDependency)


# ==========================
# POP
# ==========================

@admin.register(POP)
class POPAdmin(GISModelAdmin):
    list_display = (
        "code",
        "name",
        "city",
        "enabled",
    )

    list_filter = (
        "city",
        "enabled",
    )

    search_fields = (
        "code",
        "name",
        "city",
    )


# ==========================
# Rack
# ==========================

@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "pop",
        "manufacturer",
        "model",
        "height_units",
        "enabled",
    )

    list_filter = (
        "pop",
        "enabled",
    )

    search_fields = (
        "code",
        "name",
        "manufacturer",
        "model",
    )

    autocomplete_fields = (
        "pop",
    )

    inlines = [
        RackEquipmentInline,
    ]


@admin.register(RackEquipment)
class RackEquipmentAdmin(admin.ModelAdmin):
    list_display = (
        "rack",
        "name",
        "equipment_type",
        "start_unit",
        "unit_height",
        "face",
    )

    list_filter = (
        "equipment_type",
        "face",
    )

    search_fields = (
        "name",
        "manufacturer",
        "model",
        "serial_number",
    )

    autocomplete_fields = (
        "rack",
    )


# ==========================
# Cores
# ==========================

@admin.register(FiberColor)
class FiberColorAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "name",
        "code",
        "hex_color",
    )

    search_fields = (
        "name",
        "code",
        "hex_color",
    )

    ordering = (
        "order",
    )


@admin.register(FiberColorStandard)
class FiberColorStandardAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
    )

    search_fields = (
        "name",
        "code",
    )

    inlines = [
        FiberColorStandardItemInline,
    ]


# ==========================
# Modelo de cabo
# ==========================

@admin.register(CableModel)
class CableModelAdmin(admin.ModelAdmin):
    list_display = (
        "manufacturer",
        "model",
        "fiber_count",
        "tube_count",
        "fibers_per_tube",
    )

    list_filter = (
        "construction",
    )

    search_fields = (
        "manufacturer",
        "model",
    )

    autocomplete_fields = (
        "color_standard",
    )


# ==========================
# Tubos
# ==========================

@admin.register(FiberTube)
class FiberTubeAdmin(admin.ModelAdmin):
    list_display = (
        "cable",
        "number",
        "color",
        "identification",
    )

    search_fields = (
        "identification",
    )

    autocomplete_fields = (
        "cable",
        "color",
    )


# ==========================
# Fibras
# ==========================

@admin.register(FiberStrand)
class FiberStrandAdmin(admin.ModelAdmin):
    list_display = (
        "cable",
        "number",
        "tube",
        "color",
        "status",
        "usage",
    )

    list_filter = (
        "status",
        "color",
    )

    search_fields = (
        "usage",
        "notes",
    )

    autocomplete_fields = (
        "cable",
        "tube",
        "origin_element",
        "destination_element",
        "color",
    )


# ==========================
# Emendas ópticas
# ==========================

@admin.register(SpliceTray)
class SpliceTrayAdmin(admin.ModelAdmin):
    list_display = (
        "splice_box",
        "number",
        "name",
        "capacity",
    )

    list_filter = (
        "splice_box",
    )

    search_fields = (
        "name",
    )

    autocomplete_fields = (
        "splice_box",
    )


@admin.register(FiberSplice)
class FiberSpliceAdmin(admin.ModelAdmin):
    list_display = (
        "tray",
        "position",
        "splice_box",
        "input_fiber",
        "output_fiber",
        "loss_db",
    )

    list_filter = (
        "tray",
        "splice_box",
    )

    search_fields = (
        "notes",
    )

    autocomplete_fields = (
        "tray",
        "splice_box",
        "input_fiber",
        "output_fiber",
    )
