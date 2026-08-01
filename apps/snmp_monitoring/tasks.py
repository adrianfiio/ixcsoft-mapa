import logging

from celery import shared_task
from django.utils import timezone

from apps.core.enums import OperationalStatus
from . import influx_client, services
from .docker_control import reload_telegraf
from .models import SNMPMonitoringProfile

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(OSError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def apply_snmp_monitoring_profile(self, profile_id):
    """Gera/atualiza o `.conf` do Telegraf pro perfil e recarrega o
    coletor. Roda em background (Celery) — nunca no processo web, pra não
    travar a resposta HTTP nem exigir acesso ao Docker do host a partir do
    container exposto à internet."""
    try:
        profile = SNMPMonitoringProfile.objects.select_related("element").get(pk=profile_id)
    except SNMPMonitoringProfile.DoesNotExist:
        return False
    if not profile.enabled:
        services.remove_conf_by_influx_id(profile.influx_id)
    else:
        services.write_conf(profile)
    reload_telegraf()
    return True


@shared_task
def remove_snmp_monitoring_profile(influx_id):
    services.remove_conf_by_influx_id(influx_id)
    reload_telegraf()


@shared_task
def poll_snmp_status():
    """Task periódica (Celery Beat): consulta o InfluxDB pra cada
    equipamento com monitoramento ativo e atualiza o status do elemento no
    mapa — é o que faz o marcador ficar vermelho quando uma porta cai."""
    updated = 0
    for profile in SNMPMonitoringProfile.objects.filter(enabled=True).select_related("element"):
        try:
            ports = influx_client.fetch_port_status(profile.influx_id)
        except Exception as exc:  # noqa: BLE001 — segue pro próximo equipamento
            profile.last_poll_message = f"Erro ao consultar InfluxDB: {exc}"
            profile.save(update_fields=["last_poll_message"])
            logger.warning("Falha ao consultar SNMP de %s: %s", profile.influx_id, exc)
            continue

        profile.last_poll_at = timezone.now()
        if not ports:
            profile.last_poll_message = "Sem dados retornados pelo InfluxDB nos últimos 5 minutos."
            element_status = OperationalStatus.NO_DATA
        elif any(status == "DOWN" for status in ports.values()):
            down_ports = [name for name, status in ports.items() if status == "DOWN"]
            profile.last_poll_message = f"Porta(s) offline: {', '.join(down_ports)}"
            element_status = OperationalStatus.OFFLINE
        else:
            profile.last_poll_message = f"{len(ports)} porta(s) online."
            element_status = OperationalStatus.NORMAL

        profile.save(update_fields=["last_poll_at", "last_poll_message"])
        if profile.element.status != element_status:
            profile.element.status = element_status
            profile.element.save(update_fields=["status", "updated_at"])
        updated += 1
    return updated
