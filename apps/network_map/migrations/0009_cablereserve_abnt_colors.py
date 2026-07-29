from django.contrib.gis.db import models as gis_models
from django.db import migrations, models
import django.db.models.deletion


ABNT = [
    ("green", "Verde", "#00B050", "#000000"),
    ("yellow", "Amarelo", "#FFFF00", "#000000"),
    ("white", "Branco", "#FFFFFF", "#000000"),
    ("blue", "Azul", "#00A6D6", "#000000"),
    ("red", "Vermelho", "#FF0000", "#000000"),
    ("violet", "Violeta", "#7030A0", "#FFFFFF"),
    ("brown", "Marrom", "#996633", "#000000"),
    ("pink", "Rosa", "#FF3399", "#000000"),
    ("black", "Preto", "#000000", "#FFFFFF"),
    ("gray", "Cinza", "#808080", "#000000"),
    ("orange", "Laranja", "#FF9900", "#000000"),
    ("aqua", "Água", "#00E5E5", "#000000"),
]


def apply_abnt(apps, schema_editor):
    FiberColor = apps.get_model("network_map", "FiberColor")
    FiberColorStandard = apps.get_model("network_map", "FiberColorStandard")
    FiberColorStandardItem = apps.get_model("network_map", "FiberColorStandardItem")
    for position, (code, name, color, text) in enumerate(ABNT, 1):
        item, _ = FiberColor.objects.update_or_create(
            code=code,
            defaults={"name": name, "hex_color": color, "text_color": text, "order": position},
        )
        for standard in FiberColorStandard.objects.all():
            FiberColorStandardItem.objects.update_or_create(
                standard=standard,
                position=position,
                defaults={"color": item},
            )
            if standard.code == "OPTICO-12":
                standard.name = "Padrão ABNT de 12 cores"
                standard.save(update_fields=["name"])


class Migration(migrations.Migration):
    dependencies = [("network_map", "0008_ctosplitter_input_fiber")]
    operations = [
        migrations.CreateModel(
            name="CableReserve",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("point", gis_models.PointField(srid=4326)),
                ("length_m", models.DecimalField(decimal_places=2, max_digits=8)),
                ("label", models.CharField(blank=True, max_length=100)),
                ("notes", models.TextField(blank=True)),
                ("cable", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reserves", to="network_map.fibercable")),
            ],
            options={"verbose_name": "Reserva técnica", "verbose_name_plural": "Reservas técnicas", "ordering": ["cable", "id"]},
        ),
        migrations.RunPython(apply_abnt, migrations.RunPython.noop),
    ]
