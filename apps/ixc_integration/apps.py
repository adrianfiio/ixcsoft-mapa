from django.apps import AppConfig


class IxcIntegrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ixc_integration"
    verbose_name = "Integração IXCSoft"

    def ready(self):
        # Importa módulos adicionais de modelos para registrá-los no app.
        from . import customer_models, fiber_models  # noqa: F401
