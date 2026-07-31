from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .crypto import SecretCipher
from .models import Company, CompanyEmailConfiguration, CompanyMembership, MapBaseConfiguration
from apps.network_map.models import NetworkProject, POP
from apps.olt_integration.models import OLT
from apps.optical.models import DIO
from apps.ixc_integration.models import IXCConfiguration
from apps.ixc_integration.services.configuration import encrypt_secret
from django.contrib.gis.geos import Point


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
    latitude = forms.DecimalField(required=True, min_value=-90, max_value=90, decimal_places=7)
    longitude = forms.DecimalField(required=True, min_value=-180, max_value=180, decimal_places=7)

    class Meta:
        model = POP
        fields = (
            "company", "project", "name", "code", "address", "city",
            "latitude", "longitude", "enabled",
        )

    def __init__(self, *args, company_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].required = True
        if company_ids is not None:
            self.fields["company"].queryset = self.fields["company"].queryset.filter(id__in=company_ids)
            self.fields["project"].queryset = NetworkProject.objects.filter(company_id__in=company_ids)
            if len(company_ids) == 1:
                self.fields["company"].initial = company_ids[0]

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.point = Point(
            float(self.cleaned_data["longitude"]),
            float(self.cleaned_data["latitude"]),
            srid=4326,
        )
        if commit:
            instance.save()
            self.save_m2m()
        return instance


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


class ERPOnboardingForm(forms.ModelForm):
    api_token = forms.CharField(
        label="Token da API",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="O token será armazenado criptografado.",
    )

    class Meta:
        model = IXCConfiguration
        fields = (
            "company", "provider", "name", "base_url", "api_token", "verify_ssl",
            "sync_active_contracts_only", "sync_customers", "sync_pppoe",
            "sync_projects", "sync_ctos", "sync_map_elements",
            "sync_interval_minutes", "enabled",
        )
        labels = {
            "company": "Empresa",
            "provider": "ERP",
            "name": "Nome da integração",
            "base_url": "Endereço da API",
            "verify_ssl": "Verificar certificado SSL",
            "sync_active_contracts_only": "Somente contratos ativos",
            "sync_customers": "Importar clientes",
            "sync_pppoe": "Importar logins PPPoE",
            "sync_projects": "Importar projetos",
            "sync_ctos": "Importar CTOs e caixas",
            "sync_map_elements": "Importar elementos do mapa",
            "sync_interval_minutes": "Intervalo automático em minutos",
            "enabled": "Integração ativa",
        }

    def __init__(self, *args, company_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["api_token"].required = False
            self.fields["api_token"].widget.attrs["placeholder"] = "Deixe em branco para manter o token atual"
        self.fields["company"].required = True
        if company_ids is not None:
            self.fields["company"].queryset = self.fields["company"].queryset.filter(id__in=company_ids)
            if len(company_ids) == 1:
                self.fields["company"].initial = company_ids[0]

    def save(self, commit=True):
        instance = super().save(commit=False)
        token = self.cleaned_data.get("api_token", "").strip()
        if token:
            instance.api_token_encrypted = encrypt_secret(token)
        if commit:
            instance.save()
        return instance


class CompanyOnboardingForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = (
            "name", "trade_name", "document", "contact_name", "contact_phone",
            "contact_email", "address", "company_type",
        )
        labels = {
            "name": "Razão social ou nome",
            "trade_name": "Nome fantasia",
            "document": "CPF ou CNPJ",
            "contact_name": "Pessoa de contato",
            "contact_phone": "Telefone / WhatsApp",
            "contact_email": "E-mail",
            "address": "Endereço",
            "company_type": "Como sua empresa vai operar?",
        }

    def __init__(self, *args, lock_company_type=False, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("name", "document", "contact_name", "contact_phone", "contact_email", "address", "company_type"):
            self.fields[name].required = True
        if lock_company_type:
            # Depois de escolhido, o tipo só muda pelo suporte (via Django Admin) —
            # planos de provedor e projetista têm custo mensal diferente.
            self.fields["company_type"].disabled = True


class CompanyProviderModeForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ("integration_mode",)
        labels = {
            "integration_mode": "Como deseja começar?",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["integration_mode"].required = True


class CompanyTeamMemberForm(forms.Form):
    first_name = forms.CharField(label="Nome", max_length=150)
    username = forms.CharField(label="Usuário de acesso", max_length=150)
    password = forms.CharField(label="Senha", widget=forms.PasswordInput)
    role = forms.ChoiceField(label="Nível de acesso", choices=CompanyMembership.Role.choices)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Já existe um usuário com este nome de acesso.")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password


class CompanyEmailConfigurationForm(forms.ModelForm):
    password = forms.CharField(
        label="Senha",
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Armazenada criptografada.",
    )

    class Meta:
        model = CompanyEmailConfiguration
        fields = ("host", "port", "username", "password", "use_tls", "from_email", "enabled")
        labels = {
            "host": "Servidor SMTP",
            "port": "Porta",
            "username": "Usuário",
            "use_tls": "Usar TLS",
            "from_email": "E-mail remetente",
            "enabled": "Integração ativa",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["host"].required = True
        self.fields["from_email"].required = True
        if self.instance and self.instance.pk:
            self.fields["password"].widget.attrs["placeholder"] = "Deixe em branco para manter a senha atual"

    def save(self, commit=True):
        instance = super().save(commit=False)
        password = self.cleaned_data.get("password", "").strip()
        if password:
            instance.password_encrypted = SecretCipher().encrypt(password)
        if commit:
            instance.save()
        return instance


class CompanyBrandingForm(forms.ModelForm):
    MAX_LOGO_SIZE = 2 * 1024 * 1024

    class Meta:
        model = Company
        fields = ("logo", "brand_color")
        labels = {
            "logo": "Logo",
            "brand_color": "Cor de destaque",
        }
        widgets = {
            "brand_color": forms.TextInput(attrs={"type": "color"}),
        }

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if logo and hasattr(logo, "size") and logo.size > self.MAX_LOGO_SIZE:
            raise forms.ValidationError("A logo deve ter no máximo 2MB.")
        return logo
