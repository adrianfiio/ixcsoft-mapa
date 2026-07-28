from django.db import models

from apps.core.enums import OperationalStatus
from apps.core.models import TimeStampedModel


class IXCConfiguration(TimeStampedModel):
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="ixc_configurations",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120, default="IXCSoft principal")
    base_url = models.URLField()
    api_token_encrypted = models.TextField(blank=True)
    verify_ssl = models.BooleanField(default=True)
    sync_interval_minutes = models.PositiveSmallIntegerField(default=5)
    enabled = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(max_length=30, blank=True)
    last_sync_message = models.TextField(blank=True)

    class Meta:
        verbose_name = "Configuração IXCSoft"
        verbose_name_plural = "Configurações IXCSoft"

    def __str__(self):
        return f"{self.company} - {self.name}"


class IXCSyncExecution(TimeStampedModel):
    class Status(models.TextChoices):
        RUNNING = "running", "Executando"
        SUCCESS = "success", "Sucesso"
        FAILED = "failed", "Falhou"
        PARTIAL = "partial", "Parcial"

    configuration = models.ForeignKey(
        IXCConfiguration,
        on_delete=models.CASCADE,
        related_name="executions",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RUNNING,
    )
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    records_received = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    records_failed = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["configuration", "-started_at"]),
            models.Index(fields=["status", "-started_at"]),
        ]


class IXCCustomer(TimeStampedModel):
    ixc_customer_id = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=180, db_index=True)
    document = models.CharField(max_length=30, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    active = models.BooleanField(default=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class IXCLogin(TimeStampedModel):
    ixc_login_id = models.CharField(max_length=80, unique=True)
    customer = models.ForeignKey(
        IXCCustomer,
        on_delete=models.CASCADE,
        related_name="logins",
    )
    username = models.CharField(max_length=180, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=OperationalStatus.choices,
        default=OperationalStatus.NO_DATA,
    )
    online = models.BooleanField(default=False)
    cto = models.ForeignKey(
        "network_map.CTO",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ixc_logins",
    )
    onu = models.OneToOneField(
        "olt_integration.ONU",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ixc_login",
    )
    last_online_at = models.DateTimeField(null=True, blank=True)
    last_offline_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["username"]
        indexes = [
            models.Index(fields=["cto", "online"]),
            models.Index(fields=["status", "online"]),
        ]

    def __str__(self):
        return self.username
