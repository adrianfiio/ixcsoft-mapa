from django import forms

from apps.ixc_integration.models import IXCConfiguration
from apps.ixc_integration.services.configuration import encrypt_secret


class IXCConfigurationAdminForm(forms.ModelForm):
    api_token = forms.CharField(
        label="Token da API",
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={
                "autocomplete": "new-password",
                "placeholder": "Deixe em branco para manter o token atual",
            },
        ),
        help_text="O token será armazenado de forma criptografada.",
    )

    class Meta:
        model = IXCConfiguration
        exclude = ("api_token_encrypted",)

    def clean_api_token(self):
        token = self.cleaned_data.get("api_token", "").strip()

        if not self.instance.pk and not token:
            raise forms.ValidationError(
                "Informe o token da API para criar a configuração."
            )

        return token

    def save(self, commit=True):
        instance = super().save(commit=False)
        token = self.cleaned_data.get("api_token")

        if token:
            instance.api_token_encrypted = encrypt_secret(token)

        if commit:
            instance.save()
            self.save_m2m()

        return instance
