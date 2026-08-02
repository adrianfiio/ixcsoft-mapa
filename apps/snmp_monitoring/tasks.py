from __future__ import annotations

import logging
from collections import defaultdict

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.enums import OperationalStatus
from . import influx_client, services
from .docker_control import reload_telegraf
from .link_status import (
    binding_operational_status,
    raw_link_status,
    sync_link_alert,
    sync_port_alert,
    transition_ready,
)
from .models import (
    MonitoredNetworkLink,
    SNMPInterfaceState,
    SNMPMonitoringProfile,
    SNMPPortBinding,
    normalize_interface_name,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(OSError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def apply_snmp_monitoring_profile(self, profile_id):
    try:
        profile = SNMPMonitoringProfile.objects.select_related("element", "equipment").get(pk=profile_id)
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


def _sync_interface_states(profile, observations, now):
    states = []
    for row in observations:
        if_name = str(row.get("if_name") or "?").strip() or "?"
        if_index = row.get("if_index")
        key = SNMPInterfaceState.build_key(if_name, if_index)
        state, created = SNMPInterfaceState.objects.get_or_create(
            profile=profile,
            interface_key=key,
            defaults={
                "company": profile.company,
                "if_name": if_name,
                "if_index": if_index,
                "if_alias": row.get("if_alias") or "",
                "status": row.get("status") or SNMPInterfaceState.Status.UNKNOWN,
                "raw_status": row.get("raw_status"),
                "last_seen_at": row.get("observed_at") or now,
                "status_changed_at": row.get("observed_at") or now,
                "metadata": {"hostname": row.get("hostname") or ""},
            },
        )
        new_status = row.get("status") or SNMPInterfaceState.Status.UNKNOWN
        changed = not created and state.status != new_status
        state.if_name = if_name
        state.if_index = if_index
        state.if_alias = row.get("if_alias") or ""
        state.status = new_status
        state.raw_status = row.get("raw_status")
        state.last_seen_at = row.get("observed_at") or now
        if changed:
            state.status_changed_at = state.last_seen_at
        metadata = dict(state.metadata or {})
        metadata["hostname"] = row.get("hostname") or metadata.get("hostname", "")
        state.metadata = metadata
        state.save()
        states.append(state)
    return states


def _binding_state(binding, states, now, stale_seconds):
    by_index = {state.if_index: state for state in states if state.if_index is not None}
    by_name = {normalize_interface_name(state.if_name): state for state in states}
    state = by_index.get(binding.if_index) if binding.if_index is not None else None
    if state is None:
        state = by_name.get(normalize_interface_name(binding.if_name))
    if state is None or not state.last_seen_at:
        return "unknown", None
    if (now - state.last_seen_at).total_seconds() > stale_seconds:
        return "unknown", state
    if state.status == SNMPInterfaceState.Status.UP:
        return "up", state
    if state.status in {
        SNMPInterfaceState.Status.DOWN,
        SNMPInterfaceState.Status.LOWER_LAYER_DOWN,
        SNMPInterfaceState.Status.NOT_PRESENT,
    }:
        return "down", state
    if state.status == SNMPInterfaceState.Status.UNKNOWN:
        return "unknown", state
    return "other", state


def _sync_bindings(profile, states, now, stale_seconds):
    bindings = list(
        profile.port_bindings.select_related("equipment_port").filter(enabled=True)
    )
    for binding in bindings:
        new_status, state = _binding_state(binding, states, now, stale_seconds)
        changed = binding.last_status != new_status
        binding.last_status = new_status
        binding.last_seen_at = state.last_seen_at if state else None
        if changed:
            binding.status_changed_at = now
        if new_status == "down":
            binding.down_since = binding.down_since or now
            binding.up_since = None
        elif new_status == "up":
            binding.up_since = binding.up_since or now
            binding.down_since = None
        else:
            binding.up_since = None
        binding.save(update_fields=[
            "last_status", "last_seen_at", "status_changed_at",
            "down_since", "up_since", "updated_at",
        ])
    return bindings


def _profile_status(profile, states, bindings, now, stale_seconds):
    if profile.aggregate_policy == SNMPMonitoringProfile.AggregatePolicy.NO_AGGREGATE:
        return profile.last_status
    if profile.aggregate_policy == SNMPMonitoringProfile.AggregatePolicy.BOUND_PORTS:
        return binding_operational_status(bindings)
    fresh = [
        state for state in states
        if state.last_seen_at and (now - state.last_seen_at).total_seconds() <= stale_seconds
    ]
    if not fresh:
        return OperationalStatus.NO_DATA
    if any(state.status in {"down", "lower_layer_down", "not_present"} for state in fresh):
        return OperationalStatus.OFFLINE
    if all(state.status == "up" for state in fresh):
        return OperationalStatus.NORMAL
    return OperationalStatus.DEGRADED


def _update_profile_target(profile, status, bindings, states, now, *, observations_received=False):
    profile.last_status = status
    profile.last_poll_at = now
    if observations_received:
        profile.last_success_at = now
    if status == OperationalStatus.OFFLINE:
        down = [binding.display_name for binding in bindings if binding.last_status == "down"]
        profile.last_poll_message = "Porta(s) monitorada(s) offline: " + ", ".join(down or ["interface detectada"])
    elif status == OperationalStatus.NORMAL:
        profile.last_poll_message = f"Monitoramento normal · {len(states)} interface(s) detectada(s)."
    elif status == OperationalStatus.DEGRADED:
        profile.last_poll_message = "Há interfaces sem estado conclusivo."
    else:
        profile.last_poll_message = "Sem dados SNMP recentes."
    profile.save(update_fields=[
        "last_status", "last_poll_at", "last_success_at", "last_poll_message", "updated_at",
    ])

    if profile.element_id and profile.aggregate_policy != SNMPMonitoringProfile.AggregatePolicy.NO_AGGREGATE:
        if profile.element.status != status:
            profile.element.status = status
            profile.element.save(update_fields=["status", "updated_at"])
    elif profile.equipment_id:
        metadata = dict(profile.equipment.metadata or {})
        metadata["snmp_monitoring"] = {
            "status": status,
            "last_poll_at": now.isoformat(),
            "message": profile.last_poll_message,
        }
        profile.equipment.metadata = metadata
        profile.equipment.save(update_fields=["metadata", "updated_at"])


def _link_message(link, statuses):
    labels = []
    if link.source_binding_id:
        labels.append(f"{link.source_binding.display_name}: {link.source_binding.last_status.upper()}")
    if link.destination_binding_id:
        labels.append(f"{link.destination_binding.display_name}: {link.destination_binding.last_status.upper()}")
    return " · ".join(labels) or "Nenhuma porta monitorada vinculada."


def _evaluate_link(link, now):
    bindings = [binding for binding in (link.source_binding, link.destination_binding) if binding and binding.enabled]
    statuses = [binding.last_status for binding in bindings]
    raw = raw_link_status(statuses, require_both=link.require_both_endpoints)
    link.last_evaluated_at = now
    link.last_message = _link_message(link, statuses)

    if raw == link.status:
        link.candidate_status = ""
        link.candidate_since = None
    else:
        if link.candidate_status != raw:
            link.candidate_status = raw
            link.candidate_since = now
        if link.status == OperationalStatus.NO_DATA and raw == OperationalStatus.NORMAL:
            link.status = raw
            link.status_changed_at = now
            link.candidate_status = ""
            link.candidate_since = None
        elif transition_ready(
            current=link.status,
            candidate=raw,
            candidate_since=link.candidate_since,
            now=now,
            outage_seconds=link.outage_persistence_seconds,
            recovery_seconds=link.recovery_seconds,
        ):
            link.status = raw
            link.status_changed_at = now
            link.candidate_status = ""
            link.candidate_since = None

    link.save(update_fields=[
        "status", "candidate_status", "candidate_since", "status_changed_at",
        "last_evaluated_at", "last_message", "updated_at",
    ])
    if link.cable_id and link.cable.status != link.status:
        link.cable.status = link.status
        link.cable.save(update_fields=["status", "updated_at"])
    sync_link_alert(link, now)


@shared_task
def poll_snmp_status(profile_ids=None):
    """Consulta InfluxDB em lotes, atualiza portas, enlaces, cabos e alertas."""
    eligible_types = [
        "switch", "router", "firewall", "access_point", "ptp", "onu", "other",
    ]
    queryset = SNMPMonitoringProfile.objects.filter(
        enabled=True,
        equipment__enabled=True,
        equipment__provisioning_mode="snmp",
        equipment__equipment_type__in=eligible_types,
    ).select_related(
        "company", "element", "equipment__container",
    )
    if profile_ids:
        queryset = queryset.filter(pk__in=list(profile_ids))
    profiles = list(queryset)
    if not profiles:
        logger.debug("Coleta SNMP ignorada: nenhum equipamento elegível/configurado.")
        return {"profiles": 0, "skipped": True}
    now = timezone.now()
    stale_seconds = int(getattr(settings, "SNMP_STATUS_STALE_SECONDS", 180))
    observations_by_profile = {}
    query_error = None
    try:
        observations_by_profile = influx_client.fetch_port_observations_many(
            [profile.influx_id for profile in profiles],
            lookback_minutes=max(5, (stale_seconds // 60) + 2),
        )
    except Exception as exc:  # noqa: BLE001
        query_error = exc
        logger.exception("Falha no query em lote do InfluxDB: %s", exc)

    processed = 0
    for profile in profiles:
        observations = observations_by_profile.get(profile.influx_id, [])
        try:
            with transaction.atomic():
                states = _sync_interface_states(profile, observations, now)
                if not states:
                    states = list(profile.interface_states.all())
                bindings = _sync_bindings(profile, states, now, stale_seconds)
                status = _profile_status(profile, states, bindings, now, stale_seconds)
                _update_profile_target(
                    profile, status, bindings, states, now,
                    observations_received=bool(observations),
                )
                if query_error is not None:
                    profile.last_poll_message = f"Erro ao consultar InfluxDB: {query_error}"
                    profile.save(update_fields=["last_poll_message", "updated_at"])
            processed += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("Falha ao processar perfil SNMP %s", profile.pk)
            SNMPMonitoringProfile.objects.filter(pk=profile.pk).update(
                last_poll_at=now,
                last_poll_message=f"Erro ao processar monitoramento: {exc}",
            )

    links = MonitoredNetworkLink.objects.filter(enabled=True).select_related(
        "company", "project", "cable__route", "source_element", "destination_element",
        "source_binding__profile__equipment__container", "source_binding__equipment_port",
        "destination_binding__profile__equipment__container", "destination_binding__equipment_port",
    )
    if profile_ids:
        links = links.filter(
            source_binding__profile_id__in=profile_ids
        ) | links.filter(destination_binding__profile_id__in=profile_ids)
    for link in links.distinct():
        try:
            _evaluate_link(link, now)
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao avaliar enlace monitorado %s", link.pk)

    bindings = SNMPPortBinding.objects.filter(enabled=True, alert_enabled=True).select_related(
        "company", "profile__element", "profile__equipment__container", "equipment_port",
    )
    if profile_ids:
        bindings = bindings.filter(profile_id__in=profile_ids)
    for binding in bindings:
        try:
            sync_port_alert(binding, now)
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao sincronizar alerta da porta %s", binding.pk)
    return processed
