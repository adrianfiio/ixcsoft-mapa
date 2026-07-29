from django.db import migrations, models
import django.db.models.deletion


def create_default_splitters(apps, schema_editor):
    CTO = apps.get_model("network_map", "CTO")
    CTOSplitter = apps.get_model("network_map", "CTOSplitter")
    CTOSplitterPort = apps.get_model("network_map", "CTOSplitterPort")
    for cto in CTO.objects.all().iterator():
        port_count = max(1, min(cto.capacity or 8, 128))
        ratio = cto.splitter_ratio if cto.splitter_ratio in {
            "1:2", "1:4", "1:8", "1:16", "1:32", "1:64"
        } else "1:8"
        splitter = CTOSplitter.objects.create(
            cto=cto,
            name="Splitter 1",
            ratio=ratio,
            output_ports=port_count,
        )
        CTOSplitterPort.objects.bulk_create([
            CTOSplitterPort(splitter=splitter, number=number)
            for number in range(1, port_count + 1)
        ])


class Migration(migrations.Migration):

    dependencies = [
        ("access", "0002_add_ftth_fields"),
        ("network_map", "0006_networkproject_project_links"),
    ]

    operations = [
        migrations.CreateModel(
            name="CTOSplitter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(default="Splitter 1", max_length=100)),
                (
                    "ratio",
                    models.CharField(
                        choices=[
                            ("1:2", "1:2"),
                            ("1:4", "1:4"),
                            ("1:8", "1:8"),
                            ("1:16", "1:16"),
                            ("1:32", "1:32"),
                            ("1:64", "1:64"),
                        ],
                        default="1:8",
                        max_length=10,
                    ),
                ),
                ("output_ports", models.PositiveSmallIntegerField(default=8)),
                ("input_label", models.CharField(blank=True, max_length=80)),
                ("position", models.PositiveSmallIntegerField(default=1)),
                ("enabled", models.BooleanField(default=True)),
                (
                    "cto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="splitters",
                        to="network_map.cto",
                    ),
                ),
            ],
            options={
                "verbose_name": "Splitter de CTO",
                "verbose_name_plural": "Splitters de CTO",
                "ordering": ["cto", "position"],
            },
        ),
        migrations.CreateModel(
            name="CTOSplitterPort",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("number", models.PositiveSmallIntegerField()),
                ("label", models.CharField(blank=True, max_length=80)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("free", "Livre"),
                            ("reserved", "Reservada"),
                            ("occupied", "Ocupada"),
                            ("defective", "Defeituosa"),
                        ],
                        db_index=True,
                        default="free",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                (
                    "access_point",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="cto_splitter_ports",
                        to="access.accesspoint",
                    ),
                ),
                (
                    "splitter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ports",
                        to="network_map.ctosplitter",
                    ),
                ),
            ],
            options={
                "verbose_name": "Porta de splitter",
                "verbose_name_plural": "Portas de splitter",
                "ordering": ["splitter", "number"],
            },
        ),
        migrations.AddConstraint(
            model_name="ctosplitter",
            constraint=models.UniqueConstraint(
                fields=("cto", "position"),
                name="unique_splitter_position_per_cto",
            ),
        ),
        migrations.AddConstraint(
            model_name="ctosplitterport",
            constraint=models.UniqueConstraint(
                fields=("splitter", "number"),
                name="unique_port_number_per_splitter",
            ),
        ),
        migrations.RunPython(
            create_default_splitters,
            migrations.RunPython.noop,
        ),
    ]
