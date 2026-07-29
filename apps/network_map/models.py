from django.contrib.gis.db import models

from apps.core.enums import OperationalStatus
from apps.core.models import CompanyScopedModel, NamedModel, TimeStampedModel


class NetworkRoute(CompanyScopedModel, NamedModel):
    code = models.CharField(max_length=80, unique=True)
    geometry = models.MultiLineStringField(srid=4326, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=OperationalStatus.choices,
        default=OperationalStatus.NO_DATA,
    )
    offline_cto_threshold = models.PositiveSmallIntegerField(default=2)
    offline_cto_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50,
    )
    enabled = models.BooleanField(default=True)


    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["status", "enabled"])]


class NetworkElement(CompanyScopedModel, NamedModel):
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
    status = models.CharField(
        max_length=20,
        choices=OperationalStatus.choices,
        default=OperationalStatus.NO_DATA,
    )
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


class FiberCable(CompanyScopedModel, NamedModel):
    class CableType(models.TextChoices):
        FEEDER = "feeder", "Alimentador"
        DISTRIBUTION = "distribution", "Distribuição"
        DROP = "drop", "Drop"
        BACKBONE = "backbone", "Backbone"

    code = models.CharField(max_length=100, blank=True, db_index=True)
    cable_type = models.CharField(max_length=30, choices=CableType.choices)
    cable_model = models.ForeignKey(
        "CableModel",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="installed_cables",
        verbose_name="Modelo do cabo",
    )
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
    status = models.CharField(
        max_length=20,
        choices=OperationalStatus.choices,
        default=OperationalStatus.NO_DATA,
    )


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


class POP(CompanyScopedModel, NamedModel):
    code = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Código",
    )
    point = models.PointField(
        srid=4326,
        null=True,
        blank=True,
        verbose_name="Localização",
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Endereço",
    )
    city = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Cidade",
    )
    enabled = models.BooleanField(
        default=True,
        verbose_name="Ativo",
    )

    class Meta:
        verbose_name = "POP"
        verbose_name_plural = "POPs"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="unique_pop_code_per_company",
            )
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Rack(CompanyScopedModel, NamedModel):
    pop = models.ForeignKey(
        POP,
        on_delete=models.CASCADE,
        related_name="racks",
        verbose_name="POP",
    )
    code = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Código",
    )
    height_units = models.PositiveSmallIntegerField(
        default=44,
        verbose_name="Altura em U",
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
    enabled = models.BooleanField(
        default=True,
        verbose_name="Ativo",
    )

    class Meta:
        verbose_name = "Rack"
        verbose_name_plural = "Racks"
        ordering = ["pop", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["pop", "code"],
                name="unique_rack_code_per_pop",
            )
        ]

    def __str__(self):
        return f"{self.pop.code} / {self.code}"


class RackEquipment(TimeStampedModel):
    class Face(models.TextChoices):
        FRONT = "front", "Frontal"
        REAR = "rear", "Traseira"
        BOTH = "both", "Frontal e traseira"

    rack = models.ForeignKey(
        Rack,
        on_delete=models.CASCADE,
        related_name="equipments",
        verbose_name="Rack",
    )
    name = models.CharField(
        max_length=180,
        verbose_name="Equipamento",
    )
    equipment_type = models.CharField(
        max_length=80,
        verbose_name="Tipo",
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
    start_unit = models.PositiveSmallIntegerField(
        verbose_name="U inicial",
    )
    unit_height = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Altura em U",
    )
    face = models.CharField(
        max_length=10,
        choices=Face.choices,
        default=Face.FRONT,
        verbose_name="Face",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        verbose_name = "Equipamento de rack"
        verbose_name_plural = "Equipamentos de rack"
        ordering = ["rack", "-start_unit"]
        constraints = [
            models.UniqueConstraint(
                fields=["rack", "start_unit", "face"],
                name="unique_rack_unit_face",
            )
        ]

    def __str__(self):
        return f"{self.rack} U{self.start_unit} - {self.name}"


class FiberColor(models.Model):
    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Código",
    )
    name = models.CharField(
        max_length=80,
        verbose_name="Nome",
    )
    hex_color = models.CharField(
        max_length=7,
        default="#000000",
        verbose_name="Cor hexadecimal",
    )
    text_color = models.CharField(
        max_length=7,
        default="#FFFFFF",
        verbose_name="Cor do texto",
    )
    order = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Ordem",
    )

    class Meta:
        verbose_name = "Cor de fibra"
        verbose_name_plural = "Cores de fibra"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class FiberColorStandard(CompanyScopedModel, NamedModel):
    code = models.CharField(
        max_length=80,
        db_index=True,
        verbose_name="Código",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descrição",
    )

    class Meta:
        verbose_name = "Padrão de cores"
        verbose_name_plural = "Padrões de cores"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="unique_color_standard_per_company",
            )
        ]


class FiberColorStandardItem(models.Model):
    standard = models.ForeignKey(
        FiberColorStandard,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Padrão",
    )
    position = models.PositiveSmallIntegerField(
        verbose_name="Posição",
    )
    color = models.ForeignKey(
        FiberColor,
        on_delete=models.PROTECT,
        related_name="standard_items",
        verbose_name="Cor",
    )

    class Meta:
        verbose_name = "Item do padrão de cores"
        verbose_name_plural = "Itens do padrão de cores"
        ordering = ["standard", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["standard", "position"],
                name="unique_color_position_per_standard",
            )
        ]

    def __str__(self):
        return f"{self.standard} - {self.position}: {self.color}"


class CableModel(CompanyScopedModel, NamedModel):
    class Construction(models.TextChoices):
        LOOSE_TUBE = "loose_tube", "Loose tube"
        TIGHT_BUFFER = "tight_buffer", "Tight buffer"
        RIBBON = "ribbon", "Ribbon"
        DROP = "drop", "Drop"
        OTHER = "other", "Outro"

    manufacturer = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Fabricante",
    )
    model = models.CharField(
        max_length=120,
        verbose_name="Modelo",
    )
    construction = models.CharField(
        max_length=30,
        choices=Construction.choices,
        default=Construction.LOOSE_TUBE,
        verbose_name="Construção",
    )
    fiber_count = models.PositiveSmallIntegerField(
        verbose_name="Quantidade de fibras",
    )
    tube_count = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Quantidade de tubos",
    )
    fibers_per_tube = models.PositiveSmallIntegerField(
        default=12,
        verbose_name="Fibras por tubo",
    )
    outer_diameter_mm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Diâmetro externo em mm",
    )
    color_standard = models.ForeignKey(
        FiberColorStandard,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cable_models",
        verbose_name="Padrão de cores",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        verbose_name = "Modelo de cabo"
        verbose_name_plural = "Modelos de cabo"
        ordering = ["manufacturer", "model"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "manufacturer", "model"],
                name="unique_cable_model_per_company",
            )
        ]

    def __str__(self):
        return f"{self.manufacturer} {self.model}".strip()


class FiberTube(TimeStampedModel):
    cable = models.ForeignKey(
        FiberCable,
        on_delete=models.CASCADE,
        related_name="tubes",
        verbose_name="Cabo",
    )
    number = models.PositiveSmallIntegerField(
        verbose_name="Número",
    )
    color = models.ForeignKey(
        FiberColor,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="fiber_tubes",
        verbose_name="Cor",
    )
    identification = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="Identificação",
    )

    class Meta:
        verbose_name = "Tubo de fibra"
        verbose_name_plural = "Tubos de fibra"
        ordering = ["cable", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["cable", "number"],
                name="unique_tube_number_per_cable",
            )
        ]

    def __str__(self):
        return f"{self.cable} - Tubo {self.number}"


class FiberStrand(TimeStampedModel):
    class Status(models.TextChoices):
        FREE = "free", "Livre"
        USED = "used", "Em uso"
        RESERVED = "reserved", "Reservada"
        DAMAGED = "damaged", "Danificada"
        DARK = "dark", "Apagada"

    cable = models.ForeignKey(
        FiberCable,
        on_delete=models.CASCADE,
        related_name="fibers",
        verbose_name="Cabo",
    )
    tube = models.ForeignKey(
        FiberTube,
        on_delete=models.CASCADE,
        related_name="fibers",
        null=True,
        blank=True,
        verbose_name="Tubo",
    )
    number = models.PositiveSmallIntegerField(
        verbose_name="Número global",
    )
    position_in_tube = models.PositiveSmallIntegerField(
        verbose_name="Posição no tubo",
    )
    color = models.ForeignKey(
        FiberColor,
        on_delete=models.PROTECT,
        related_name="fiber_strands",
        verbose_name="Cor",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.FREE,
        verbose_name="Estado",
    )
    origin_element = models.ForeignKey(
        NetworkElement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="origin_fibers",
        verbose_name="Origem",
    )
    destination_element = models.ForeignKey(
        NetworkElement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="destination_fibers",
        verbose_name="Destino",
    )
    usage = models.CharField(
        max_length=180,
        blank=True,
        verbose_name="Uso",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Observações",
    )

    class Meta:
        verbose_name = "Fibra"
        verbose_name_plural = "Fibras"
        ordering = ["cable", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["cable", "number"],
                name="unique_fiber_number_per_cable",
            ),
            models.UniqueConstraint(
                fields=["tube", "position_in_tube"],
                name="unique_fiber_position_per_tube",
            ),
        ]

    def __str__(self):
        return f"{self.cable} - Fibra {self.number}"


class SpliceTray(TimeStampedModel):
    splice_box = models.ForeignKey(
        NetworkElement,
        on_delete=models.CASCADE,
        related_name="splice_trays",
        verbose_name="Caixa",
    )

    number = models.PositiveSmallIntegerField(
        verbose_name="Bandeja"
    )

    name = models.CharField(
        max_length=100,
        blank=True,
    )

    capacity = models.PositiveSmallIntegerField(
        default=12,
        verbose_name="Capacidade",
    )

    class Meta:
        ordering = ["splice_box", "number"]
        unique_together = ("splice_box", "number")
        verbose_name = "Bandeja de emenda"
        verbose_name_plural = "Bandejas de emenda"

    def __str__(self):
        return f"{self.splice_box} - Bandeja {self.number}"


class FiberSplice(TimeStampedModel):
    tray = models.ForeignKey(
        "SpliceTray",
        on_delete=models.CASCADE,
        related_name="splices",
        verbose_name="Bandeja",
    )

    splice_box = models.ForeignKey(
        NetworkElement,
        on_delete=models.CASCADE,
        related_name="fiber_splices",
        limit_choices_to={"element_type": NetworkElement.ElementType.DIO},
        verbose_name="Caixa de emenda",
    )

    input_fiber = models.OneToOneField(
        "FiberStrand",
        on_delete=models.PROTECT,
        related_name="splice_output",
        verbose_name="Fibra de entrada",
    )

    output_fiber = models.OneToOneField(
        "FiberStrand",
        on_delete=models.PROTECT,
        related_name="splice_input",
        verbose_name="Fibra de saída",
    )

    position = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Posição da fusão",
    )

    loss_db = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.05,
        verbose_name="Perda (dB)",
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["splice_box", "id"]
        verbose_name = "Emenda óptica"
        verbose_name_plural = "Emendas ópticas"

    def save(self, *args, **kwargs):
        if self.input_fiber_id:
            exists = FiberSplice.objects.filter(
                input_fiber=self.input_fiber
            ).exclude(pk=self.pk).exists()

            if exists:
                raise ValueError(
                    "A fibra de entrada já possui uma fusão."
                )

        if self.output_fiber_id:
            exists = FiberSplice.objects.filter(
                output_fiber=self.output_fiber
            ).exclude(pk=self.pk).exists()

            if exists:
                raise ValueError(
                    "A fibra de saída já possui uma fusão."
                )

        if self.position is None or self.position == 1:
            last = FiberSplice.objects.filter(
                tray=self.tray
            ).order_by("-position").first()

            if last:
                self.position = last.position + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.input_fiber} → {self.output_fiber}"



