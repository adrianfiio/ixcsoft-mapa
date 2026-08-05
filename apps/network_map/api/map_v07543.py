from __future__ import annotations

from django.db import transaction
from django.db.models import Max, Q
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


VERSION = "0.75.43"
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


def _link_for_port(port):
    return (
        ContainerPortLink.objects
        .filter(Q(source_port=port) | Q(destination_port=port))
        .order_by("id")
        .first()
    )


def _card_profile(equipment, card):
    metadata = dict(equipment.metadata or {})
    profiles = metadata.get(CARD_PROFILE_KEY) or {}
    profile = dict(profiles.get(str(card.id)) or {})
    technology = str(profile.get("technology") or "gpon").lower()
    if technology not in TECHNOLOGIES:
        technology = "gpon"
    model = str(profile.get("model") or "").strip()
    return {
        "id": card.id,
        "slot": card.slot,
        "name": card.name,
        "pon_count": card.pon_count,
        "technology": technology,
        "model": model,
    }


def _uplink_payload(port):
    link = _link_for_port(port)
    return {
        "id": port.id,
        "number": port.port_number or port.number,
        "label": port.label,
        "port_type": port.port_type,
        "port_type_label": port.get_port_type_display(),
        "link_id": link.id if link else None,
        "linked": bool(link),
    }


def _hardware_payload(equipment):
    cards = [
        _card_profile(equipment, card)
        for card in ContainerEquipmentCard.objects.filter(equipment=equipment).order_by("slot", "id")
    ]
    uplinks = [
        _uplink_payload(port)
        for port in ContainerEquipmentPort.objects.filter(
            equipment=equipment,
            card__isnull=True,
            port_type__in=list(UPLINK_TYPES.values()),
        ).order_by("port_number", "number", "id")
    ]
    return {
        "version": VERSION,
        "equipment": {
            "id": equipment.id,
            "name": equipment.name,
        },
        "cards": cards,
        "uplinks": uplinks,
        "uplink_types": [
            {"value": value, "label": UPLINK_LABELS[key]}
            for key, value in UPLINK_TYPES.items()
        ],
        "technologies": [
            {"value": "gpon", "label": "GPON"},
            {"value": "xgpon", "label": "XG-PON"},
            {"value": "xgspon", "label": "XGS-PON"},
        ],
    }


def _can_edit(request, container):
    return can_edit_company(request.user, container.company_id)


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def olt_hardware_v07543(request, element_id, equipment_id):
    container = _container(request, element_id)
    equipment = _olt(container, equipment_id)

    if request.method == "GET":
        return JsonResponse(_hardware_payload(equipment))

    if not _can_edit(request, container):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)

    data = request.data if isinstance(request.data, dict) else {}
    action = str(data.get("action") or "").strip().lower()

    if request.method == "POST" and action == "save_card":
        card = get_object_or_404(
            ContainerEquipmentCard.objects,
            pk=data.get("card_id"),
            equipment=equipment,
        )
        technology = str(data.get("technology") or "gpon").strip().lower()
        if technology not in TECHNOLOGIES:
            return JsonResponse({"detail": "Tecnologia da placa inválida."}, status=400)
        model = str(data.get("model") or "").strip()[:100]
        name = str(data.get("name") or "").strip()[:100]
        with transaction.atomic():
            metadata = dict(equipment.metadata or {})
            profiles = dict(metadata.get(CARD_PROFILE_KEY) or {})
            profiles[str(card.id)] = {
                "technology": technology,
                "model": model,
            }
            metadata[CARD_PROFILE_KEY] = profiles
            equipment.metadata = metadata
            equipment.save(update_fields=["metadata", "updated_at"])
            if name:
                card.name = name
                card.save(update_fields=["name"])
        return JsonResponse(_hardware_payload(equipment))

    if request.method == "POST" and action == "save_uplink":
        port_type = str(data.get("port_type") or "").strip()
        if port_type not in UPLINK_TYPES.values():
            return JsonResponse({"detail": "Escolha RJ45 1G, SFP 1G ou SFP+ 10G."}, status=400)
        label = str(data.get("label") or "").strip()[:100]
        port_id = data.get("port_id")
        with transaction.atomic():
            if port_id:
                port = get_object_or_404(
                    ContainerEquipmentPort.objects,
                    pk=port_id,
                    equipment=equipment,
                    card__isnull=True,
                )
                link = _link_for_port(port)
                if link and port.port_type != port_type:
                    return JsonResponse(
                        {"detail": "Desligue o uplink antes de alterar o tipo físico da porta."},
                        status=409,
                    )
                port.port_type = port_type
                port.label = label or UPLINK_LABELS.get(port_type, port.get_port_type_display())
                port.save(update_fields=["port_type", "label"])
            else:
                max_number = equipment.ports.aggregate(value=Max("number"))["value"] or 0
                uplink_count = equipment.ports.filter(
                    card__isnull=True,
                    port_type__in=list(UPLINK_TYPES.values()),
                ).count()
                if uplink_count >= 16:
                    return JsonResponse({"detail": "A OLT já atingiu o limite de 16 uplinks."}, status=400)
                port_number = uplink_count + 1
                port = ContainerEquipmentPort.objects.create(
                    equipment=equipment,
                    port_type=port_type,
                    number=max_number + 1,
                    port_number=port_number,
                    label=label or f"Uplink {port_number} · {UPLINK_LABELS.get(port_type, port_type)}",
                )
        return JsonResponse(_hardware_payload(equipment), status=201 if not port_id else 200)

    if request.method == "DELETE" or action == "delete_uplink":
        port = get_object_or_404(
            ContainerEquipmentPort.objects,
            pk=data.get("port_id"),
            equipment=equipment,
            card__isnull=True,
            port_type__in=list(UPLINK_TYPES.values()),
        )
        if _link_for_port(port):
            return JsonResponse({"detail": "Desligue o uplink antes de excluir a porta."}, status=409)
        port.delete()
        return JsonResponse(_hardware_payload(equipment))

    return JsonResponse({"detail": "Ação inválida."}, status=400)
