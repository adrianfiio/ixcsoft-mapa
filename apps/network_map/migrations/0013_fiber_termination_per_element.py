from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("network_map", "0012_cleanup_duplicate_fiber_links"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fibersplice",
            name="input_fiber",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="splice_outputs",
                to="network_map.fiberstrand",
                verbose_name="Fibra de entrada",
            ),
        ),
        migrations.AlterField(
            model_name="fibersplice",
            name="output_fiber",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="splice_inputs",
                to="network_map.fiberstrand",
                verbose_name="Fibra de saída",
            ),
        ),
        migrations.AddConstraint(
            model_name="fibersplice",
            constraint=models.UniqueConstraint(
                fields=("splice_box", "input_fiber"),
                name="unique_input_fiber_per_splice_box",
            ),
        ),
        migrations.AddConstraint(
            model_name="fibersplice",
            constraint=models.UniqueConstraint(
                fields=("splice_box", "output_fiber"),
                name="unique_output_fiber_per_splice_box",
            ),
        ),
    ]
