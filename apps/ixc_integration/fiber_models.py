from django.db import models

from apps.core.models import TimeStampedModel


class IXCFiberAssignment(TimeStampedModel):
    """Espelho do endpoint radpop_radio_cliente_fibra do IXCSoft."""

    company = models.ForeignKey("core.Company", on_delete=models.CASCADE, related_name="ixc_fiber_assignments", null=True, blank=True)
    ixc_id = models.CharField(max_length=80, db_index=True)
    login = models.ForeignKey(
        "ixc_integration.IXCLogin",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fiber_assignments",
    )
    cto = models.ForeignKey(
        "network_map.CTO",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ixc_fiber_assignments",
    )
    onu = models.ForeignKey(
        "olt_integration.ONU",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ixc_fiber_assignments",
    )

    ixc_login_id = models.CharField(max_length=80, blank=True, db_index=True)
    ixc_project_id = models.CharField(max_length=80, blank=True, db_index=True)
    ixc_cto_id = models.CharField(max_length=80, blank=True, db_index=True)
    ixc_transmitter_id = models.CharField(max_length=80, blank=True)
    ixc_contract_id = models.CharField(max_length=80, blank=True)
    ixc_hardware_id = models.CharField(max_length=80, blank=True)

    name = models.CharField(max_length=180, blank=True)
    mac_address = models.CharField(max_length=32, blank=True, db_index=True)
    pon_id = models.CharField(max_length=80, blank=True)
    slot_number = models.CharField(max_length=30, blank=True)
    pon_number = models.CharField(max_length=30, blank=True)
    onu_number = models.CharField(max_length=30, blank=True)
    onu_type = models.CharField(max_length=120, blank=True)
    vlan = models.CharField(max_length=30, blank=True)
    vlan_pppoe = models.CharField(max_length=30, blank=True)
    vlan_dhcp = models.CharField(max_length=30, blank=True)
    gemport = models.CharField(max_length=30, blank=True)
    service_port = models.CharField(max_length=30, blank=True)
    cto_port = models.CharField(max_length=30, blank=True)

    rx_power = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    tx_power = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    temperature = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    voltage = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    distance_meters = models.PositiveIntegerField(null=True, blank=True)
    last_signal_at = models.DateTimeField(null=True, blank=True)
    last_down_cause = models.CharField(max_length=255, blank=True)

    management_ip = models.GenericIPAddressField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    city = models.CharField(max_length=120, blank=True)
    neighborhood = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=255, blank=True)
    number = models.CharField(max_length=30, blank=True)
    complement = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    reference = models.CharField(max_length=255, blank=True)

    raw_data = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name", "ixc_id"]
        indexes = [
            models.Index(fields=["ixc_cto_id", "ixc_login_id"]),
            models.Index(fields=["mac_address", "onu_number"]),
            models.Index(fields=["ixc_project_id"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=("company", "ixc_id"), name="unique_ixc_fiber_per_company")
        ]

    def __str__(self):
        return self.name or f"Fibra IXC {self.ixc_id}"
