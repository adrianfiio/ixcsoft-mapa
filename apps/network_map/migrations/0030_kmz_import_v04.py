from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Lote/auditoria da importação KMZ v0.4 (KMZImportBatch, KMZImportObject)
    e o registro de passagem física de cabo por caixa (CableElementPassage),
    usado pelo corte/passagem/derivação da topologia detectada no KMZ."""

    dependencies = [
        ("network_map", "0029_olt_power_and_link_loss"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="KMZImportBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("filename", models.CharField(max_length=255)),
                ("file_sha256", models.CharField(db_index=True, max_length=64)),
                ("preview_token", models.CharField(blank=True, db_index=True, max_length=64)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("preview", "Prévia gerada"),
                            ("imported", "Importado"),
                            ("undone", "Desfeito"),
                            ("failed", "Falhou"),
                        ],
                        default="preview",
                        max_length=20,
                    ),
                ),
                ("decisions", models.JSONField(blank=True, default=dict)),
                ("summary", models.JSONField(blank=True, default=dict)),
                ("warning_messages", models.JSONField(blank=True, default=list)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kmz_import_batches",
                        to="network_map.networkproject",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kmz_import_batches",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Lote de importação KMZ",
                "verbose_name_plural": "Lotes de importação KMZ",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="KMZImportObject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("object_type", models.CharField(db_index=True, max_length=40)),
                ("object_id", models.PositiveBigIntegerField(db_index=True)),
                ("source_id", models.CharField(blank=True, db_index=True, max_length=180)),
                ("source_name", models.CharField(blank=True, max_length=255)),
                ("source_folder", models.CharField(blank=True, max_length=500)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="objects",
                        to="network_map.kmzimportbatch",
                    ),
                ),
            ],
            options={
                "ordering": ["object_type", "object_id"],
            },
        ),
        migrations.CreateModel(
            name="CableElementPassage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("pass", "Passagem sem corte"),
                            ("connect", "Conectado na ponta"),
                            ("cut", "Corte"),
                            ("branch", "Derivação"),
                        ],
                        max_length=20,
                    ),
                ),
                ("sequence", models.PositiveIntegerField(default=1)),
                ("position_m", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("distance_m", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "cable",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="element_passages",
                        to="network_map.fibercable",
                    ),
                ),
                (
                    "element",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cable_passages",
                        to="network_map.networkelement",
                    ),
                ),
            ],
            options={
                "verbose_name": "Passagem de cabo por elemento",
                "verbose_name_plural": "Passagens de cabos por elementos",
                "ordering": ["cable", "sequence"],
            },
        ),
        migrations.AddConstraint(
            model_name="kmzimportobject",
            constraint=models.UniqueConstraint(
                fields=("batch", "object_type", "object_id"),
                name="unique_kmz_batch_object",
            ),
        ),
        migrations.AddConstraint(
            model_name="cableelementpassage",
            constraint=models.UniqueConstraint(
                fields=("cable", "element", "action"),
                name="unique_cable_element_passage_action",
            ),
        ),
        migrations.AddIndex(
            model_name="kmzimportbatch",
            index=models.Index(
                fields=["project", "status", "-created_at"],
                name="kmz_batch_proj_status_idx",
            ),
        ),
    ]
