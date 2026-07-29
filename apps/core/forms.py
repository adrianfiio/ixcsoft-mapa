from django import forms

from .crypto import SecretCipher
from .models import MapBaseConfiguration


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
