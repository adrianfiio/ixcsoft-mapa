from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "trade_name", "document", "slug", "active")
    list_filter = ("active",)
    search_fields = ("name", "trade_name", "document", "slug")
