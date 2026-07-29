from django.core.exceptions import ValidationError
from django.db import models

from apps.core.enums import OperationalStatus
from apps.core.models import TimeStampedModel
from apps.network_map.models import NetworkElement, POP, Rack, RackEquipment


class DIO(NetworkElement):
    """
    Distribuidor Interno Óptico.

    Por herdar de NetworkElement, o DIO poderá aparecer no mapa,
    participar da topologia e ser origem ou destino de cabos.
    """

    class ConnectorType(models.TextChoices):
        SC_APC = "sc_apc", "SC/APC"
        SC_UPC = "sc_upc", "SC/UPC"
        LC_APC = "lc_apc", "LC/APC"
        LC_UPC = "lc_upc", "LC/UPC"
        E2000_APC = "e2000_apc", "E2000/APC"
        OTHER = "other", "Outro"

    pop = models.ForeignKey(
        POP,
        on_delete=models.PROTECT,
        related_name="dios",
        verbose_name="POP",
    )
    rack = models.ForeignKey(
        Rack,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dios",
        verbose_name="Rack",
    )
    rack_equipment = models.OneToOneField(
        RackEquipment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dio",
        verbose_name="Equipamento no rack",
    )
    manufacturer = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Fabricante",
    )
    model = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Modelo",
    )
    serial_number = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Número de série",
    )
    connector_type = models.CharField(
        max_length=20,
        choices=ConnectorType.choices,
        default=ConnectorType.SC_APC,
        verbose_name="Tipo de conector",
    )
    tray_capacity = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Quantidade de bandejas",
    )
    port_capacity = models.PositiveSmallIntegerField(
        default=24,
        verbose_name="Quantidade de portas",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Observações",
    )

    class Meta:
        verbose_name = "DIO"
        verbose_name_plural = "DIOs"
        ordering = ["pop", "rack", "name"]

    def clean(self):
        super().clean()

        if self.rack_id and self.pop_id and self.rack.pop_id != self.pop_id:
            raise ValidationError(
                {"rack": "O rack selecionado não pertence ao POP informado."}
            )

        if self.rack_equipment_id:
            if not self.rack_id:
                raise ValidationError(
                    {
                        "rack_equipment": (
                            "Informe o rack antes de selecionar o equipamento."
                        )
                    }
                )

            if self.rack_equipment.rack_id != self.rack_id:
                raise ValidationError(
                    {
                        "rack_equipment": (
                            "O equipamento selecionado não pertence ao rack informado."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.element_type = NetworkElement.ElementType.DIO
        super().save(*args, **kwargs)
        tray, _ = DIOTray.objects.get_or_create(
            dio=self,
            number=1,
            defaults={"name": "Bandeja 1", "splice_capacity": self.port_capacity},
        )
        for number in range(1, self.port_capacity + 1):
            DIOPort.objects.get_or_create(
                dio=self,
                number=number,
                defaults={"tray": tray},
            )

    def __str__(self):
        return f"{self.pop.code} / {self.code} - {self.name}"


class DIOTray(TimeStampedModel):
    """
    Bandeja física instalada dentro de um DIO.
    """

    dio = models.ForeignKey(
        DIO,
        on_delete=models.CASCADE,
        related_name="trays",
        verbose_name="DIO",
    )
    number = models.PositiveSmallIntegerField(
        verbose_name="Número",
    )
    name = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Identificação",
    )
    splice_capacity = models.PositiveSmallIntegerField(
        default=24,
        verbose_name="Capacidade de fusões",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Observações",
    )

    class Meta:
        verbose_name = "Bandeja de DIO"
        verbose_name_plural = "Bandejas de DIO"
        ordering = ["dio", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["dio", "number"],
                name="unique_tray_number_per_dio",
            )
        ]

    def __str__(self):
        identification = self.name or f"Bandeja {self.number}"
        return f"{self.dio} / {identification}"


class DIOPort(TimeStampedModel):
    """
    Porta ou adaptador frontal de um DIO.
    """

    dio = models.ForeignKey(
        DIO,
        on_delete=models.CASCADE,
        related_name="ports",
        verbose_name="DIO",
    )
    tray = models.ForeignKey(
        DIOTray,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ports",
        verbose_name="Bandeja",
    )
    number = models.PositiveSmallIntegerField(
        verbose_name="Número",
    )
    label = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Identificação",
    )
    connector_type = models.CharField(
        max_length=20,
        choices=DIO.ConnectorType.choices,
        default=DIO.ConnectorType.SC_APC,
        verbose_name="Tipo de conector",
    )
    status = models.CharField(
        max_length=20,
        choices=OperationalStatus.choices,
        default=OperationalStatus.NO_DATA,
        verbose_name="Estado operacional",
    )
    enabled = models.BooleanField(
        default=True,
        verbose_name="Ativa",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Observações",
    )

    class Meta:
        verbose_name = "Porta de DIO"
        verbose_name_plural = "Portas de DIO"
        ordering = ["dio", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["dio", "number"],
                name="unique_port_number_per_dio",
            )
        ]
        indexes = [
            models.Index(fields=["dio", "status"]),
            models.Index(fields=["dio", "enabled"]),
        ]

    def clean(self):
        super().clean()

        if self.tray_id and self.dio_id and self.tray.dio_id != self.dio_id:
            raise ValidationError(
                {"tray": "A bandeja selecionada não pertence ao DIO informado."}
            )

    def __str__(self):
        label = f" - {self.label}" if self.label else ""
        return f"{self.dio} / Porta {self.number}{label}"
