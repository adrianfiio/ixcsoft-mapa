from django.contrib.gis.db import models
from apps.core.enums import OperationalStatus
from apps.core.models import NamedModel, TimeStampedModel


class NetworkRoute(NamedModel):
    code = models.CharField(max_length=80, unique=True)
    geometry = models.MultiLineStringField(srid=4326, null=True, blank=True)
    status = models.CharField(max_length=20, choices=OperationalStatus.choices, default=OperationalStatus.NO_DATA)
    offline_cto_threshold = models.PositiveSmallIntegerField(default=2)
    offline_cto_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["status", "enabled"])]


class NetworkElement(NamedModel):
    class ElementType(models.TextChoices):
        OLT = "olt", "OLT"
        DIO = "dio", "DIO"
        SPLICE_BOX = "splice_box", "Caixa de emenda"
        CTO = "cto", "CTO"
        POLE = "pole", "Poste"
        CABINET = "cabinet", "Armário"
        OTHER = "other", "Outro"

    code = models.CharField(max_length=100, blank=True, db_index=True)
    element_type = models.CharField(max_length=30, choices=ElementType.choices)
    point = models.PointField(srid=4326, null=True, blank=True)
    status = models.CharField(max_length=20, choices=OperationalStatus.choices, default=OperationalStatus.NO_DATA)
    metadata = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["element_type", "name"]
        indexes = [
            models.Index(fields=["element_type", "status"]),
            models.Index(fields=["code"]),
        ]


class CTO(NetworkElement):
    ixc_box_id = models.CharField(max_length=80, unique=True, null=True, blank=True)
    route = models.ForeignKey(
        NetworkRoute,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ctos",
    )
    capacity = models.PositiveSmallIntegerField(default=16)
    splitter_ratio = models.CharField(max_length=30, blank=True)
    offline_onu_threshold = models.PositiveSmallIntegerField(default=3)
    offline_onu_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=60)
    los_onu_threshold = models.PositiveSmallIntegerField(default=2)
    los_onu_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    last_evaluated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "CTO"
        verbose_name_plural = "CTOs"


class FiberCable(NamedModel):
    class CableType(models.TextChoices):
        FEEDER = "feeder", "Alimentador"
        DISTRIBUTION = "distribution", "Distribuição"
        DROP = "drop", "Drop"
        BACKBONE = "backbone", "Backbone"

    code = models.CharField(max_length=100, blank=True, db_index=True)
    cable_type = models.CharField(max_length=30, choices=CableType.choices)
    geometry = models.MultiLineStringField(srid=4326)
    fiber_count = models.PositiveSmallIntegerField(default=12)
    used_fibers = models.PositiveSmallIntegerField(default=0)
    origin = models.ForeignKey(
        NetworkElement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outgoing_cables",
    )
    destination = models.ForeignKey(
        NetworkElement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_cables",
    )
    route = models.ForeignKey(
        NetworkRoute,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cables",
    )
    status = models.CharField(max_length=20, choices=OperationalStatus.choices, default=OperationalStatus.NO_DATA)

    class Meta:
        ordering = ["name"]


class NetworkDependency(TimeStampedModel):
    upstream = models.ForeignKey(
        NetworkElement,
        on_delete=models.CASCADE,
        related_name="downstream_dependencies",
    )
    downstream = models.ForeignKey(
        NetworkElement,
        on_delete=models.CASCADE,
        related_name="upstream_dependencies",
    )
    fiber_identifier = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["upstream", "downstream"],
                name="unique_network_dependency",
            )
        ]

    def __str__(self):
        return f"{self.upstream} → {self.downstream}"
