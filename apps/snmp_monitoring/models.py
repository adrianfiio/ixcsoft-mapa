import uuid

from django.db import models

from apps.core.crypto import SecretCipher
from apps.core.models import CompanyScopedModel


def _generate_influx_id():
    return uuid.uuid4().hex


class SNMPMonitoringProfile(CompanyScopedModel):
    """Config de coleta SNMP (Telegraf/InfluxDB) de um elemento do mapa.

    ``influx_id`` é o identificador estável usado na tag ``equipamento_id``
    do InfluxDB e no nome do arquivo ``.conf`` do Telegraf — gerado uma vez
    na criação, nunca reaproveita PK de banco (não expõe IDs internos pra
    fora e continua válido mesmo se o elemento for recriado).
    """

    class SNMPVersion(models.TextChoices):
        V2C = "2c", "SNMP v2c"

    element = models.OneToOneField(
        "network_map.NetworkElement",
        on_delete=models.CASCADE,
        related_name="snmp_monitoring",
    )
    enabled = models.BooleanField(default=True)
    management_ip = models.GenericIPAddressField()
    port = models.PositiveIntegerField(default=161)
    snmp_version = models.CharField(max_length=10, choices=SNMPVersion.choices, default=SNMPVersion.V2C)
    community_encrypted = models.TextField(blank=True)
    polling_interval_seconds = models.PositiveIntegerField(default=60)
    influx_id = models.CharField(max_length=32, unique=True, editable=False, default=_generate_influx_id)
    last_poll_at = models.DateTimeField(null=True, blank=True)
    last_poll_message = models.TextField(blank=True)

    class Meta:
        verbose_name = "Monitoramento SNMP"
        verbose_name_plural = "Monitoramentos SNMP"
        indexes = [
            models.Index(fields=["enabled"]),
        ]

    def __str__(self):
        return f"SNMP · {self.element.name} ({self.management_ip})"

    def save(self, *args, **kwargs):
        if self.element_id and not self.company_id:
            self.company_id = self.element.company_id
        super().save(*args, **kwargs)

    def set_community(self, raw_value):
        self.community_encrypted = SecretCipher().encrypt(raw_value) if raw_value else ""

    def get_community(self):
        return SecretCipher().decrypt(self.community_encrypted) if self.community_encrypted else ""

    @property
    def conf_filename(self):
        return f"element_{self.influx_id}.conf"
