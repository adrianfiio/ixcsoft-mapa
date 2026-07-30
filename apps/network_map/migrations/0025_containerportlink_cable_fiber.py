import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Permite registrar qual fibra específica do cabo foi fundida numa porta
    do DIO, para a fusão visual do rack no nível de fibra (como já existe na
    CTO/CEO)."""

    dependencies = [("network_map", "0024_containerportlink_source_port_optional")]

    operations = [
        migrations.AddField(
            model_name="containerportlink",
            name="cable_fiber",
            field=models.ForeignKey(
                blank=True,
                help_text="Fibra específica do cabo fundida nesta porta, quando aplicável.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="container_port_links",
                to="network_map.fiberstrand",
            ),
        ),
    ]
