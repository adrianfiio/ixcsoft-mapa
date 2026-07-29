from django.db import migrations, models
import django.db.models.deletion


ABNT_CODES = [
    "green", "yellow", "white", "blue", "red", "violet",
    "brown", "pink", "black", "gray", "orange", "aqua",
]


def remap_existing_fibers(apps, schema_editor):
    FiberColor = apps.get_model("network_map", "FiberColor")
    FiberStrand = apps.get_model("network_map", "FiberStrand")
    FiberTube = apps.get_model("network_map", "FiberTube")
    colors = {item.code: item for item in FiberColor.objects.filter(code__in=ABNT_CODES)}
    if len(colors) != 12:
        return
    for fiber in FiberStrand.objects.all().iterator():
        fiber.color = colors[ABNT_CODES[(fiber.position_in_tube - 1) % 12]]
        fiber.save(update_fields=["color"])
    for tube in FiberTube.objects.all().iterator():
        tube.color = colors[ABNT_CODES[(tube.number - 1) % 12]]
        tube.save(update_fields=["color"])


class Migration(migrations.Migration):
    dependencies = [("network_map", "0009_cablereserve_abnt_colors")]
    operations = [
        migrations.CreateModel(
            name="SpliceTraySplitter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("position", models.PositiveSmallIntegerField(default=1)),
                ("ratio", models.CharField(choices=[("1:2", "1:2"), ("1:4", "1:4"), ("1:8", "1:8"), ("1:16", "1:16"), ("1:32", "1:32"), ("1:64", "1:64")], max_length=10)),
                ("output_ports", models.PositiveSmallIntegerField(default=8)),
                ("tray", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="splitters", to="network_map.splicetray")),
            ],
            options={"ordering": ["tray", "position"]},
        ),
        migrations.AddConstraint(
            model_name="splicetraysplitter",
            constraint=models.UniqueConstraint(fields=("tray", "position"), name="unique_splitter_position_per_splice_tray"),
        ),
        migrations.RunPython(remap_existing_fibers, migrations.RunPython.noop),
    ]
