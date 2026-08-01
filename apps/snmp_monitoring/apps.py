from django.apps import AppConfig


class SnmpMonitoringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.snmp_monitoring"
    verbose_name = "Monitoramento SNMP"

    def ready(self):
        from . import signals  # noqa: F401
