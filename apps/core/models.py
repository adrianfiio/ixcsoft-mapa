from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CompanyScopedModel(TimeStampedModel):
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


class NamedModel(TimeStampedModel):
    name = models.CharField(max_length=180, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Company(TimeStampedModel):
    class CompanyType(models.TextChoices):
        PROVIDER = "provider", "Provedor (ISP, com clientes)"
        DESIGNER = "designer", "Projetista (sem clientes)"

    class IntegrationMode(models.TextChoices):
        ERP = "erp", "Usar com ERP"
        MANUAL = "manual", "Usar sem ERP"

    name = models.CharField(max_length=180)
    trade_name = models.CharField(max_length=180, blank=True)
    document = models.CharField(max_length=30, blank=True)
    contact_name = models.CharField(max_length=180, blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    contact_email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    company_type = models.CharField(
        max_length=20,
        choices=CompanyType.choices,
        blank=True,
        verbose_name="Tipo de empresa",
        help_text=(
            "Definido pela empresa no primeiro acesso. Depois de definido, só o "
            "suporte da plataforma pode alterar (planos possuem custos diferentes)."
        ),
    )
    integration_mode = models.CharField(
        max_length=20,
        choices=IntegrationMode.choices,
        blank=True,
    )
    onboarding_completed = models.BooleanField(default=False)
    slug = models.SlugField(max_length=180, unique=True)
    active = models.BooleanField(default=True)
    logo = models.ImageField(
        upload_to="company_logos/",
        blank=True,
        null=True,
        verbose_name="Logo (whitelabel)",
        help_text="Substitui a logo padrão na barra lateral para os usuários desta empresa.",
    )
    brand_color = models.CharField(
        max_length=7,
        blank=True,
        default="",
        verbose_name="Cor de destaque (whitelabel)",
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Use o formato #RRGGBB.")],
        help_text="Substitui a cor de destaque padrão para os usuários desta empresa.",
    )

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ["name"]

    def __str__(self):
        return self.trade_name or self.name

    @property
    def is_designer(self):
        return self.company_type == self.CompanyType.DESIGNER

    @property
    def is_provider(self):
        return self.company_type == self.CompanyType.PROVIDER

    @property
    def needs_type_choice(self):
        return not self.company_type

    @property
    def needs_provider_mode_choice(self):
        return self.is_provider and not self.integration_mode


class CompanyEmailConfiguration(TimeStampedModel):
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="email_configuration",
    )
    host = models.CharField(max_length=255, verbose_name="Servidor SMTP")
    port = models.PositiveIntegerField(default=587, verbose_name="Porta")
    username = models.CharField(max_length=255, blank=True, verbose_name="Usuário")
    password_encrypted = models.TextField(blank=True, editable=False)
    use_tls = models.BooleanField(default=True, verbose_name="Usar TLS")
    from_email = models.EmailField(verbose_name="E-mail remetente")
    enabled = models.BooleanField(default=True, verbose_name="Integração ativa")

    class Meta:
        verbose_name = "Configuração de e-mail (SMTP)"
        verbose_name_plural = "Configurações de e-mail (SMTP)"

    def __str__(self):
        return f"SMTP · {self.company}"


class CompanyMembership(TimeStampedModel):
    class Role(models.TextChoices):
        VIEW = "view", "VIEW — somente visualizar"
        EDIT = "edit", "EDIT — visualizar e editar"
        ADMIN = "admin", "ADMIN — administrar a empresa"
        TECHNICIAN = "technician", "Técnico — aplicativo de campo"

    class DataSource(models.TextChoices):
        MANUAL = "manual", "Usuário padrão — sem ERP"
        ERP = "erp", "Usuário vinculado a ERP"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Empresa",
    )
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="company_memberships",
        verbose_name="Usuário",
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.EDIT,
        verbose_name="Nível de acesso",
    )
    active = models.BooleanField(default=True, verbose_name="Acesso ativo")
    data_source = models.CharField(
        max_length=20,
        choices=DataSource.choices,
        default=DataSource.MANUAL,
        verbose_name="Origem dos dados",
    )
    erp_provider = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="ERP vinculado",
        help_text="Informe o provedor somente para usuários vinculados a ERP.",
    )
    erp_configuration_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name="ID da configuração ERP",
    )

    class Meta:
        verbose_name = "Acesso à empresa"
        verbose_name_plural = "Acessos às empresas"
        constraints = [
            models.UniqueConstraint(
                fields=("company", "user"),
                name="core_unique_company_user_membership",
            ),
        ]
        ordering = ("company__name", "user__username")

    def __str__(self):
        return f"{self.user} · {self.company} · {self.get_role_display()}"


class MapBaseConfiguration(TimeStampedModel):
    class DefaultLayer(models.TextChoices):
        GOOGLE_SATELLITE = "google_satellite", "Google Satélite"
        ESRI_SATELLITE = "esri_satellite", "Satélite alternativo"
        OPENSTREETMAP = "openstreetmap", "Mapa de ruas"

    name = models.CharField(max_length=120, default="Mapa principal")
    google_tiles_enabled = models.BooleanField(
        default=False,
        verbose_name="Ativar Google Map Tiles",
    )
    google_api_key_encrypted = models.TextField(blank=True, editable=False)
    default_layer = models.CharField(
        max_length=30,
        choices=DefaultLayer.choices,
        default=DefaultLayer.GOOGLE_SATELLITE,
        verbose_name="Camada padrão",
    )

    class Meta:
        verbose_name = "Configuração do mapa-base"
        verbose_name_plural = "Configuração do mapa-base"

    def __str__(self):
        return self.name


class CompanyDashboardLayout(TimeStampedModel):
    """Personalização da visão geral de uma empresa: posição, tamanho e
    visibilidade dos cartões/painéis (grid livre, tipo Zabbix/Grafana), e
    uma mensagem opcional no topo. Editável tanto por um membro EDIT da
    própria empresa (autoatendimento) quanto pelo superusuário via
    `/painel/dashboards/<empresa>/`."""

    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="dashboard_layout",
    )
    widget_layout = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Posição/tamanho/visibilidade de cada widget do dashboard dessa "
            'empresa: {"chave": {"x": 0, "y": 0, "w": 3, "h": 2, "hidden": false}}.'
        ),
    )
    banner_text = models.CharField(
        max_length=280,
        blank=True,
        verbose_name="Mensagem no topo do dashboard",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = "Layout de dashboard da empresa"
        verbose_name_plural = "Layouts de dashboard das empresas"


class PlatformDashboardLayout(TimeStampedModel):
    """Personalização admin-only da "Visão da plataforma" — mesma ideia de
    `CompanyDashboardLayout`, mas sem empresa dona: é o layout da própria
    plataforma. Sempre existe no máximo uma linha (singleton)."""

    widget_layout = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Posição/tamanho/visibilidade de cada widget da visão da "
            'plataforma: {"chave": {"x": 0, "y": 0, "w": 3, "h": 2, "hidden": false}}.'
        ),
    )
    banner_text = models.CharField(
        max_length=280,
        blank=True,
        verbose_name="Mensagem no topo da visão da plataforma",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = "Layout da visão da plataforma"
        verbose_name_plural = "Layout da visão da plataforma"

    def __str__(self):
        return f"Layout · {self.company}"
