from django.contrib import admin

from .models import AccessPoint


@admin.register(AccessPoint)
class AccessPointAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name",
        "username",
        "source",
        "status",
        "online",
        "last_seen_at",
    )

    list_filter = (
        "source",
        "status",
        "online",
        "company",
    )

    search_fields = (
        "customer_name",
        "username",
        "external_id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "raw_data",
    )
