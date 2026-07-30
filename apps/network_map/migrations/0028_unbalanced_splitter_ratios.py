from django.db import migrations, models


class Migration(migrations.Migration):
    """Adiciona ratios de splitter desbalanceado (1x2: 10/90, 15/85, 20/80,
    30/70, 40/60, 45/55) às choices já existentes de splitter balanceado."""

    dependencies = [("network_map", "0027_splitter_cascade_input")]

    RATIO_CHOICES = [
        ("1:2", "1:2 (balanceado)"),
        ("1:4", "1:4 (balanceado)"),
        ("1:8", "1:8 (balanceado)"),
        ("1:16", "1:16 (balanceado)"),
        ("1:32", "1:32 (balanceado)"),
        ("1:64", "1:64 (balanceado)"),
        ("10:90", "10/90 (desbalanceado)"),
        ("15:85", "15/85 (desbalanceado)"),
        ("20:80", "20/80 (desbalanceado)"),
        ("30:70", "30/70 (desbalanceado)"),
        ("40:60", "40/60 (desbalanceado)"),
        ("45:55", "45/55 (desbalanceado)"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ctosplitter",
            name="ratio",
            field=models.CharField(choices=RATIO_CHOICES, default="1:8", max_length=10),
        ),
        migrations.AlterField(
            model_name="splicetraysplitter",
            name="ratio",
            field=models.CharField(choices=RATIO_CHOICES, max_length=10),
        ),
    ]
