import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Permite que a entrada de um splitter da CEO/CTO venha da saída de
    outro splitter (cascata), em vez de exigir sempre uma fibra do cabo."""

    dependencies = [("network_map", "0026_dio_front_back_ports")]

    operations = [
        migrations.AddField(
            model_name="splicetraysplitter",
            name="input_splitter_port",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Entrada alimentada por uma saída de outro splitter "
                    "(cascata), em vez de uma fibra do cabo. Alternativo a "
                    "input_fiber."
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cascaded_splitters",
                to="network_map.splicetraysplitterport",
            ),
        ),
    ]
