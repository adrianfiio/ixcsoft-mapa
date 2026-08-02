from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import CompanyScopedModel

from .models import NetworkElement, NetworkProject


class MapIconStyle(CompanyScopedModel):
    """Visual configuration for one map asset type.

    The JavaScript renderer consumes these records through the master bootstrap API.
    SVG is stored as text so administrators can replace icons without rebuilding
    static files. Only a conservative SVG subset is rendered by the browser code.
    """

    element_type = models.CharField(max_length=40, db_index=True)
    subtype = models.CharField(max_length=40, blank=True, db_index=True)
    display_name = models.CharField(max_length=80)
    svg_markup = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    foreground_color = models.CharField(max_length=16, default="#e6edf7")
    background_color = models.CharField(max_length=16, default="#0f1f33")
    border_color = models.CharField(max_length=16, default="#53c7ff")
    size_px = models.PositiveSmallIntegerField(
        default=30,
        validators=[MinValueValidator(16), MaxValueValidator(96)],
    )
    show_label = models.BooleanField(default=True)
    show_name_inside_icon = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ("element_type", "subtype", "display_name")
        constraints = [
            models.UniqueConstraint(
                fields=("company", "element_type", "subtype"),
                name="unique_map_icon_style_per_company_type",
            )
        ]
        verbose_name = "Estilo de ícone do mapa"
        verbose_name_plural = "Estilos de ícones do mapa"

    def __str__(self) -> str:
        suffix = f"/{self.subtype}" if self.subtype else ""
        return f"{self.display_name} ({self.element_type}{suffix})"


class MapDiagramRevision(CompanyScopedModel):
    class DiagramType(models.TextChoices):
        FUSION = "fusion", "Fusões"
        CONTAINER = "container", "POP/Rack/Torre"
        ROUTE = "route", "Rota óptica"

    project = models.ForeignKey(
        NetworkProject,
        on_delete=models.CASCADE,
        related_name="map_diagram_revisions",
    )
    element = models.ForeignKey(
        NetworkElement,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="map_diagram_revisions",
    )
    diagram_type = models.CharField(max_length=20, choices=DiagramType.choices)
    payload = models.JSONField(default=dict, blank=True)
    note = models.CharField(max_length=240, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="map_diagram_revisions",
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("project", "diagram_type", "created_at")),
            models.Index(fields=("element", "diagram_type", "created_at")),
        ]
        verbose_name = "Revisão de diagrama"
        verbose_name_plural = "Revisões de diagramas"

    def __str__(self) -> str:
        target = self.element or self.project
        timestamp = self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else "nova"
        return f"{target} · {self.get_diagram_type_display()} · {timestamp}"


class NetworkAssetLifecycle(CompanyScopedModel):
    class AssetType(models.TextChoices):
        ELEMENT = "element", "Elemento"
        CABLE = "cable", "Cabo"
        EQUIPMENT = "equipment", "Equipamento"
        LINK = "link", "Ligação"
        SPLITTER_PORT = "splitter_port", "Porta de splitter"

    class Stage(models.TextChoices):
        PLANNING = "planning", "Em projeto"
        NOT_DEPLOYED = "not_deployed", "Não implantado"
        DEPLOYED = "deployed", "Implantado"
        CERTIFIED = "certified", "Certificado"
        DISABLED = "disabled", "Desativado"

    project = models.ForeignKey(
        NetworkProject,
        on_delete=models.CASCADE,
        related_name="asset_lifecycle_events",
    )
    asset_type = models.CharField(max_length=24, choices=AssetType.choices)
    asset_id = models.PositiveBigIntegerField()
    stage = models.CharField(max_length=24, choices=Stage.choices, default=Stage.PLANNING)
    note = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="map_asset_lifecycle_events",
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("project", "asset_type", "asset_id", "created_at")),
            models.Index(fields=("stage", "created_at")),
        ]
        verbose_name = "Histórico de implantação"
        verbose_name_plural = "Histórico de implantação"

    def __str__(self) -> str:
        return f"{self.get_asset_type_display()} #{self.asset_id} · {self.get_stage_display()}"
