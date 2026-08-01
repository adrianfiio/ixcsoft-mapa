from django import forms
from django.contrib import admin

from .models import SNMPMonitoringProfile


class SNMPMonitoringProfileForm(forms.ModelForm):
    community = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Deixe em branco pra manter a community atual.",
    )

    class Meta:
        model = SNMPMonitoringProfile
        fields = ("element", "enabled", "management_ip", "port", "snmp_version", "polling_interval_seconds")

    def save(self, commit=True):
        instance = super().save(commit=False)
        raw_community = self.cleaned_data.get("community")
        if raw_community:
            instance.set_community(raw_community)
        if commit:
            instance.save()
        return instance


@admin.register(SNMPMonitoringProfile)
class SNMPMonitoringProfileAdmin(admin.ModelAdmin):
    form = SNMPMonitoringProfileForm
    list_display = ("element", "company", "management_ip", "enabled", "last_poll_at", "last_poll_message")
    list_filter = ("enabled", "company")
    search_fields = ("element__name", "management_ip", "influx_id")
    readonly_fields = ("influx_id", "last_poll_at", "last_poll_message")
