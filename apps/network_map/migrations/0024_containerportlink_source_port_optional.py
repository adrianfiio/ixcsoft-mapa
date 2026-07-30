import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Permite uma fusão direta de cabo numa porta do DIO, sem exigir uma
    porta de OLT do outro lado (source_port passa a ser opcional)."""

    dependencies = [("network_map", "0023_project_route_code_unique_per_company")]

    operations = [
        migrations.AlterField(
            model_name="containerportlink",
            name="source_port",
            field=models.OneToOneField(
                blank=True,
                help_text=(
                    "Em branco para uma fusão direta de cabo numa porta do DIO, "
                    "sem OLT do outro lado."
                ),
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="outgoing_link",
                to="network_map.containerequipmentport",
            ),
        ),
    ]
