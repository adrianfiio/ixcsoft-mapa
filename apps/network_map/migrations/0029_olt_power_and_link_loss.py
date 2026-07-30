from django.db import migrations, models


class Migration(migrations.Migration):
    """Potência óptica de saída da OLT (manual, sem SNMP) e perda estimada
    por ligação de porta (cordão/fusão), para o orçamento óptico."""

    dependencies = [("network_map", "0028_unbalanced_splitter_ratios")]

    operations = [
        migrations.AddField(
            model_name="containerequipment",
            name="tx_power_dbm",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text=(
                    "Potência óptica de saída da OLT (dBm), informada "
                    "manualmente quando não há coleta SNMP."
                ),
                max_digits=5,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="containerportlink",
            name="loss_db",
            field=models.DecimalField(
                decimal_places=2,
                default=0.3,
                help_text=(
                    "Perda óptica estimada (dB): conector do cordão (frente) "
                    "ou fusão da fibra no fundo da porta."
                ),
                max_digits=4,
            ),
        ),
    ]
