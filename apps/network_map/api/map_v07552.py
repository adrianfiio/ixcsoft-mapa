from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company, scope_company_queryset
from apps.network_map.models import (
    ContainerEquipment,
    ContainerEquipmentPort,
    ContainerPortLink,
    NetworkElement,
)


VERSION = "0.75.52"
CHASSIS_SCHEMA_KEY = "v07547_chassis_schema"
COMPAT_CHASSIS_SCHEMA_KEY = "v07545_chassis_schema"
UPLINK_PROFILE_KEY = "v07549_uplink_profiles"
PORT_PROFILE_KEY = "v07551_port_profiles"
SUPPORTED_CONNECTORS = {"rj45", "sfp", "sfp_plus", "xfp", "qsfp_plus"}
SUPPORTED_SPEEDS = {Decimal("1"), Decimal("10"), Decimal("25"), Decimal("40"), Decimal("100")}
CONNECTOR_LABELS = {
    "rj45": "RJ45",
    "sfp": "SFP",
    "sfp_plus": "SFP+",
    "xfp": "XFP",
    "qsfp_plus": "QSFP+",
}
SPEED_CLASS = {
    Decimal("1"): "speed-1g",
    Decimal("10"): "speed-10g",
    Decimal("25"): "speed-25g",
    Decimal("40"): "speed-40g",
    Decimal("100"): "speed-100g",
}
LEGACY_PROFILE = {
    ContainerEquipmentPort.PortType.RJ45_100M: ("rj45", Decimal("1")),
    ContainerEquipmentPort.PortType.RJ45_1G: ("rj45", Decimal("1")),
    ContainerEquipmentPort.PortType.RJ45_2G5: ("rj45", Decimal("1")),
    ContainerEquipmentPort.PortType.SFP_1G: ("sfp", Decimal("1")),
    ContainerEquipmentPort.PortType.SFP_PLUS_10G: ("sfp_plus", Decimal("10")),
    ContainerEquipmentPort.PortType.SFP28_25G: ("sfp_plus", Decimal("25")),
    ContainerEquipmentPort.PortType.QSFP_PLUS_40G: ("qsfp_plus", Decimal("40")),
    ContainerEquipmentPort.PortType.QSFP28_100G: ("qsfp_plus", Decimal("100")),
}


def _container(request, element_id):
    return get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type=NetworkElement.ElementType.RACK,
    )


def _olt(container, equipment_id, *, lock=False):
    queryset = ContainerEquipment.objects.select_for_update() if lock else ContainerEquipment.objects
    return get_object_or_404(
        queryset.prefetch_related("ports", "cards__ports"),
        pk=equipment_id,
        container=container,
        equipment_type=ContainerEquipment.EquipmentType.OLT,
    )


def _bounded_int(value, minimum, maximum, default):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _schema(equipment):
    metadata = dict(equipment.metadata or {})
    raw = metadata.get(CHASSIS_SCHEMA_KEY)
    if not isinstance(raw, dict):
        raw = metadata.get(COMPAT_CHASSIS_SCHEMA_KEY)
    raw = dict(raw) if isinstance(raw, dict) else {}
    return {
        "uplink_slot_count": _bounded_int(raw.get("uplink_slot_count", 0), 0, 16, 0),
    }


def _decimal(value):
    try:
        parsed = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Velocidade inválida.") from exc
    if parsed not in SUPPORTED_SPEEDS:
        raise ValueError("Velocidade inválida. Use 1, 10, 25, 40 ou 100 Gbps.")
    return parsed


def _decimal_payload(value):
    return int(value) if value == value.to_integral_value() else float(value)


def _connector(value):
    raw = str(value or "").strip().casefold().replace(" ", "")
    aliases = {
        "rj45": "rj45", "sfp": "sfp", "sfp+": "sfp_plus",
        "sfpplus": "sfp_plus", "sfp_plus": "sfp_plus", "xfp": "xfp",
        "qsfp+": "qsfp_plus", "qsfpplus": "qsfp_plus", "qsfp_plus": "qsfp_plus",
    }
    result = aliases.get(raw)
    if result not in SUPPORTED_CONNECTORS:
        raise ValueError("Conector inválido. Use RJ45, SFP, SFP+, XFP ou QSFP+.")
    return result


def _port_type(connector, speed):
    if connector == "rj45":
        return ContainerEquipmentPort.PortType.RJ45_1G
    if connector == "sfp" and speed == Decimal("1"):
        return ContainerEquipmentPort.PortType.SFP_1G
    if speed == Decimal("25"):
        return ContainerEquipmentPort.PortType.SFP28_25G
    if speed == Decimal("40"):
        return ContainerEquipmentPort.PortType.QSFP_PLUS_40G
    if speed == Decimal("100"):
        return ContainerEquipmentPort.PortType.QSFP28_100G
    return ContainerEquipmentPort.PortType.SFP_PLUS_10G


def _uplink_profiles(equipment):
    raw = dict((equipment.metadata or {}).get(UPLINK_PROFILE_KEY) or {})
    result = {}
    for raw_slot, profile in raw.items():
        if not isinstance(profile, dict):
            continue
        try:
            slot = str(int(raw_slot))
        except (TypeError, ValueError):
            continue
        ids = []
        for value in profile.get("port_ids", []):
            try:
                ids.append(int(value))
            except (TypeError, ValueError):
                continue
        result[slot] = {"model": str(profile.get("model") or "")[:120], "port_ids": ids}
    return result


def _port_profiles(equipment):
    raw = dict((equipment.metadata or {}).get(PORT_PROFILE_KEY) or {})
    return {str(key): dict(value) for key, value in raw.items() if isinstance(value, dict)}


def _port_profile(port, profiles):
    raw = profiles.get(str(port.id)) or {}
    if raw:
        try:
            connector = _connector(raw.get("connector_type"))
            speed = _decimal(raw.get("speed_gbps"))
            return connector, speed
        except ValueError:
            pass
    return LEGACY_PROFILE.get(port.port_type, ("sfp_plus", Decimal("10")))


def _save_metadata(equipment, uplinks, ports):
    metadata = dict(equipment.metadata or {})
    metadata[UPLINK_PROFILE_KEY] = uplinks
    metadata[PORT_PROFILE_KEY] = ports
    equipment.metadata = metadata
    equipment.save(update_fields=["metadata", "updated_at"])


def _link_map(port_ids):
    links = ContainerPortLink.objects.filter(
        Q(source_port_id__in=port_ids) | Q(destination_port_id__in=port_ids)
    ).select_related("source_port__equipment", "destination_port__equipment").order_by("id")
    result = {}
    for link in links:
        if link.source_port_id in port_ids:
            result.setdefault(link.source_port_id, link)
        if link.destination_port_id in port_ids:
            result.setdefault(link.destination_port_id, link)
    return result


def _remote(port, link):
    if not link:
        return None
    return link.destination_port if link.source_port_id == port.id else link.source_port


def _remote_speed(remote):
    if not remote:
        return None
    profiles = _port_profiles(remote.equipment)
    return _port_profile(remote, profiles)[1]


def _payload(equipment):
    schema = _schema(equipment)
    uplinks = _uplink_profiles(equipment)
    profiles = _port_profiles(equipment)
    port_map = {port.id: port for port in equipment.ports.select_related("equipment").all()}
    all_ids = [port_id for profile in uplinks.values() for port_id in profile["port_ids"]]
    links = _link_map(all_ids)
    slots = []
    for slot in range(1, schema["uplink_slot_count"] + 1):
        profile = uplinks.get(str(slot))
        rows = []
        if profile:
            for index, port_id in enumerate(profile["port_ids"], 1):
                port = port_map.get(port_id)
                if not port:
                    continue
                connector, speed = _port_profile(port, profiles)
                link = links.get(port.id)
                remote = _remote(port, link)
                effective = min(speed, _remote_speed(remote)) if link and _remote_speed(remote) else (speed if link else None)
                rows.append({
                    "id": port.id,
                    "index": index,
                    "name": port.label,
                    "label": port.label,
                    "port_type": port.port_type,
                    "port_type_label": port.get_port_type_display(),
                    "connector_type": connector,
                    "connector_type_label": CONNECTOR_LABELS[connector],
                    "speed_gbps": _decimal_payload(speed),
                    "effective_speed_gbps": _decimal_payload(effective) if effective is not None else None,
                    "speed_class": SPEED_CLASS.get(effective, "") if effective is not None else "",
                    "linked": bool(link),
                    "link_id": link.id if link else None,
                    "remote_equipment": remote.equipment.name if remote else "",
                    "remote_port": remote.label if remote else "",
                })
        slots.append({
            "slot": slot,
            "empty": not bool(profile and rows),
            "card": None if not profile else {
                "model": profile["model"],
                "ports": rows,
                "linked_ports": sum(1 for row in rows if row["linked"]),
            },
        })
    return {
        "version": VERSION,
        "equipment": {"id": equipment.id, "name": equipment.name},
        "uplink_slot_count": schema["uplink_slot_count"],
        "uplink_slots": slots,
        "connector_types": [{"value": key, "label": value} for key, value in CONNECTOR_LABELS.items()],
        "speed_options": [1, 10, 25, 40, 100],
    }


def _specs(raw):
    if not isinstance(raw, list) or not raw or len(raw) > 32:
        raise ValueError("Informe entre 1 e 32 portas de uplink.")
    result = []
    names = set()
    for index, row in enumerate(raw, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Porta de uplink #{index} inválida.")
        name = str(row.get("name") or f"Uplink {index}").strip()[:100]
        if not name:
            raise ValueError(f"Informe o nome da porta #{index}.")
        if name.casefold() in names:
            raise ValueError(f"Nome de porta duplicado: {name}.")
        names.add(name.casefold())
        connector = _connector(row.get("connector_type"))
        speed = _decimal(row.get("speed_gbps"))
        result.append({"name": name, "connector": connector, "speed": speed})
    return result


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def olt_uplink_slots_v07552(request, element_id, equipment_id):
    container = _container(request, element_id)
    equipment = _olt(container, equipment_id)
    if request.method == "GET":
        return JsonResponse(_payload(equipment))
    if not can_edit_company(request.user, container.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)

    data: dict[str, Any] = request.data if isinstance(request.data, dict) else {}
    action = str(data.get("action") or "").strip().lower()
    schema = _schema(equipment)
    try:
        slot = int(data.get("slot") or 0)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Slot de uplink inválido."}, status=400)
    if slot < 1 or slot > schema["uplink_slot_count"]:
        return JsonResponse({"detail": "Slot de uplink fora do chassi configurado."}, status=400)

    with transaction.atomic():
        equipment = _olt(container, equipment_id, lock=True)
        uplinks = _uplink_profiles(equipment)
        profiles = _port_profiles(equipment)
        current = uplinks.get(str(slot))
        current_ids = list(current.get("port_ids", [])) if current else []
        linked = ContainerPortLink.objects.filter(
            Q(source_port_id__in=current_ids) | Q(destination_port_id__in=current_ids)
        ).exists()

        if action == "remove_uplink_card":
            if linked:
                return JsonResponse({"detail": "Desligue todas as portas da placa antes de removê-la."}, status=409)
            equipment.ports.filter(id__in=current_ids).delete()
            for port_id in current_ids:
                profiles.pop(str(port_id), None)
            uplinks.pop(str(slot), None)
            _save_metadata(equipment, uplinks, profiles)
            return JsonResponse(_payload(_olt(container, equipment_id)))

        if action != "save_uplink_card":
            return JsonResponse({"detail": "Ação de uplink inválida."}, status=400)
        model = str(data.get("model") or "").strip()[:120]
        if not model:
            return JsonResponse({"detail": "Informe o modelo da placa de uplink."}, status=400)
        try:
            specs = _specs(data.get("port_specs"))
        except ValueError as exc:
            return JsonResponse({"detail": str(exc)}, status=400)
        if linked and len(specs) != len(current_ids):
            return JsonResponse({"detail": "Desligue as portas antes de alterar a quantidade."}, status=409)

        current_port_map = {port.id: port for port in equipment.ports.filter(id__in=current_ids)}
        current_ports = [current_port_map[port_id] for port_id in current_ids if port_id in current_port_map]
        if len(current_ports) != len(specs):
            if linked:
                return JsonResponse({"detail": "Desligue as portas antes de recriar a placa."}, status=409)
            equipment.ports.filter(id__in=current_ids).delete()
            for port_id in current_ids:
                profiles.pop(str(port_id), None)
            start = (equipment.ports.order_by("-number").values_list("number", flat=True).first() or 0) + 1
            current_ports = [
                ContainerEquipmentPort.objects.create(
                    equipment=equipment,
                    port_type=_port_type(spec["connector"], spec["speed"]),
                    number=start + index - 1,
                    card_number=0,
                    port_number=index,
                    label=spec["name"],
                )
                for index, spec in enumerate(specs, 1)
            ]
        else:
            for index, (port, spec) in enumerate(zip(current_ports, specs), 1):
                port.label = spec["name"]
                port.port_type = _port_type(spec["connector"], spec["speed"])
                port.port_number = index
            ContainerEquipmentPort.objects.bulk_update(current_ports, ["label", "port_type", "port_number"])

        for index, (port, spec) in enumerate(zip(current_ports, specs), 1):
            profiles[str(port.id)] = {
                "connector_type": spec["connector"],
                "speed_gbps": _decimal_payload(spec["speed"]),
                "external_key": f"olt-{equipment.id}-uplink-{slot}-{index}",
                "source_name": spec["name"],
                "source_type": spec["connector"],
                "description": f"Placa {model} · slot U{slot}",
                "order": index,
            }
        uplinks[str(slot)] = {"model": model, "port_ids": [port.id for port in current_ports]}
        _save_metadata(equipment, uplinks, profiles)

    return JsonResponse(_payload(_olt(container, equipment_id)))
