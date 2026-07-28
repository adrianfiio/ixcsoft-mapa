from django.db import models
from apps.core.models import TimeStampedModel


class IXCConfiguration(TimeStampedModel):
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
        return self.name


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
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
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

    def __str__(self):
        return f"{self.configuration} - {self.started_at:%d/%m/%Y %H:%M}"
