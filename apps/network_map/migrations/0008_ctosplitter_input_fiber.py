from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("network_map", "0007_ctosplitter_ctosplitterport"),
    ]

    operations = [
        migrations.AddField(
            model_name="ctosplitter",
            name="input_cable",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="fed_splitters",
                to="network_map.fibercable",
            ),
        ),
        migrations.AddField(
            model_name="ctosplitter",
            name="input_fiber",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="fed_splitters",
                to="network_map.fiberstrand",
            ),
        ),
    ]
