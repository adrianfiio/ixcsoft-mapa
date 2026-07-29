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
    integration_mode = models.CharField(
        max_length=20,
        choices=IntegrationMode.choices,
        blank=True,
    )
    onboarding_completed = models.BooleanField(default=False)
    slug = models.SlugField(max_length=180, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ["name"]

    def __str__(self):
        return self.trade_name or self.name


class CompanyMembership(TimeStampedModel):
    class Role(models.TextChoices):
        VIEW = "view", "VIEW — somente visualizar"
        EDIT = "edit", "EDIT — visualizar e editar"

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
