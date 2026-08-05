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


VERSION = "0.75.44"
HARDWARE_SCHEMA_KEY = "v07544_hardware_schema"
UPLINK_GROUPS_KEY = "v07544_uplink_groups"
CARD_PROFILE_KEY = "v07543_card_profiles"
UPLINK_TYPES = {
    "rj45_1g": ContainerEquipmentPort.PortType.RJ45_1G,
    "sfp_1g": ContainerEquipmentPort.PortType.SFP_1G,
    "sfp_plus_10g": ContainerEquipmentPort.PortType.SFP_PLUS_10G,
}
UPLINK_LABELS = {
    "rj45_1g": "RJ45 1G",
    "sfp_1g": "SFP 1G",
    "sfp_plus_10g": "SFP+ 10G",
}
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


def _card_payload(equipment, card):
    profiles = dict((equipment.metadata or {}).get(CARD_PROFILE_KEY) or {})
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
    }


def _clean_groups(equipment):
    metadata = dict(equipment.metadata or {})
    rows = metadata.get(UPLINK_GROUPS_KEY) or []
    if not isinstance(rows, list):
        return []
    existing = {
        port.id: port
        for port in equipment.ports.filter(card__isnull=True).order_by("number", "id")
    }
    groups = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        port_type = str(row.get("port_type") or "")
        if port_type not in UPLINK_TYPES:
            continue
        port_ids = []
        ports = []
        for raw_id in row.get("port_ids") or []:
            try:
                port_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            port = existing.get(port_id)
            if not port or port.port_type != UPLINK_TYPES[port_type]:
                continue
            port_ids.append(port.id)
            ports.append(_port_payload(port))
        groups.append({
            "id": str(row.get("id") or f"uplink-{index}"),
            "name": str(row.get("name") or f"Uplink {index}")[:100],
            "port_type": port_type,
            "port_type_label": UPLINK_LABELS[port_type],
            "port_ids": port_ids,
            "ports": ports,
        })
    return groups


def _hardware_payload(equipment):
    cards = [
        _card_payload(equipment, card)
        for card in equipment.cards.all().order_by("slot", "id")
    ]
    groups = _clean_groups(equipment)
    explicit_ids = {port_id for group in groups for port_id in group["port_ids"]}
    hidden_legacy = equipment.ports.filter(card__isnull=True).exclude(id__in=explicit_ids).count()
    return {
        "version": VERSION,
        "equipment": {
            "id": equipment.id,
            "name": equipment.name,
            "vendor": equipment.vendor,
            "model": equipment.model,
            "management_ip": equipment.management_ip,
            "slot_count": len(cards),
            "pons_per_slot": max((len(card["ports"]) for card in cards), default=0),
        },
        "cards": cards,
        "uplink_groups": groups,
        "hidden_legacy_ports": hidden_legacy,
        "uplink_types": [
            {"value": key, "label": label}
            for key, label in UPLINK_LABELS.items()
        ],
    }


def _validate_uplink_groups(raw_groups):
    if raw_groups in (None, ""):
        return []
    if not isinstance(raw_groups, list):
        raise ValueError("A configuração de uplinks deve ser uma lista.")
    if len(raw_groups) > 16:
        raise ValueError("A OLT aceita no máximo 16 grupos de uplink.")
    groups = []
    total_ports = 0
    for index, row in enumerate(raw_groups, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Configuração do uplink {index} inválida.")
        port_type = str(row.get("port_type") or "").strip()
        if port_type not in UPLINK_TYPES:
            raise ValueError(f"Escolha o tipo físico do uplink {index}.")
        try:
            port_count = int(row.get("port_count") or 0)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Quantidade de portas do uplink {index} inválida.") from error
        if port_count < 1 or port_count > 16:
            raise ValueError("Cada grupo de uplink deve possuir entre 1 e 16 portas.")
        total_ports += port_count
        if total_ports > 64:
            raise ValueError("A OLT aceita no máximo 64 portas de uplink explícitas.")
        groups.append({
            "id": f"uplink-{index}",
            "name": str(row.get("name") or f"Uplink {index}").strip()[:100],
            "port_type": port_type,
            "port_count": port_count,
        })
    return groups


def _create_uplink_ports(equipment, groups, start_number):
    metadata_groups = []
    next_number = start_number
    for group_index, group in enumerate(groups, start=1):
        port_ids = []
        for port_index in range(1, group["port_count"] + 1):
            next_number += 1
            port = ContainerEquipmentPort.objects.create(
                equipment=equipment,
                port_type=UPLINK_TYPES[group["port_type"]],
                number=next_number,
                port_number=port_index,
                label=f"{group['name']} / Porta {port_index}",
            )
            port_ids.append(port.id)
        metadata_groups.append({
            "id": group["id"],
            "name": group["name"],
            "port_type": group["port_type"],
            "port_ids": port_ids,
        })
    return metadata_groups


def _create_service_cards(equipment, slot_count, pons_per_slot):
    global_number = 0
    for slot in range(1, slot_count + 1):
        card = ContainerEquipmentCard.objects.create(
            equipment=equipment,
            slot=slot,
            name=f"Placa {slot}",
            pon_count=pons_per_slot,
        )
        ports = []
        for pon in range(1, pons_per_slot + 1):
            global_number += 1
            ports.append(ContainerEquipmentPort(
                equipment=equipment,
                card=card,
                port_type=ContainerEquipmentPort.PortType.PON,
                number=global_number,
                card_number=slot,
                port_number=pon,
                label=f"S{slot} / PON {pon}",
            ))
        ContainerEquipmentPort.objects.bulk_create(ports)
    return global_number


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def equipment_collection_v07544(request, element_id):
    container = _container(request, element_id)
    if not _can_edit(request, container):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    data = request.data if isinstance(request.data, dict) else {}
    if str(data.get("equipment_type") or "") != ContainerEquipment.EquipmentType.OLT:
        return JsonResponse({"detail": "Este endpoint cria somente OLTs no padrão v0.75.44."}, status=400)
    name = str(data.get("name") or "").strip()
    if not name:
        return JsonResponse({"detail": "Informe o nome da OLT."}, status=400)
    try:
        slot_count = int(data.get("card_count") or data.get("slot_count") or 0)
        pons_per_slot = int(data.get("pons_per_card") or data.get("pons_per_slot") or 0)
        groups = _validate_uplink_groups(data.get("uplink_groups") or [])
    except (TypeError, ValueError) as error:
        return JsonResponse({"detail": str(error)}, status=400)
    if slot_count < 1 or slot_count > 16:
        return JsonResponse({"detail": "Informe entre 1 e 16 placas de serviço."}, status=400)
    if pons_per_slot < 1 or pons_per_slot > 32:
        return JsonResponse({"detail": "Informe entre 1 e 32 portas PON por placa."}, status=400)
    metadata = {
        HARDWARE_SCHEMA_KEY: 1,
        UPLINK_GROUPS_KEY: [],
        "height_units": max(2, slot_count + (1 if groups else 0)),
        "rack_form_factor": "19-inch",
    }
    try:
        with transaction.atomic():
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
                model=str(data.get("model") or "").strip(),
                serial_number=str(data.get("serial_number") or "").strip(),
                card_count=slot_count,
                pons_per_card=pons_per_slot,
                dio_port_capacity=0,
                enabled=bool(data.get("enabled", True)),
                metadata=metadata,
            )
            last_number = _create_service_cards(equipment, slot_count, pons_per_slot)
            metadata[UPLINK_GROUPS_KEY] = _create_uplink_ports(equipment, groups, last_number)
            equipment.metadata = metadata
            equipment.save(update_fields=["metadata", "updated_at"])
    except IntegrityError:
        return JsonResponse({"detail": "Já existe um equipamento com este nome no Rack."}, status=409)
    return JsonResponse({"equipment": _hardware_payload(equipment)}, status=201)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def olt_hardware_v07544(request, element_id, equipment_id):
    container = _container(request, element_id)
    equipment = _olt(container, equipment_id)
    if request.method == "GET":
        return JsonResponse(_hardware_payload(equipment))
    if not _can_edit(request, container):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    data = request.data if isinstance(request.data, dict) else {}
    action = str(data.get("action") or "").strip().lower()

    if action == "save_card":
        card = get_object_or_404(ContainerEquipmentCard.objects, pk=data.get("card_id"), equipment=equipment)
        technology = str(data.get("technology") or "gpon").strip().lower()
        if technology not in TECHNOLOGIES:
            return JsonResponse({"detail": "Tecnologia da placa inválida."}, status=400)
        model = str(data.get("model") or "").strip()[:100]
        name = str(data.get("name") or "").strip()[:100]
        with transaction.atomic():
            metadata = dict(equipment.metadata or {})
            profiles = dict(metadata.get(CARD_PROFILE_KEY) or {})
            profiles[str(card.id)] = {"technology": technology, "model": model}
            metadata[CARD_PROFILE_KEY] = profiles
            equipment.metadata = metadata
            equipment.save(update_fields=["metadata", "updated_at"])
            if name:
                card.name = name
                card.save(update_fields=["name"])
        return JsonResponse(_hardware_payload(equipment))

    if action == "replace_uplink_groups":
        try:
            groups = _validate_uplink_groups(data.get("uplink_groups") or [])
        except ValueError as error:
            return JsonResponse({"detail": str(error)}, status=400)
        existing_groups = _clean_groups(equipment)
        explicit_ids = [port_id for group in existing_groups for port_id in group["port_ids"]]
        linked = ContainerPortLink.objects.filter(
            Q(source_port_id__in=explicit_ids) | Q(destination_port_id__in=explicit_ids)
        ).exists()
        if linked:
            return JsonResponse({"detail": "Desligue os uplinks atuais antes de reconfigurar os grupos."}, status=409)
        with transaction.atomic():
            equipment.ports.filter(id__in=explicit_ids).delete()
            max_number = equipment.ports.order_by("-number").values_list("number", flat=True).first() or 0
            metadata = dict(equipment.metadata or {})
            metadata[HARDWARE_SCHEMA_KEY] = 1
            metadata[UPLINK_GROUPS_KEY] = _create_uplink_ports(equipment, groups, max_number)
            equipment.metadata = metadata
            equipment.save(update_fields=["metadata", "updated_at"])
        return JsonResponse(_hardware_payload(equipment))

    return JsonResponse({"detail": "Ação inválida."}, status=400)
