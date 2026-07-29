from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MapBaseConfiguration",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(default="Mapa principal", max_length=120)),
                (
                    "google_tiles_enabled",
                    models.BooleanField(
                        default=False,
                        verbose_name="Ativar Google Map Tiles",
                    ),
                ),
                ("google_api_key_encrypted", models.TextField(blank=True, editable=False)),
                (
                    "default_layer",
                    models.CharField(
                        choices=[
                            ("google_satellite", "Google Satélite"),
                            ("esri_satellite", "Satélite alternativo"),
                            ("openstreetmap", "Mapa de ruas"),
                        ],
                        default="google_satellite",
                        max_length=30,
                        verbose_name="Camada padrão",
                    ),
                ),
            ],
            options={
                "verbose_name": "Configuração do mapa-base",
                "verbose_name_plural": "Configuração do mapa-base",
            },
        ),
    ]
