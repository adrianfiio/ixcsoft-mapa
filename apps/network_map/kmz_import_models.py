from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class KMZImportBatch(TimeStampedModel):
    class Status(models.TextChoices):
        PREVIEW = "preview", "Prévia gerada"
        IMPORTED = "imported", "Importado"
        UNDONE = "undone", "Desfeito"
        FAILED = "failed", "Falhou"

    project = models.ForeignKey(
        "network_map.NetworkProject",
        on_delete=models.CASCADE,
        related_name="kmz_import_batches",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kmz_import_batches",
    )
    filename = models.CharField(max_length=255)
    file_sha256 = models.CharField(max_length=64, db_index=True)
    preview_token = models.CharField(max_length=64, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PREVIEW)
    decisions = models.JSONField(default=dict, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    warning_messages = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lote de importação KMZ"
        verbose_name_plural = "Lotes de importação KMZ"
        indexes = [
            models.Index(
                fields=["project", "status", "-created_at"],
                name="kmz_batch_proj_status_idx",
            )
        ]

    def __str__(self):
        return f"#{self.pk} · {self.filename}"


class KMZImportObject(TimeStampedModel):
    batch = models.ForeignKey(
        KMZImportBatch,
        on_delete=models.CASCADE,
        related_name="objects",
    )
    object_type = models.CharField(max_length=40, db_index=True)
    object_id = models.PositiveBigIntegerField(db_index=True)
    source_id = models.CharField(max_length=180, blank=True, db_index=True)
    source_name = models.CharField(max_length=255, blank=True)
    source_folder = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["object_type", "object_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "object_type", "object_id"],
                name="unique_kmz_batch_object",
            )
        ]

    def __str__(self):
        return f"{self.batch_id}: {self.object_type}#{self.object_id}"


class CableElementPassage(TimeStampedModel):
    """Relação física quando um cabo passa por uma caixa sem ser dividido.

    Para cortes/derivações, os trechos de FiberCable usam origin/destination.
    Este modelo registra passagem, conexão de ponta e decisão topológica para
    auditoria e para exibição no detalhe da CTO/CEO.
    """

    class Action(models.TextChoices):
        PASS = "pass", "Passagem sem corte"
        CONNECT = "connect", "Conectado na ponta"
        CUT = "cut", "Corte"
        BRANCH = "branch", "Derivação"

    cable = models.ForeignKey(
        "network_map.FiberCable",
        on_delete=models.CASCADE,
        related_name="element_passages",
    )
    element = models.ForeignKey(
        "network_map.NetworkElement",
        on_delete=models.CASCADE,
        related_name="cable_passages",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    sequence = models.PositiveIntegerField(default=1)
    position_m = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    distance_m = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["cable", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["cable", "element", "action"],
                name="unique_cable_element_passage_action",
            )
        ]
        verbose_name = "Passagem de cabo por elemento"
        verbose_name_plural = "Passagens de cabos por elementos"

    def __str__(self):
        return f"{self.cable} · {self.element} · {self.get_action_display()}"
