from django.utils import timezone

from .models import AlertEvent


# MAP_V085_ALERT_AUTO_CLOSE: toda FK de AlertEvent pro objeto monitorado é
# SET_NULL, não CASCADE (histórico de alerta sobrevive à exclusão do
# equipamento) -- mas isso deixava alertas OPEN/ACKNOWLEDGED/RECOVERING
# órfãos e ativos pra sempre, já que nada vai "voltar a normal" pra fechar
# um alerta cujo equipamento não existe mais. Fechamos explicitamente
# qualquer alerta ainda ativo referenciando o objeto, antes dele sumir.
ACTIVE_STATES = (
    AlertEvent.State.OPEN,
    AlertEvent.State.ACKNOWLEDGED,
    AlertEvent.State.RECOVERING,
)

_ALERT_FK_BY_MODEL = {
    "olt_integration.OLT": "olt",
    "olt_integration.PONPort": "pon_port",
    "olt_integration.ONU": "onu",
    "network_map.CTO": "cto",
    "network_map.NetworkRoute": "route",
    "network_map.NetworkElement": "network_element",
    "network_map.ContainerEquipment": "container_equipment",
    "network_map.ContainerEquipmentPort": "equipment_port",
    "snmp_monitoring.MonitoredNetworkLink": "monitored_link",
}


def close_active_alerts_for_instance(sender, instance, **kwargs):
    field_name = _ALERT_FK_BY_MODEL.get(f"{sender._meta.app_label}.{sender.__name__}")
    if not field_name:
        return
    AlertEvent.objects.filter(
        **{field_name: instance.pk}, state__in=ACTIVE_STATES
    ).update(state=AlertEvent.State.CLOSED, closed_at=timezone.now())


def register():
    from django.db.models.signals import pre_delete

    for label in _ALERT_FK_BY_MODEL:
        app_label, model_name = label.split(".")
        model = None
        try:
            from django.apps import apps as django_apps

            model = django_apps.get_model(app_label, model_name)
        except LookupError:
            continue
        pre_delete.connect(close_active_alerts_for_instance, sender=model, weak=False)
