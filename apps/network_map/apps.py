from django.apps import AppConfig


class NetworkMapConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.network_map"
    verbose_name = "Mapa de Rede"

    def ready(self):
        import apps.network_map.signals  # noqa: F401
