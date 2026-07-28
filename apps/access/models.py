from django.db import models

from apps.core.models import CompanyScopedModel


class AccessPoint(CompanyScopedModel):
    """
    Representa um assinante/conexão de acesso da rede.

    Não pertence ao ERP.
    O ERP apenas alimenta este cadastro.
    """

    class Status(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        UNKNOWN = "unknown", "Desconhecido"

    source = models.CharField(
        max_length=50,
        default="ixc",
        db_index=True,
        verbose_name="Origem",
    )

    external_id = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="ID externo",
    )

    ixc_customer_id = models.CharField(
        max_length=80,
        blank=True,
        db_index=True,
        verbose_name="ID Cliente IXC",
    )

    ixc_contract_id = models.CharField(
        max_length=80,
        blank=True,
        db_index=True,
        verbose_name="ID Contrato IXC",
    )

    username = models.CharField(
        max_length=180,
        blank=True,
        db_index=True,
        verbose_name="Login PPPoE",
    )

    customer_name = models.CharField(
        max_length=180,
        blank=True,
        verbose_name="Cliente",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNKNOWN,
        db_index=True,
    )

    online = models.BooleanField(
        default=False,
        db_index=True,
    )

    #
    # Localização
    #

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    #
    # Dados FTTH vindos do IXC
    #

    onu_mac = models.CharField(
        max_length=80,
        blank=True,
        db_index=True,
        verbose_name="MAC ONU",
    )

    cto_ixc_id = models.CharField(
        max_length=80,
        blank=True,
        db_index=True,
        verbose_name="ID CTO IXC",
    )

    ftth_port = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Porta FTTH",
    )

    concentrator_id = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="ID Concentrador",
    )

    concentrator = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Concentrador",
    )

    interface_transmission = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Interface transmissão",
    )

    connection_type = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="Tipo conexão",
    )

    #
    # Sessão PPPoE
    #

    last_connection_start = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_connection_end = models.DateTimeField(
        null=True,
        blank=True,
    )

    disconnect_reason = models.CharField(
        max_length=255,
        blank=True,
    )

    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    raw_data = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        verbose_name = "Ponto de acesso"
        verbose_name_plural = "Pontos de acesso"
        ordering = ["customer_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "source", "external_id"],
                name="unique_accesspoint_source_external",
            )
        ]
        indexes = [
            models.Index(fields=["company", "online"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["onu_mac"]),
            models.Index(fields=["cto_ixc_id"]),
        ]

    def __str__(self):
        return self.username or self.customer_name or self.external_id
