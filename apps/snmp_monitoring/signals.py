from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import SNMPMonitoringProfile


_CONFIG_FIELDS = {
    "element", "equipment", "enabled", "management_ip", "port",
    "snmp_version", "community_encrypted", "polling_interval_seconds",
}


@receiver(post_save, sender=SNMPMonitoringProfile)
def _apply_snmp_profile(sender, instance, update_fields=None, **kwargs):
    # Atualizações de telemetria feitas pela task não podem recarregar o
    # Telegraf a cada ciclo. Só mudanças de configuração geram novo .conf.
    if update_fields is not None and _CONFIG_FIELDS.isdisjoint(set(update_fields)):
        return
    from .tasks import apply_snmp_monitoring_profile

    apply_snmp_monitoring_profile.delay(instance.pk)


@receiver(post_delete, sender=SNMPMonitoringProfile)
def _remove_snmp_profile(sender, instance, **kwargs):
    from .tasks import remove_snmp_monitoring_profile

    remove_snmp_monitoring_profile.delay(instance.influx_id)
