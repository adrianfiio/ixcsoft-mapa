from __future__ import annotations

from django.db import IntegrityError, transaction
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


VERSION = "0.75.45"
CHASSIS_SCHEMA_KEY = "v07545_chassis_schema"
CARD_PROFILE_KEY = "v07545_card_profiles"
LEGACY_CARD_PROFILE_KEY = "v07543_card_profiles"
LEGACY_UPLINK_GROUPS_KEY = "v07544_uplink_groups"
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
        ContainerEquipment.objects,
        pk=equipment_id,
        container=container,
        equipment_type=ContainerEquipment.EquipmentType.OLT,
    )


def _can_edit(request, container):
    return can_edit_company(request.user, container.company_id)


def _port_link(port):
    return (
        ContainerPortLink.objects
        .filter(Q(source_port=port) | Q(destination_port=port))
        .order_by("id")
        .first()
    )


def _port_payload(port):
    link = _port_link(port)
    return {
        "id": port.id,
        "number": port.port_number or port.number,
        "global_number": port.number,
        "label": port.label,
        "port_type": port.port_type,
        "port_type_label": port.get_port_type_display(),
        "link_id": link.id if link else None,
        "linked": bool(link),
    }


def _schema(equipment):
    metadata = dict(equipment.metadata or {})
    raw = metadata.get(CHASSIS_SCHEMA_KEY)
    if isinstance(raw, dict):
        orientation = str(raw.get("orientation") or "horizontal").lower()
        if orientation not in ORIENTATIONS:
            orientation = "horizontal"
        try:
            slot_count = int(raw.get("slot_count") or equipment.card_count or 1)
        except (TypeError, ValueError):
            slot_count = equipment.card_count or 1
        return {
            "orientation": orientation,
            "slot_count": max(1, min(slot_count, 16)),
            "chassis_model": str(raw.get("chassis_model") or equipment.model or "").strip(),
        }

    max_slot = equipment.cards.order_by("-slot").values_list("slot", flat=True).first() or 0
    return {
        "orientation": "horizontal",
        "slot_count": max(1, min(int(equipment.card_count or max_slot or 1), 16)),
        "chassis_model": str(equipment.model or "").strip(),
    }


def _profiles(equipment):
    metadata = dict(equipment.metadata or {})
    current = metadata.get(CARD_PROFILE_KEY)
    if isinstance(current, dict):
        return dict(current)
    legacy = metadata.get(LEGACY_CARD_PROFILE_KEY)
    return dict(legacy) if isinstance(legacy, dict) else {}


def _card_payload(equipment, card):
    profiles = _profiles(equipment)
    profile = dict(profiles.get(str(card.id)) or {})
    technology = str(profile.get("technology") or "gpon").lower()
    if technology not in TECHNOLOGIES:
        technology = "gpon"
    ports = [
        _port_payload(port)
        for port in card.ports.filter(
            port_type=ContainerEquipmentPort.PortType.PON,
        ).order_by("port_number", "number", "id")
    ]
    return {
        "id": card.id,
        "slot": card.slot,
        "name": card.name or f"Placa {card.slot}",
        "model": str(profile.get("model") or card.model or "").strip(),
        "technology": technology,
        "pon_count": len(ports),
        "ports": ports,
        "linked_ports": sum(1 for port in ports if port["linked"]),
    }


def _hardware_payload(equipment):
    schema = _schema(equipment)
    cards_by_slot = {
        card.slot: _card_payload(equipment, card)
        for card in equipment.cards.all().order_by("slot", "id")
        if card.slot <= schema["slot_count"]
    }
    slots = []
    for slot in range(1, schema["slot_count"] + 1):
        slots.append({
            "slot": slot,
            "empty": slot not in cards_by_slot,
            "card": cards_by_slot.get(slot),
        })
    metadata = dict(equipment.metadata or {})
    legacy_uplinks = metadata.get(LEGACY_UPLINK_GROUPS_KEY)
    return {
        "version": VERSION,
        "equipment": {
            "id": equipment.id,
            "name": equipment.name,
            "vendor": equipment.vendor,
            "model": equipment.model,
            "management_ip": equipment.management_ip,
        },
        "chassis": schema,
        "slots": slots,
        "legacy_uplink_groups": len(legacy_uplinks) if isinstance(legacy_uplinks, list) else 0,
    }


def _next_port_number(equipment, excluded_card=None):
    queryset = equipment.ports.all()
    if excluded_card is not None:
        queryset = queryset.exclude(card=excluded_card)
    return (queryset.order_by("-number").values_list("number", flat=True).first() or 0) + 1


def _create_card_ports(equipment, card, pon_count):
    start = _next_port_number(equipment, excluded_card=card)
    ports = []
    for offset, pon in enumerate(range(1, pon_count + 1)):
        ports.append(ContainerEquipmentPort(
            equipment=equipment,
            card=card,
            port_type=ContainerEquipmentPort.PortType.PON,
            number=start + offset,
            card_number=card.slot,
            port_number=pon,
            label=f"S{card.slot} / PON {pon}",
        ))
    ContainerEquipmentPort.objects.bulk_create(ports)


def _save_profile(equipment, card, *, model, technology):
    metadata = dict(equipment.metadata or {})
    profiles = _profiles(equipment)
    profiles[str(card.id)] = {
        "model": model,
        "technology": technology,
    }
    metadata[CARD_PROFILE_KEY] = profiles
    metadata.pop(LEGACY_CARD_PROFILE_KEY, None)
    equipment.metadata = metadata
    equipment.save(update_fields=["metadata", "updated_at"])


def _linked_card(card):
    port_ids = list(card.ports.values_list("id", flat=True))
    if not port_ids:
        return False
    return ContainerPortLink.objects.filter(
        Q(source_port_id__in=port_ids) | Q(destination_port_id__in=port_ids)
    ).exists()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def equipment_collection_v07545(request, element_id):
    container = _container(request, element_id)
    if not _can_edit(request, container):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    data = request.data if isinstance(request.data, dict) else {}
    if str(data.get("equipment_type") or "") != ContainerEquipment.EquipmentType.OLT:
        return JsonResponse({"detail": "Este endpoint cria somente OLTs no padrão v0.75.45."}, status=400)

    name = str(data.get("name") or "").strip()
    if not name:
        return JsonResponse({"detail": "Informe o nome da OLT."}, status=400)
    orientation = str(data.get("chassis_orientation") or "horizontal").strip().lower()
    if orientation not in ORIENTATIONS:
        return JsonResponse({"detail": "Escolha placas de serviço verticais ou horizontais."}, status=400)
    try:
        slot_count = int(data.get("service_slot_count") or data.get("slot_count") or 0)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Quantidade de slots inválida."}, status=400)
    if slot_count < 1 or slot_count > 16:
        return JsonResponse({"detail": "Informe entre 1 e 16 slots de placas de serviço."}, status=400)

    chassis_model = str(data.get("chassis_model") or data.get("model") or "").strip()[:120]
    metadata = {
        CHASSIS_SCHEMA_KEY: {
            "orientation": orientation,
            "slot_count": slot_count,
            "chassis_model": chassis_model,
        },
        LEGACY_UPLINK_GROUPS_KEY: [],
        "rack_form_factor": "19-inch",
        "height_units": max(3, 4 if orientation == "vertical" else slot_count * 2),
    }
    try:
        equipment = ContainerEquipment.objects.create(
            company=container.company,
            container=container,
            name=name,
            description=str(data.get("description") or "").strip(),
            equipment_type=ContainerEquipment.EquipmentType.OLT,
            management_ip=data.get("management_ip") or None,
            provisioning_mode=str(data.get("provisioning_mode") or "manual"),
            tx_power_dbm=data.get("tx_power_dbm") or None,
            vendor=str(data.get("vendor") or "").strip(),
            model=chassis_model,
            serial_number=str(data.get("serial_number") or "").strip(),
            card_count=slot_count,
            pons_per_card=0,
            dio_port_capacity=0,
            enabled=bool(data.get("enabled", True)),
            metadata=metadata,
        )
    except IntegrityError:
        return JsonResponse({"detail": "Já existe um equipamento com este nome no Rack."}, status=409)
    return JsonResponse({"equipment": _hardware_payload(equipment)}, status=201)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def olt_chassis_v07545(request, element_id, equipment_id):
    container = _container(request, element_id)
    equipment = _olt(container, equipment_id)
    if request.method == "GET":
        return JsonResponse(_hardware_payload(equipment))
    if not _can_edit(request, container):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)

    data = request.data if isinstance(request.data, dict) else {}
    action = str(data.get("action") or "").strip().lower()
    schema = _schema(equipment)

    if action == "install_card":
        try:
            slot = int(data.get("slot") or 0)
            pon_count = int(data.get("pon_count") or 0)
        except (TypeError, ValueError):
            return JsonResponse({"detail": "Slot ou quantidade de portas inválida."}, status=400)
        if slot < 1 or slot > schema["slot_count"]:
            return JsonResponse({"detail": "Slot fora do chassi configurado."}, status=400)
        if pon_count < 1 or pon_count > 32:
            return JsonResponse({"detail": "Informe entre 1 e 32 portas PON na placa."}, status=400)
        technology = str(data.get("technology") or "gpon").strip().lower()
        if technology not in TECHNOLOGIES:
            return JsonResponse({"detail": "Tecnologia da placa inválida."}, status=400)
        name = str(data.get("name") or f"Placa {slot}").strip()[:100]
        model = str(data.get("model") or "").strip()[:120]

        card = equipment.cards.filter(slot=slot).first()
        if card and card.ports.count() != pon_count and _linked_card(card):
            return JsonResponse({"detail": "Desligue as portas desta placa antes de alterar a quantidade de PONs."}, status=409)
        with transaction.atomic():
            if card is None:
                card = ContainerEquipmentCard.objects.create(
                    equipment=equipment,
                    slot=slot,
                    name=name,
                    model=model,
                    pon_count=pon_count,
                )
                _create_card_ports(equipment, card, pon_count)
            else:
                if card.ports.count() != pon_count:
                    card.ports.all().delete()
                    _create_card_ports(equipment, card, pon_count)
                card.name = name
                card.model = model
                card.pon_count = pon_count
                card.enabled = True
                card.save(update_fields=["name", "model", "pon_count", "enabled"])
            _save_profile(equipment, card, model=model, technology=technology)
        return JsonResponse(_hardware_payload(equipment))

    if action == "remove_card":
        try:
            slot = int(data.get("slot") or 0)
        except (TypeError, ValueError):
            return JsonResponse({"detail": "Slot inválido."}, status=400)
        card = get_object_or_404(ContainerEquipmentCard.objects, equipment=equipment, slot=slot)
        if _linked_card(card):
            return JsonResponse({"detail": "Desligue todas as portas da placa antes de removê-la."}, status=409)
        with transaction.atomic():
            metadata = dict(equipment.metadata or {})
            profiles = _profiles(equipment)
            profiles.pop(str(card.id), None)
            metadata[CARD_PROFILE_KEY] = profiles
            metadata.pop(LEGACY_CARD_PROFILE_KEY, None)
            equipment.metadata = metadata
            equipment.save(update_fields=["metadata", "updated_at"])
            card.delete()
        return JsonResponse(_hardware_payload(equipment))

    return JsonResponse({"detail": "Ação inválida."}, status=400)
