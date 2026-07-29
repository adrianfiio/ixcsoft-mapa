from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("network_map", "0005_fibersplice_position"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NetworkProject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(db_index=True, max_length=180)),
                ("description", models.TextField(blank=True)),
                ("code", models.CharField(db_index=True, max_length=100, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("planning", "Planejamento"),
                            ("active", "Ativo"),
                            ("paused", "Pausado"),
                            ("archived", "Arquivado"),
                        ],
                        db_index=True,
                        default="planning",
                        max_length=20,
                    ),
                ),
                ("color", models.CharField(default="#2dd4bf", max_length=7)),
                ("enabled", models.BooleanField(default=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="core.company",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="network_projects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Projeto de rede",
                "verbose_name_plural": "Projetos de rede",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="networkroute",
            name="project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="routes",
                to="network_map.networkproject",
            ),
        ),
        migrations.AddField(
            model_name="networkelement",
            name="project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="elements",
                to="network_map.networkproject",
            ),
        ),
        migrations.AddField(
            model_name="fibercable",
            name="project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cables",
                to="network_map.networkproject",
            ),
        ),
        migrations.AddIndex(
            model_name="networkproject",
            index=models.Index(fields=["status", "enabled"], name="network_map_status_47dd57_idx"),
        ),
    ]
