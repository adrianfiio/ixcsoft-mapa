from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import SNMPMonitoringProfile


@receiver(post_save, sender=SNMPMonitoringProfile)
def _apply_snmp_profile(sender, instance, **kwargs):
    from .tasks import apply_snmp_monitoring_profile

    apply_snmp_monitoring_profile.delay(instance.pk)


@receiver(post_delete, sender=SNMPMonitoringProfile)
def _remove_snmp_profile(sender, instance, **kwargs):
    from .tasks import remove_snmp_monitoring_profile

    remove_snmp_monitoring_profile.delay(instance.influx_id)
