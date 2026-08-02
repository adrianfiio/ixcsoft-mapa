from django import forms
from django.contrib import admin

from .models import (
    MonitoredNetworkLink,
    SNMPInterfaceState,
    SNMPMonitoringProfile,
    SNMPPortBinding,
)


class SNMPMonitoringProfileForm(forms.ModelForm):
    community = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Obrigatória na criação. Em edição, deixe em branco para manter a atual.",
    )

    class Meta:
        model = SNMPMonitoringProfile
        fields = (
            "element", "equipment", "enabled", "management_ip", "port",
            "snmp_version", "polling_interval_seconds", "aggregate_policy",
        )

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk and not cleaned.get("community"):
            self.add_error("community", "Informe a community SNMP na criação.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        raw_community = self.cleaned_data.get("community")
        if raw_community:
            instance.set_community(raw_community)
        if commit:
            instance.save()
        return instance


class SNMPPortBindingInline(admin.TabularInline):
    model = SNMPPortBinding
    extra = 0
    fields = (
        "equipment_port", "label", "if_name", "if_index", "role",
        "enabled", "expected_up", "alert_enabled", "last_status", "last_seen_at",
    )
    readonly_fields = ("last_status", "last_seen_at")


@admin.register(SNMPMonitoringProfile)
class SNMPMonitoringProfileAdmin(admin.ModelAdmin):
    form = SNMPMonitoringProfileForm
    list_display = (
        "target_name", "company", "management_ip", "aggregate_policy",
        "last_status", "enabled", "last_poll_at",
    )
    list_filter = ("enabled", "aggregate_policy", "last_status", "company")
    search_fields = (
        "element__name", "equipment__name", "management_ip", "influx_id",
    )
    readonly_fields = (
        "influx_id", "last_status", "last_poll_at", "last_success_at", "last_poll_message",
    )
    inlines = [SNMPPortBindingInline]

    @admin.display(description="Ativo")
    def target_name(self, obj):
        return obj.target_name


@admin.register(SNMPInterfaceState)
class SNMPInterfaceStateAdmin(admin.ModelAdmin):
    list_display = (
        "profile", "if_name", "if_index", "if_alias", "status", "last_seen_at",
    )
    list_filter = ("status", "company")
    search_fields = ("profile__equipment__name", "profile__element__name", "if_name", "if_alias")
    readonly_fields = (
        "profile", "company", "interface_key", "if_name", "if_index", "if_alias",
        "status", "raw_status", "last_seen_at", "status_changed_at", "metadata",
    )

    def has_add_permission(self, request):
        return False


@admin.register(SNMPPortBinding)
class SNMPPortBindingAdmin(admin.ModelAdmin):
    list_display = (
        "display_name", "role", "if_name", "if_index", "last_status",
        "last_seen_at", "enabled", "alert_enabled",
    )
    list_filter = ("role", "last_status", "enabled", "alert_enabled", "company")
    search_fields = (
        "profile__equipment__name", "profile__element__name", "equipment_port__label",
        "if_name", "label",
    )
    readonly_fields = ("last_status", "last_seen_at", "status_changed_at", "down_since", "up_since")


@admin.register(MonitoredNetworkLink)
class MonitoredNetworkLinkAdmin(admin.ModelAdmin):
    list_display = (
        "name", "project", "link_type", "source_element", "destination_element",
        "status", "enabled", "last_evaluated_at",
    )
    list_filter = ("link_type", "status", "enabled", "severity", "company")
    search_fields = (
        "name", "code", "project__name", "source_element__name",
        "destination_element__name", "cable__name",
    )
    autocomplete_fields = (
        "project", "source_element", "destination_element", "source_binding",
        "destination_binding", "cable",
    )
    readonly_fields = (
        "status", "candidate_status", "candidate_since", "status_changed_at",
        "last_evaluated_at", "last_message",
    )
