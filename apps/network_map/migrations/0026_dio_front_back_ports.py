import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Uma porta de DIO tem frente (cordão para a OLT) e fundo (fusão da
    fibra do cabo). destination_port deixa de ser único por porta para
    permitir as duas ligações ao mesmo tempo na mesma porta; constraints
    parciais garantem no máximo um cordão e uma fusão por porta.

    Também adiciona o tipo de conector do DIO (SC/APC, SC/UPC, LC/LC UPC,
    LC/LC APC), definido no cadastro do equipamento."""

    dependencies = [("network_map", "0025_containerportlink_cable_fiber")]

    operations = [
        migrations.AddField(
            model_name="containerequipment",
            name="connector_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("sc_apc", "SC/APC"),
                    ("sc_upc", "SC/UPC"),
                    ("lc_upc", "LC/LC UPC"),
                    ("lc_apc", "LC/LC APC"),
                ],
                help_text=(
                    "Tipo de conector das portas do DIO (SC/APC, SC/UPC, "
                    "LC/LC UPC, LC/LC APC)."
                ),
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="containerportlink",
            name="destination_port",
            field=models.ForeignKey(
                help_text=(
                    "Uma porta de DIO pode ter até duas ligações: o cordão "
                    "para a OLT (frente) e a fusão da fibra do cabo (atrás)."
                ),
                on_delete=django.db.models.deletion.CASCADE,
                related_name="incoming_links",
                to="network_map.containerequipmentport",
            ),
        ),
        migrations.AddConstraint(
            model_name="containerportlink",
            constraint=models.UniqueConstraint(
                condition=models.Q(("source_port__isnull", False)),
                fields=("destination_port",),
                name="unique_cord_link_per_destination_port",
            ),
        ),
        migrations.AddConstraint(
            model_name="containerportlink",
            constraint=models.UniqueConstraint(
                condition=models.Q(("cable_fiber__isnull", False)),
                fields=("destination_port",),
                name="unique_fusion_link_per_destination_port",
            ),
        ),
    ]
