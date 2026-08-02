from __future__ import annotations

from datetime import datetime

from apps.core.enums import OperationalStatus


DOWN_BINDING_STATES = {"down"}
UP_BINDING_STATES = {"up"}
UNKNOWN_BINDING_STATES = {"unknown", ""}


def raw_link_status(statuses, *, require_both: bool = True) -> str:
    """Calcula o estado bruto do enlace a partir das pontas monitoradas."""
    clean = [str(value or "unknown") for value in statuses if value is not None]
    if require_both and len(clean) < 2:
        return OperationalStatus.NO_DATA
    if not clean:
        return OperationalStatus.NO_DATA
    if any(value in DOWN_BINDING_STATES for value in clean):
        return OperationalStatus.OFFLINE
    up_count = sum(value in UP_BINDING_STATES for value in clean)
    if up_count == len(clean):
        return OperationalStatus.NORMAL
    if up_count:
        return OperationalStatus.DEGRADED
    if all(value in UNKNOWN_BINDING_STATES for value in clean):
        return OperationalStatus.NO_DATA
    return OperationalStatus.DEGRADED


def transition_threshold_seconds(candidate: str, outage_seconds: int, recovery_seconds: int) -> int:
    if candidate == OperationalStatus.NORMAL:
        return max(0, int(recovery_seconds or 0))
    if candidate == OperationalStatus.OFFLINE:
        return max(0, int(outage_seconds or 0))
    return 0


def transition_ready(
    *,
    current: str,
    candidate: str,
    candidate_since: datetime | None,
    now: datetime,
    outage_seconds: int,
    recovery_seconds: int,
) -> bool:
    if candidate == current:
        return False
    if candidate_since is None:
        return False
    threshold = transition_threshold_seconds(candidate, outage_seconds, recovery_seconds)
    return (now - candidate_since).total_seconds() >= threshold


def binding_operational_status(bindings) -> str:
    values = [binding.last_status for binding in bindings if binding.enabled and binding.expected_up]
    if not values:
        return OperationalStatus.NO_DATA
    if any(value == "down" for value in values):
        return OperationalStatus.OFFLINE
    if all(value == "up" for value in values):
        return OperationalStatus.NORMAL
    if any(value == "up" for value in values):
        return OperationalStatus.DEGRADED
    return OperationalStatus.NO_DATA


def _alert_payload_for_link(link):
    source = link.source_binding.display_name if link.source_binding_id else link.source_element.name
    destination = (
        link.destination_binding.display_name
        if link.destination_binding_id
        else link.destination_element.name
    )
    return {
        "company_id": link.company_id,
        "project_id": link.project_id,
        "project": link.project.name,
        "link_id": link.id,
        "link_type": link.link_type,
        "link_type_label": link.get_link_type_display(),
        "cable_id": link.cable_id,
        "cable": link.cable.name if link.cable_id else "",
        "source": source,
        "destination": destination,
        "source_binding_id": link.source_binding_id,
        "destination_binding_id": link.destination_binding_id,
        "status": link.status,
        "message": link.last_message,
    }


def sync_link_alert(link, now):
    """Abre/reabre e fecha o alerta único do enlace."""
    from apps.alerts.models import AlertEvent, AlertRule

    fingerprint = f"snmp-link:{link.id}"
    active_states = {
        AlertEvent.State.OPEN,
        AlertEvent.State.ACKNOWLEDGED,
        AlertEvent.State.RECOVERING,
    }
    event = AlertEvent.objects.filter(fingerprint=fingerprint).first()
    if link.status == OperationalStatus.OFFLINE and link.alert_enabled:
        title = f"Enlace offline · {link.name}"
        message = link.last_message or "Uma ou mais portas do enlace estão DOWN."
        defaults = {
            "company": link.company,
            "title": title,
            "message": message,
            "scope": AlertRule.Scope.LINK,
            "severity": link.severity,
            "state": AlertEvent.State.OPEN,
            "source_status": OperationalStatus.OFFLINE,
            "network_element": link.source_element,
            "monitored_link": link,
            "route": link.cable.route if link.cable_id and link.cable.route_id else None,
            "opened_at": now,
            "metadata": _alert_payload_for_link(link),
        }
        if event is None:
            AlertEvent.objects.create(fingerprint=fingerprint, **defaults)
        else:
            reopen = event.state not in active_states
            for field, value in defaults.items():
                setattr(event, field, value)
            if reopen:
                event.opened_at = now
                event.closed_at = None
                event.recovery_started_at = None
                event.acknowledged_at = None
                event.acknowledged_by = None
            event.save()
        return

    if event and event.state in active_states and link.status == OperationalStatus.NORMAL:
        event.state = AlertEvent.State.CLOSED
        event.source_status = OperationalStatus.NORMAL
        event.recovery_started_at = event.recovery_started_at or now
        event.closed_at = now
        event.message = f"Enlace recuperado: {link.name}."
        metadata = dict(event.metadata or {})
        metadata.update(_alert_payload_for_link(link))
        metadata["recovered_at"] = now.isoformat()
        event.metadata = metadata
        event.save()


def _alert_payload_for_binding(binding):
    profile = binding.profile
    element = profile.target_element
    return {
        "company_id": binding.company_id,
        "project_id": getattr(element, "project_id", None),
        "binding_id": binding.id,
        "profile_id": profile.id,
        "equipment_id": profile.equipment_id,
        "element_id": getattr(element, "id", None),
        "interface": binding.if_name,
        "if_index": binding.if_index,
        "port_id": binding.equipment_port_id,
        "port": binding.equipment_port.label if binding.equipment_port_id else binding.label,
        "role": binding.role,
        "status": binding.last_status,
    }


def sync_port_alert(binding, now):
    """Alerta uma porta avulsa. Portas usadas por um enlace geram só o
    alerta do enlace, evitando duplicidade no sino da empresa."""
    from apps.alerts.models import AlertEvent, AlertRule

    if binding.source_links.filter(enabled=True).exists() or binding.destination_links.filter(enabled=True).exists():
        return
    fingerprint = f"snmp-port:{binding.id}"
    active_states = {
        AlertEvent.State.OPEN,
        AlertEvent.State.ACKNOWLEDGED,
        AlertEvent.State.RECOVERING,
    }
    event = AlertEvent.objects.filter(fingerprint=fingerprint).first()
    down_ready = (
        binding.last_status == "down"
        and binding.down_since is not None
        and (now - binding.down_since).total_seconds() >= binding.outage_persistence_seconds
    )
    if down_ready and binding.alert_enabled:
        profile = binding.profile
        element = profile.target_element
        port_name = binding.equipment_port.label if binding.equipment_port_id else binding.label or binding.if_name
        defaults = {
            "company": binding.company,
            "title": f"Porta offline · {profile.target_name} · {port_name}",
            "message": f"A interface SNMP {binding.if_name} está DOWN.",
            "scope": AlertRule.Scope.PORT,
            "severity": binding.severity,
            "state": AlertEvent.State.OPEN,
            "source_status": OperationalStatus.OFFLINE,
            "network_element": element,
            "container_equipment": profile.equipment,
            "equipment_port": binding.equipment_port,
            "opened_at": now,
            "metadata": _alert_payload_for_binding(binding),
        }
        if event is None:
            AlertEvent.objects.create(fingerprint=fingerprint, **defaults)
        else:
            reopen = event.state not in active_states
            for field, value in defaults.items():
                setattr(event, field, value)
            if reopen:
                event.opened_at = now
                event.closed_at = None
                event.recovery_started_at = None
                event.acknowledged_at = None
                event.acknowledged_by = None
            event.save()
        return

    recovery_ready = (
        binding.last_status == "up"
        and binding.up_since is not None
        and (now - binding.up_since).total_seconds() >= binding.recovery_seconds
    )
    if event and event.state in active_states and recovery_ready:
        event.state = AlertEvent.State.CLOSED
        event.source_status = OperationalStatus.NORMAL
        event.recovery_started_at = event.recovery_started_at or now
        event.closed_at = now
        event.message = f"Porta recuperada: {binding.display_name}."
        metadata = dict(event.metadata or {})
        metadata.update(_alert_payload_for_binding(binding))
        metadata["recovered_at"] = now.isoformat()
        event.metadata = metadata
        event.save()
