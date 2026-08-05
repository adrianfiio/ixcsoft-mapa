from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company, scope_company_queryset
from apps.network_map.models import (
    ContainerEquipment,
    ContainerEquipmentCard,
    ContainerEquipmentPort,
    ContainerPortLink,
    NetworkElement,
)


VERSION = "0.75.48"
CHASSIS_SCHEMA_KEY = "v07547_chassis_schema"
COMPAT_CHASSIS_SCHEMA_KEY = "v07545_chassis_schema"
CARD_PROFILE_KEY = "v07545_card_profiles"
LEGACY_CARD_PROFILE_KEY = "v07543_card_profiles"
PORT_POWER_KEY = "v07548_port_tx_power_dbm"
ORIENTATIONS = {"vertical", "horizontal"}
TECHNOLOGIES = {"gpon", "xgpon", "xgspon"}


def _container(request, element_id):
    return get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type=NetworkElement.ElementType.RACK,
    )


def _olt(container, equipment_id):
    return get_object_or_404(
        ContainerEquipment.objects.prefetch_related("cards__ports", "ports"),
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


def _decimal_or_none(value, *, minimum=-50, maximum=20):
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Potência óptica inválida.")
    if parsed < Decimal(str(minimum)) or parsed > Decimal(str(maximum)):
        raise ValueError(f"Informe uma potência entre {minimum} e {maximum} dBm.")
    return parsed.quantize(Decimal("0.01"))


def _schema(equipment):
    metadata = dict(equipment.metadata or {})
    raw = metadata.get(CHASSIS_SCHEMA_KEY)
    if not isinstance(raw, dict):
        raw = metadata.get(COMPAT_CHASSIS_SCHEMA_KEY)
    raw = dict(raw) if isinstance(raw, dict) else {}
    orientation = str(raw.get("orientation") or "horizontal").lower()
    if orientation not in ORIENTATIONS:
        orientation = "horizontal"
    service_slots = _bounded_int(
        raw.get("service_slot_count", raw.get("slot_count", equipment.card_count or 1)),
        minimum=1,
        maximum=32,
        default=max(1, equipment.card_count or 1),
    )
    uplink_slots = _bounded_int(raw.get("uplink_slot_count", 0), minimum=0, maximum=16, default=0)
    return {
        "orientation": orientation,
        "service_slot_count": service_slots,
        "uplink_slot_count": uplink_slots,
        "slot_count": service_slots,
        "chassis_model": str(raw.get("chassis_model") or equipment.model or "").strip(),
    }


def _profiles(equipment):
    metadata = dict(equipment.metadata or {})
    current = metadata.get(CARD_PROFILE_KEY)
    if isinstance(current, dict):
        return dict(current)
    legacy = metadata.get(LEGACY_CARD_PROFILE_KEY)
    return dict(legacy) if isinstance(legacy, dict) else {}


def _port_powers(equipment):
    raw = dict((equipment.metadata or {}).get(PORT_POWER_KEY) or {})
    result = {}
    for key, value in raw.items():
        try:
            result[str(int(key))] = float(value)
        except (TypeError, ValueError):
            continue
    return result


def _link_for_source(port):
    return (
        ContainerPortLink.objects
        .filter(source_port=port)
        .select_related("destination_port__equipment", "cable", "cable_fiber")
        .order_by("id")
        .first()
    )


def _rear_link_for_dio_port(port):
    return (
        ContainerPortLink.objects
        .filter(destination_port=port)
        .filter(Q(cable_fiber__isnull=False) | Q(source_port__isnull=True, cable__isnull=False))
        .select_related("cable", "cable_fiber", "destination_port__equipment")
        .order_by("id")
        .first()
    )


def _front_link_for_dio_port(port):
    return (
        ContainerPortLink.objects
        .filter(destination_port=port, source_port__isnull=False)
        .select_related("source_port__equipment", "destination_port__equipment")
        .order_by("id")
        .first()
    )


def _port_payload(equipment, port, powers):
    power = powers.get(str(port.id))
    if power is None and equipment.tx_power_dbm is not None:
        power = float(equipment.tx_power_dbm)
    link = _link_for_source(port)
    return {
        "id": port.id,
        "number": port.port_number or port.number,
        "global_number": port.number,
        "label": port.label,
        "port_type": port.port_type,
        "linked": bool(link),
        "link_id": link.id if link else None,
        "tx_power_dbm": power,
    }


def _card_payload(equipment, card, powers):
    profile = dict(_profiles(equipment).get(str(card.id)) or {})
    technology = str(profile.get("technology") or "gpon").lower()
    if technology not in TECHNOLOGIES:
        technology = "gpon"
    ports = [
        _port_payload(equipment, port, powers)
        for port in card.ports.filter(port_type=ContainerEquipmentPort.PortType.PON).order_by("port_number", "number", "id")
    ]
    return {
        "id": card.id,
        "slot": card.slot,
        "name": card.name or f"Placa {card.slot}",
        "model": str(profile.get("model") or card.model or "").strip(),
        "technology": technology,
        "ports": ports,
    }


def _editor_payload(equipment):
    schema = _schema(equipment)
    powers = _port_powers(equipment)
    cards_by_slot = {
        card.slot: _card_payload(equipment, card, powers)
        for card in equipment.cards.all().order_by("slot", "id")
        if card.slot <= schema["service_slot_count"]
    }
    slots = [
        {
            "slot": slot,
            "empty": slot not in cards_by_slot,
            "card": cards_by_slot.get(slot),
        }
        for slot in range(1, schema["service_slot_count"] + 1)
    ]
    return {
        "version": VERSION,
        "equipment": {
            "id": equipment.id,
            "name": equipment.name,
            "description": equipment.description,
            "vendor": equipment.vendor,
            "model": equipment.model,
            "serial_number": equipment.serial_number,
            "management_ip": equipment.management_ip,
            "provisioning_mode": equipment.provisioning_mode,
            "tx_power_dbm": float(equipment.tx_power_dbm) if equipment.tx_power_dbm is not None else None,
            "enabled": equipment.enabled,
        },
        "chassis": schema,
        "slots": slots,
        "uplink_slots": [
            {"slot": slot, "empty": True}
            for slot in range(1, schema["uplink_slot_count"] + 1)
        ],
    }


def _save_schema(equipment, schema):
    metadata = dict(equipment.metadata or {})
    metadata[CHASSIS_SCHEMA_KEY] = dict(schema)
    metadata[COMPAT_CHASSIS_SCHEMA_KEY] = {
        "orientation": schema["orientation"],
        "slot_count": schema["service_slot_count"],
        "chassis_model": schema["chassis_model"],
    }
    equipment.metadata = metadata


def _topology_payload(container):
    rear_links = (
        ContainerPortLink.objects
        .filter(container=container, destination_port__equipment__equipment_type=ContainerEquipment.EquipmentType.DIO)
        .filter(Q(cable_fiber__isnull=False) | Q(source_port__isnull=True, cable__isnull=False))
        .select_related("destination_port__equipment", "cable", "cable_fiber")
        .order_by("id")
    )
    front_links = (
        ContainerPortLink.objects
        .filter(container=container, source_port__isnull=False, destination_port__equipment__equipment_type=ContainerEquipment.EquipmentType.DIO)
        .select_related("source_port__equipment", "destination_port__equipment")
        .order_by("id")
    )
    active_types = {
        ContainerEquipment.EquipmentType.OLT,
        ContainerEquipment.EquipmentType.DIO,
        ContainerEquipment.EquipmentType.SWITCH,
    }
    essential_count = ContainerEquipment.objects.filter(container=container, equipment_type__in=active_types).count()
    return {
        "version": VERSION,
        "essential_equipment_count": essential_count,
        "rear_links": [
            {
                "id": link.id,
                "dio_id": link.destination_port.equipment_id,
                "dio_port_id": link.destination_port_id,
                "dio_port_number": link.destination_port.port_number or link.destination_port.number,
                "cable_id": link.cable_id,
                "cable_name": link.cable.name if link.cable else "",
                "fiber_id": link.cable_fiber_id,
                "fiber_number": link.cable_fiber.number if link.cable_fiber else None,
                "loss_db": float(link.loss_db or 0),
            }
            for link in rear_links
        ],
        "front_links": [
            {
                "id": link.id,
                "source_equipment_id": link.source_port.equipment_id,
                "source_port_id": link.source_port_id,
                "destination_equipment_id": link.destination_port.equipment_id,
                "destination_port_id": link.destination_port_id,
                "loss_db": float(link.loss_db or 0),
            }
            for link in front_links
        ],
    }


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def olt_editor_v07548(request, element_id, equipment_id):
    container = _container(request, element_id)
    equipment = _olt(container, equipment_id)
    if request.method == "GET":
        return JsonResponse(_editor_payload(equipment))
    if not _can_edit(request, container):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)

    data = request.data if isinstance(request.data, dict) else {}
    schema = _schema(equipment)
    orientation = str(data.get("orientation", schema["orientation"]) or "horizontal").lower()
    if orientation not in ORIENTATIONS:
        return JsonResponse({"detail": "Disposição das placas inválida."}, status=400)
    service_slots = _bounded_int(
        data.get("service_slot_count", schema["service_slot_count"]),
        minimum=1,
        maximum=32,
        default=schema["service_slot_count"],
    )
    uplink_slots = _bounded_int(
        data.get("uplink_slot_count", schema["uplink_slot_count"]),
        minimum=0,
        maximum=16,
        default=schema["uplink_slot_count"],
    )
    highest_card_slot = equipment.cards.order_by("-slot").values_list("slot", flat=True).first() or 0
    if service_slots < highest_card_slot:
        return JsonResponse(
            {"detail": f"Remova ou mova a placa do slot S{highest_card_slot} antes de reduzir o chassi."},
            status=409,
        )

    try:
        default_power = _decimal_or_none(data.get("tx_power_dbm", equipment.tx_power_dbm))
    except ValueError as error:
        return JsonResponse({"detail": str(error)}, status=400)

    port_power_data = data.get("port_tx_power_dbm")
    if port_power_data is not None and not isinstance(port_power_data, dict):
        return JsonResponse({"detail": "Potências das portas devem ser enviadas como objeto."}, status=400)

    with transaction.atomic():
        for field, maximum in (
            ("name", 180),
            ("description", 10000),
            ("vendor", 80),
            ("serial_number", 120),
        ):
            if field in data:
                value = str(data.get(field) or "").strip()[:maximum]
                if field == "name" and not value:
                    return JsonResponse({"detail": "Informe o nome da OLT."}, status=400)
                setattr(equipment, field, value)
        if "management_ip" in data:
            equipment.management_ip = str(data.get("management_ip") or "").strip() or None
        if "provisioning_mode" in data:
            mode = str(data.get("provisioning_mode") or "manual")
            if mode not in dict(ContainerEquipment.ProvisioningMode.choices):
                return JsonResponse({"detail": "Modo de provisionamento inválido."}, status=400)
            equipment.provisioning_mode = mode
        equipment.enabled = bool(data.get("enabled", equipment.enabled))
        equipment.tx_power_dbm = default_power
        chassis_model = str(data.get("chassis_model") or data.get("model") or schema["chassis_model"] or "").strip()[:120]
        equipment.model = chassis_model
        equipment.card_count = service_slots
        equipment.pons_per_card = 0
        next_schema = {
            "orientation": orientation,
            "service_slot_count": service_slots,
            "uplink_slot_count": uplink_slots,
            "slot_count": service_slots,
            "chassis_model": chassis_model,
        }
        _save_schema(equipment, next_schema)
        metadata = dict(equipment.metadata or {})
        powers = dict(metadata.get(PORT_POWER_KEY) or {})
        if isinstance(port_power_data, dict):
            allowed_ids = set(
                equipment.ports.filter(port_type=ContainerEquipmentPort.PortType.PON).values_list("id", flat=True)
            )
            for raw_id, raw_power in port_power_data.items():
                try:
                    port_id = int(raw_id)
                except (TypeError, ValueError):
                    continue
                if port_id not in allowed_ids:
                    continue
                try:
                    power = _decimal_or_none(raw_power)
                except ValueError as error:
                    return JsonResponse({"detail": f"PON {port_id}: {error}"}, status=400)
                if power is None:
                    powers.pop(str(port_id), None)
                else:
                    powers[str(port_id)] = float(power)
        metadata[PORT_POWER_KEY] = powers
        equipment.metadata = metadata
        equipment.save()

    return JsonResponse(_editor_payload(equipment))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def rack_topology_v07548(request, element_id):
    container = _container(request, element_id)
    return JsonResponse(_topology_payload(container))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def olt_port_path_v07548(request, element_id, equipment_id, port_id):
    container = _container(request, element_id)
    equipment = _olt(container, equipment_id)
    port = get_object_or_404(
        ContainerEquipmentPort,
        pk=port_id,
        equipment=equipment,
        port_type=ContainerEquipmentPort.PortType.PON,
    )
    powers = _port_powers(equipment)
    tx_power = powers.get(str(port.id))
    if tx_power is None and equipment.tx_power_dbm is not None:
        tx_power = float(equipment.tx_power_dbm)

    segments = [{
        "kind": "olt_port",
        "equipment_id": equipment.id,
        "equipment": equipment.name,
        "port_id": port.id,
        "port": port.label,
        "power_dbm": tx_power,
    }]
    total_loss = Decimal("0")
    front = _link_for_source(port)
    dio_port = None
    if front:
        total_loss += front.loss_db or Decimal("0")
        dio_port = front.destination_port
        segments.append({
            "kind": "front_link",
            "link_id": front.id,
            "loss_db": float(front.loss_db or 0),
            "dio_id": dio_port.equipment_id,
            "dio": dio_port.equipment.name,
            "dio_port_id": dio_port.id,
            "dio_port": dio_port.label,
        })

    rear = _rear_link_for_dio_port(dio_port) if dio_port else None
    if rear:
        total_loss += rear.loss_db or Decimal("0")
        segments.append({
            "kind": "rear_link",
            "link_id": rear.id,
            "loss_db": float(rear.loss_db or 0),
            "cable_id": rear.cable_id,
            "cable": rear.cable.name if rear.cable else "",
            "fiber_id": rear.cable_fiber_id,
            "fiber_number": rear.cable_fiber.number if rear.cable_fiber else None,
        })

    estimated = None if tx_power is None else float(Decimal(str(tx_power)) - total_loss)
    return JsonResponse({
        "version": VERSION,
        "complete_to_cable": bool(front and rear),
        "tx_power_dbm": tx_power,
        "total_known_loss_db": float(total_loss),
        "estimated_power_after_dio_dbm": estimated,
        "segments": segments,
        "cable_id": rear.cable_id if rear else None,
        "dio_port_id": dio_port.id if dio_port else None,
    })
