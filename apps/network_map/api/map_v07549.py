from __future__ import annotations

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


VERSION = "0.75.49"
CHASSIS_SCHEMA_KEY = "v07547_chassis_schema"
COMPAT_CHASSIS_SCHEMA_KEY = "v07545_chassis_schema"
UPLINK_PROFILE_KEY = "v07549_uplink_profiles"
SUPPORTED_UPLINK_TYPES = {
    ContainerEquipmentPort.PortType.RJ45_1G,
    ContainerEquipmentPort.PortType.SFP_1G,
    ContainerEquipmentPort.PortType.SFP_PLUS_10G,
}
UPLINK_TYPE_LABELS = {
    ContainerEquipmentPort.PortType.RJ45_1G: "RJ45 1G",
    ContainerEquipmentPort.PortType.SFP_1G: "SFP 1G",
    ContainerEquipmentPort.PortType.SFP_PLUS_10G: "SFP+ 10G",
}
UPLINK_TYPE_COLORS = {
    ContainerEquipmentPort.PortType.RJ45_1G: "green",
    ContainerEquipmentPort.PortType.SFP_1G: "green",
    ContainerEquipmentPort.PortType.SFP_PLUS_10G: "blue",
}


def _container(request, element_id):
    return get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type=NetworkElement.ElementType.RACK,
    )


def _olt(container, equipment_id):
    return get_object_or_404(
        ContainerEquipment.objects.prefetch_related("ports", "cards__ports"),
        pk=equipment_id,
        container=container,
        equipment_type=ContainerEquipment.EquipmentType.OLT,
    )


def _can_edit(request, container):
    return can_edit_company(request.user, container.company_id)


def _bounded_int(value, *, minimum, maximum, default):
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
        "service_slot_count": _bounded_int(
            raw.get("service_slot_count", raw.get("slot_count", equipment.card_count or 1)),
            minimum=1,
            maximum=32,
            default=max(1, equipment.card_count or 1),
        ),
        "uplink_slot_count": _bounded_int(
            raw.get("uplink_slot_count", 0),
            minimum=0,
            maximum=16,
            default=0,
        ),
    }


def _profiles(equipment):
    raw = dict((equipment.metadata or {}).get(UPLINK_PROFILE_KEY) or {})
    result = {}
    for raw_slot, raw_profile in raw.items():
        try:
            slot = int(raw_slot)
        except (TypeError, ValueError):
            continue
        if not isinstance(raw_profile, dict):
            continue
        port_ids = []
        for value in raw_profile.get("port_ids", []):
            try:
                port_ids.append(int(value))
            except (TypeError, ValueError):
                continue
        result[str(slot)] = {
            "model": str(raw_profile.get("model") or "").strip()[:120],
            "port_ids": port_ids,
        }
    return result


def _save_profiles(equipment, profiles):
    metadata = dict(equipment.metadata or {})
    metadata[UPLINK_PROFILE_KEY] = profiles
    equipment.metadata = metadata
    equipment.save(update_fields=["metadata", "updated_at"])


def _port_link(port):
    return (
        ContainerPortLink.objects
        .filter(Q(source_port=port) | Q(destination_port=port))
        .order_by("id")
        .first()
    )


def _port_payload(port, index):
    link = _port_link(port)
    return {
        "id": port.id,
        "index": index,
        "number": port.number,
        "label": port.label,
        "port_type": port.port_type,
        "port_type_label": UPLINK_TYPE_LABELS.get(port.port_type, port.get_port_type_display()),
        "state_color": UPLINK_TYPE_COLORS.get(port.port_type, "neutral"),
        "linked": bool(link),
        "link_id": link.id if link else None,
    }


def _payload(equipment):
    schema = _schema(equipment)
    profiles = _profiles(equipment)
    port_map = {port.id: port for port in equipment.ports.all()}
    slots = []
    for slot in range(1, schema["uplink_slot_count"] + 1):
        profile = profiles.get(str(slot))
        ports = []
        if profile:
            for index, port_id in enumerate(profile["port_ids"], start=1):
                port = port_map.get(port_id)
                if port:
                    ports.append(_port_payload(port, index))
        slots.append({
            "slot": slot,
            "empty": not bool(profile and ports),
            "card": None if not profile else {
                "model": profile["model"],
                "ports": ports,
                "linked_ports": sum(1 for port in ports if port["linked"]),
            },
        })
    return {
        "version": VERSION,
        "equipment": {
            "id": equipment.id,
            "name": equipment.name,
        },
        "uplink_slot_count": schema["uplink_slot_count"],
        "uplink_slots": slots,
        "port_types": [
            {
                "value": value,
                "label": UPLINK_TYPE_LABELS[value],
                "state_color": UPLINK_TYPE_COLORS[value],
            }
            for value in (
                ContainerEquipmentPort.PortType.RJ45_1G,
                ContainerEquipmentPort.PortType.SFP_1G,
                ContainerEquipmentPort.PortType.SFP_PLUS_10G,
            )
        ],
    }


def _next_port_number(equipment):
    return (equipment.ports.order_by("-number").values_list("number", flat=True).first() or 0) + 1


def _linked_port_ids(port_ids):
    if not port_ids:
        return set()
    return set(
        ContainerPortLink.objects
        .filter(Q(source_port_id__in=port_ids) | Q(destination_port_id__in=port_ids))
        .values_list("source_port_id", "destination_port_id")
        .iterator()
    )


def _has_linked_ports(port_ids):
    if not port_ids:
        return False
    return ContainerPortLink.objects.filter(
        Q(source_port_id__in=port_ids) | Q(destination_port_id__in=port_ids)
    ).exists()


def _normalize_port_types(raw):
    if not isinstance(raw, list):
        return None
    result = []
    for value in raw:
        port_type = str(value or "").strip()
        if port_type not in SUPPORTED_UPLINK_TYPES:
            return None
        result.append(port_type)
    return result


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def olt_uplink_slots_v07549(request, element_id, equipment_id):
    container = _container(request, element_id)
    equipment = _olt(container, equipment_id)
    if request.method == "GET":
        return JsonResponse(_payload(equipment))
    if not _can_edit(request, container):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)

    data = request.data if isinstance(request.data, dict) else {}
    action = str(data.get("action") or "").strip().lower()
    schema = _schema(equipment)
    try:
        slot = int(data.get("slot") or 0)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Slot de uplink inválido."}, status=400)
    if slot < 1 or slot > schema["uplink_slot_count"]:
        return JsonResponse({"detail": "Slot de uplink fora do chassi configurado."}, status=400)

    profiles = _profiles(equipment)
    current = profiles.get(str(slot))
    current_ids = list(current.get("port_ids", [])) if current else []

    if action == "remove_uplink_card":
        if not current:
            return JsonResponse(_payload(equipment))
        if _has_linked_ports(current_ids):
            return JsonResponse(
                {"detail": "Desligue todas as portas desta placa de uplink antes de removê-la."},
                status=409,
            )
        with transaction.atomic():
            equipment.ports.filter(id__in=current_ids).delete()
            profiles.pop(str(slot), None)
            _save_profiles(equipment, profiles)
        return JsonResponse(_payload(equipment))

    if action != "save_uplink_card":
        return JsonResponse({"detail": "Ação de uplink inválida."}, status=400)

    model = str(data.get("model") or "").strip()[:120]
    port_types = _normalize_port_types(data.get("port_types"))
    if not model:
        return JsonResponse({"detail": "Informe o modelo da placa de uplink."}, status=400)
    if not port_types or len(port_types) > 32:
        return JsonResponse({"detail": "Informe entre 1 e 32 portas de uplink válidas."}, status=400)

    current_ports = list(equipment.ports.filter(id__in=current_ids).order_by("id"))
    current_types = [port.port_type for port in current_ports]
    if _has_linked_ports(current_ids) and current_types != port_types:
        return JsonResponse(
            {"detail": "Desligue as portas da placa antes de alterar quantidade ou tipo físico."},
            status=409,
        )

    with transaction.atomic():
        if current_types != port_types:
            equipment.ports.filter(id__in=current_ids).delete()
            start = _next_port_number(equipment)
            created = []
            for index, port_type in enumerate(port_types, start=1):
                created.append(ContainerEquipmentPort.objects.create(
                    equipment=equipment,
                    card=None,
                    port_type=port_type,
                    number=start + index - 1,
                    card_number=0,
                    port_number=index,
                    label=f"U{slot} / {UPLINK_TYPE_LABELS[port_type]} {index}",
                ))
            current_ids = [port.id for port in created]
        profiles[str(slot)] = {
            "model": model,
            "port_ids": current_ids,
        }
        _save_profiles(equipment, profiles)

    equipment = _olt(container, equipment_id)
    return JsonResponse(_payload(equipment))
