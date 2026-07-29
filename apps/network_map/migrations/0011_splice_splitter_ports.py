from django.db import migrations, models
import django.db.models.deletion


def create_ports(apps, schema_editor):
    Splitter = apps.get_model("network_map", "SpliceTraySplitter")
    Port = apps.get_model("network_map", "SpliceTraySplitterPort")
    for splitter in Splitter.objects.all().iterator():
        Port.objects.bulk_create([
            Port(splitter=splitter, number=number)
            for number in range(1, splitter.output_ports + 1)
        ])


class Migration(migrations.Migration):
    dependencies = [("network_map", "0010_splicetraysplitter_fix_abnt_existing")]
    operations = [
        migrations.AddField(
            model_name="splicetraysplitter",
            name="input_fiber",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="splice_box_splitter_inputs", to="network_map.fiberstrand"),
        ),
        migrations.CreateModel(
            name="SpliceTraySplitterPort",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("number", models.PositiveSmallIntegerField()),
                ("output_fiber", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="splice_box_splitter_outputs", to="network_map.fiberstrand")),
                ("splitter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ports", to="network_map.splicetraysplitter")),
            ],
            options={"ordering": ["splitter", "number"]},
        ),
        migrations.AddConstraint(
            model_name="splicetraysplitterport",
            constraint=models.UniqueConstraint(fields=("splitter", "number"), name="unique_port_per_splice_tray_splitter"),
        ),
        migrations.RunPython(create_ports, migrations.RunPython.noop),
    ]
