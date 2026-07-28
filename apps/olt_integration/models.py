from django.db import models
from apps.core.enums import OperationalStatus
from apps.core.models import NamedModel, TimeStampedModel


class OLT(NamedModel):
    class Vendor(models.TextChoices):
        FIBERHOME = "fiberhome", "FiberHome"
        HUAWEI = "huawei", "Huawei"
        ZTE = "zte", "ZTE"
        OTHER = "other", "Outro"

    class SNMPVersion(models.TextChoices):
        V2C = "2c", "SNMP v2c"
        V3 = "3", "SNMP v3"

    hostname = models.CharField(max_length=120, blank=True)
    management_ip = models.GenericIPAddressField(unique=True)
    vendor = models.CharField(max_length=30, choices=Vendor.choices, default=Vendor.FIBERHOME)
    model = models.CharField(max_length=120, blank=True)
    serial_number = models.CharField(max_length=120, blank=True)
    snmp_version = models.CharField(max_length=10, choices=SNMPVersion.choices, default=SNMPVersion.V2C)
    snmp_port = models.PositiveIntegerField(default=161)
    snmp_community_encrypted = models.TextField(blank=True)
    snmp_username = models.CharField(max_length=120, blank=True)
    snmp_auth_key_encrypted = models.TextField(blank=True)
    snmp_priv_key_encrypted = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    polling_interval_seconds = models.PositiveIntegerField(default=120)
    status = models.CharField(max_length=20, choices=OperationalStatus.choices, default=OperationalStatus.NO_DATA)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_poll_at = models.DateTimeField(null=True, blank=True)
    last_poll_message = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["enabled", "status"]),
            models.Index(fields=["vendor", "model"]),
        ]


class PONPort(TimeStampedModel):
    olt = models.ForeignKey(OLT, on_delete=models.CASCADE, related_name="pon_ports")
    frame = models.PositiveSmallIntegerField(default=0)
    slot = models.PositiveSmallIntegerField()
    port = models.PositiveSmallIntegerField()
    interface_name = models.CharField(max_length=120, blank=True)
    description = models.CharField(max_length=255, blank=True)
    capacity = models.PositiveSmallIntegerField(default=128)
    status = models.CharField(max_length=20, choices=OperationalStatus.choices, default=OperationalStatus.NO_DATA)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["olt", "frame", "slot", "port"]
        constraints = [
            models.UniqueConstraint(
                fields=["olt", "frame", "slot", "port"],
                name="unique_olt_frame_slot_port",
            )
        ]
        indexes = [
            models.Index(fields=["olt", "status"]),
        ]

    def __str__(self):
        return f"{self.olt.name} {self.frame}/{self.slot}/{self.port}"


class ONU(TimeStampedModel):
    class RegistrationStatus(models.TextChoices):
        REGISTERED = "registered", "Registrada"
        UNREGISTERED = "unregistered", "Não registrada"
        UNKNOWN = "unknown", "Desconhecida"

    pon_port = models.ForeignKey(PONPort, on_delete=models.CASCADE, related_name="onus")
    onu_id = models.PositiveSmallIntegerField()
    serial_number = models.CharField(max_length=120, blank=True, db_index=True)
    mac_address = models.CharField(max_length=32, blank=True, db_index=True)
    model = models.CharField(max_length=120, blank=True)
    firmware_version = models.CharField(max_length=120, blank=True)
    registration_status = models.CharField(
        max_length=20,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.UNKNOWN,
    )
    operational_status = models.CharField(
        max_length=20,
        choices=OperationalStatus.choices,
        default=OperationalStatus.NO_DATA,
    )
    los = models.BooleanField(default=False)
    rx_power = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    tx_power = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    temperature = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    voltage = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    distance_meters = models.PositiveIntegerField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_collected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["pon_port", "onu_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["pon_port", "onu_id"],
                name="unique_onu_per_pon",
            )
        ]
        indexes = [
            models.Index(fields=["operational_status", "los"]),
            models.Index(fields=["pon_port", "operational_status"]),
            models.Index(fields=["last_collected_at"]),
        ]

    def __str__(self):
        return f"{self.pon_port} ONU {self.onu_id}"


class ONUSignalHistory(TimeStampedModel):
    onu = models.ForeignKey(ONU, on_delete=models.CASCADE, related_name="signal_history")
    collected_at = models.DateTimeField(db_index=True)
    operational_status = models.CharField(max_length=20, choices=OperationalStatus.choices)
    los = models.BooleanField(default=False)
    rx_power = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    tx_power = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    temperature = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    voltage = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    source = models.CharField(max_length=30, default="snmp")

    class Meta:
        ordering = ["-collected_at"]
        indexes = [
            models.Index(fields=["onu", "-collected_at"]),
            models.Index(fields=["operational_status", "-collected_at"]),
        ]

    def __str__(self):
        return f"{self.onu} - {self.collected_at:%d/%m/%Y %H:%M}"
