from django import forms

from .crypto import SecretCipher
from .models import MapBaseConfiguration
from apps.network_map.models import NetworkProject, POP
from apps.olt_integration.models import OLT
from apps.optical.models import DIO


class MapBaseConfigurationAdminForm(forms.ModelForm):
    google_api_key = forms.CharField(
        label="Chave da Google Map Tiles API",
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={
                "autocomplete": "new-password",
                "placeholder": "Deixe em branco para manter a chave atual",
            },
        ),
        help_text=(
            "Armazenada criptografada. Restrinja a chave à Map Tiles API "
            "e ao endereço IP público do servidor no Google Cloud."
        ),
    )

    class Meta:
        model = MapBaseConfiguration
        exclude = ("google_api_key_encrypted",)

    def clean(self):
        cleaned = super().clean()
        key = cleaned.get("google_api_key", "").strip()
        enabled = cleaned.get("google_tiles_enabled")
        if enabled and not key and not self.instance.google_api_key_encrypted:
            self.add_error(
                "google_api_key",
                "Informe a chave para ativar o Google Map Tiles.",
            )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        key = self.cleaned_data.get("google_api_key", "").strip()
        if key:
            instance.google_api_key_encrypted = SecretCipher().encrypt(key)
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class POPPlatformForm(forms.ModelForm):
    class Meta:
        model = POP
        fields = ("company", "project", "name", "code", "address", "city", "enabled")

    def __init__(self, *args, company_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].required = True
        if company_ids is not None:
            self.fields["company"].queryset = self.fields["company"].queryset.filter(id__in=company_ids)
            self.fields["project"].queryset = NetworkProject.objects.filter(company_id__in=company_ids)
            if len(company_ids) == 1:
                self.fields["company"].initial = company_ids[0]


class OLTPlatformForm(forms.ModelForm):
    class Meta:
        model = OLT
        fields = (
            "cpd", "name", "description", "provisioning_mode", "hostname",
            "management_ip", "vendor", "model", "serial_number", "enabled",
        )

    def __init__(self, *args, company_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company_ids is not None:
            self.fields["cpd"].queryset = POP.objects.filter(company_id__in=company_ids)


class DIOPlatformForm(forms.ModelForm):
    class Meta:
        model = DIO
        fields = (
            "pop", "project", "name", "code", "description", "manufacturer",
            "model", "serial_number", "connector_type", "tray_capacity",
            "port_capacity", "status", "enabled",
        )

    def __init__(self, *args, company_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company_ids is not None:
            self.fields["pop"].queryset = POP.objects.filter(company_id__in=company_ids)
            self.fields["project"].queryset = NetworkProject.objects.filter(company_id__in=company_ids)
