from django.contrib import admin
from apps.core.admin_gis import AFServiceGISAdmin, GeoPointAdminForm
from .models import DIO, DIOPort, DIOTray


class DIOAdminForm(GeoPointAdminForm):
    class Meta:
        model = DIO
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("point"):
            pop = cleaned.get("pop")
            if pop and pop.point:
                cleaned["point"] = pop.point
                self.instance.point = pop.point
        return cleaned


class DIOTrayInline(admin.TabularInline):
    model = DIOTray
    extra = 0
    fields = (
        "number",
        "name",
        "splice_capacity",
        "notes",
    )


class DIOPortInline(admin.TabularInline):
    model = DIOPort
    extra = 0
    fields = (
        "number",
        "label",
        "tray",
        "connector_type",
        "status",
        "enabled",
    )


@admin.register(DIO)
class DIOAdmin(AFServiceGISAdmin):
    form = DIOAdminForm
    list_display = (
        "code",
        "name",
        "pop",
        "rack",
        "connector_type",
        "tray_capacity",
        "port_capacity",
        "status",
        "enabled",
    )
    list_filter = (
        "company",
        "pop",
        "connector_type",
        "status",
        "enabled",
    )
    search_fields = (
        "code",
        "name",
        "manufacturer",
        "model",
        "serial_number",
        "pop__name",
        "pop__code",
        "rack__name",
        "rack__code",
    )
    autocomplete_fields = (
        "company",
        "pop",
        "rack",
        "rack_equipment",
    )
    inlines = [
        DIOTrayInline,
        DIOPortInline,
    ]


@admin.register(DIOTray)
class DIOTrayAdmin(admin.ModelAdmin):
    list_display = (
        "dio",
        "number",
        "name",
        "splice_capacity",
    )
    list_filter = (
        "dio__pop",
        "dio",
    )
    search_fields = (
        "dio__name",
        "dio__code",
        "name",
    )
    autocomplete_fields = (
        "dio",
    )


@admin.register(DIOPort)
class DIOPortAdmin(admin.ModelAdmin):
    list_display = (
        "dio",
        "number",
        "label",
        "tray",
        "connector_type",
        "status",
        "enabled",
    )
    list_filter = (
        "dio__pop",
        "dio",
        "connector_type",
        "status",
        "enabled",
    )
    search_fields = (
        "dio__name",
        "dio__code",
        "label",
    )
    autocomplete_fields = (
        "dio",
        "tray",
    )
