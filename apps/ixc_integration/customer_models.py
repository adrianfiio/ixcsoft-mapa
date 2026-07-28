from django.db import models
from apps.core.enums import OperationalStatus
from apps.core.models import TimeStampedModel


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


class IXCLogin(TimeStampedModel):
    ixc_login_id = models.CharField(max_length=80, unique=True)
    customer = models.ForeignKey(IXCCustomer, on_delete=models.CASCADE, related_name="logins")
    username = models.CharField(max_length=180, db_index=True)
    status = models.CharField(max_length=20, choices=OperationalStatus.choices, default=OperationalStatus.NO_DATA)
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
