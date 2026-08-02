from django.contrib import admin

from .map_master_models import MapDiagramRevision, MapIconStyle, NetworkAssetLifecycle


@admin.register(MapIconStyle)
class MapIconStyleAdmin(admin.ModelAdmin):
    list_display = (
        "display_name", "element_type", "subtype", "company", "size_px",
        "show_label", "enabled", "updated_at",
    )
    list_filter = ("company", "element_type", "show_label", "enabled")
    search_fields = ("display_name", "element_type", "subtype")
    fieldsets = (
        ("Identificação", {"fields": ("company", "element_type", "subtype", "display_name", "enabled")}),
        ("Desenho", {"fields": ("svg_markup", "image_url", "size_px")}),
        ("Cores", {"fields": ("foreground_color", "background_color", "border_color")}),
        ("Rótulo", {"fields": ("show_label", "show_name_inside_icon")}),
    )


@admin.register(MapDiagramRevision)
class MapDiagramRevisionAdmin(admin.ModelAdmin):
    list_display = ("project", "element", "diagram_type", "created_by", "created_at")
    list_filter = ("diagram_type", "company", "created_at")
    search_fields = ("project__name", "element__name", "note")
    readonly_fields = ("created_at", "updated_at")


@admin.register(NetworkAssetLifecycle)
class NetworkAssetLifecycleAdmin(admin.ModelAdmin):
    list_display = ("project", "asset_type", "asset_id", "stage", "changed_by", "created_at")
    list_filter = ("asset_type", "stage", "company", "created_at")
    search_fields = ("project__name", "note")
    readonly_fields = ("created_at", "updated_at")
