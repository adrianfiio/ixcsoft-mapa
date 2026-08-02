from django.db import models
from apps.core.enums import OperationalStatus, Severity
from apps.core.models import TimeStampedModel


class AlertRule(TimeStampedModel):
    class Scope(models.TextChoices):
        ONU = "onu", "ONU"
        CTO = "cto", "CTO"
        ROUTE = "route", "Rota"
        PON = "pon", "Porta PON"
        OLT = "olt", "OLT"
        EQUIPMENT = "equipment", "Equipamento"
        PORT = "port", "Porta monitorada"
        LINK = "link", "Enlace monitorado"
        SYSTEM = "system", "Sistema"

    name = models.CharField(max_length=180)
    scope = models.CharField(max_length=20, choices=Scope.choices)
    enabled = models.BooleanField(default=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.HIGH)
    persistence_seconds = models.PositiveIntegerField(default=180)
    recovery_seconds = models.PositiveIntegerField(default=300)
    configuration = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["scope", "name"]

    def __str__(self):
        return self.name


class AlertEvent(TimeStampedModel):
    class State(models.TextChoices):
        OPEN = "open", "Aberto"
        ACKNOWLEDGED = "acknowledged", "Reconhecido"
        RECOVERING = "recovering", "Recuperando"
        CLOSED = "closed", "Fechado"
        SUPPRESSED = "suppressed", "Suprimido"

    fingerprint = models.CharField(max_length=255, unique=True)
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alert_events",
    )
    rule = models.ForeignKey(AlertRule, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    scope = models.CharField(max_length=20, choices=AlertRule.Scope.choices)
    severity = models.CharField(max_length=20, choices=Severity.choices)
    state = models.CharField(max_length=20, choices=State.choices, default=State.OPEN)
    source_status = models.CharField(max_length=20, choices=OperationalStatus.choices, default=OperationalStatus.OFFLINE)
    olt = models.ForeignKey("olt_integration.OLT", on_delete=models.SET_NULL, null=True, blank=True)
    pon_port = models.ForeignKey("olt_integration.PONPort", on_delete=models.SET_NULL, null=True, blank=True)
    onu = models.ForeignKey("olt_integration.ONU", on_delete=models.SET_NULL, null=True, blank=True)
    cto = models.ForeignKey("network_map.CTO", on_delete=models.SET_NULL, null=True, blank=True)
    route = models.ForeignKey("network_map.NetworkRoute", on_delete=models.SET_NULL, null=True, blank=True)
    network_element = models.ForeignKey(
        "network_map.NetworkElement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="monitoring_alerts",
    )
    container_equipment = models.ForeignKey(
        "network_map.ContainerEquipment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="monitoring_alerts",
    )
    equipment_port = models.ForeignKey(
        "network_map.ContainerEquipmentPort",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="monitoring_alerts",
    )
    monitored_link = models.ForeignKey(
        "snmp_monitoring.MonitoredNetworkLink",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )
    opened_at = models.DateTimeField()
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acknowledged_alerts",
    )
    recovery_started_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    affected_onus = models.PositiveIntegerField(default=0)
    affected_ctos = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    zabbix_sent = models.BooleanField(default=False)
    telegram_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["state", "severity", "-opened_at"]),
            models.Index(fields=["scope", "state"]),
            models.Index(fields=["cto", "state"]),
            models.Index(fields=["route", "state"]),
            models.Index(fields=["company", "state", "-opened_at"], name="alerts_company_state_idx"),
            models.Index(fields=["monitored_link", "state"], name="alerts_link_state_idx"),
            models.Index(fields=["equipment_port", "state"], name="alerts_port_state_idx"),
        ]

    def __str__(self):
        return self.title


class AlertNotification(TimeStampedModel):
    class Channel(models.TextChoices):
        ZABBIX = "zabbix", "Zabbix"
        TELEGRAM = "telegram", "Telegram"
        EMAIL = "email", "E-mail"
        WEBHOOK = "webhook", "Webhook"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        SENT = "sent", "Enviado"
        FAILED = "failed", "Falhou"

    alert = models.ForeignKey(AlertEvent, on_delete=models.CASCADE, related_name="notifications")
    channel = models.CharField(max_length=20, choices=Channel.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    response_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
