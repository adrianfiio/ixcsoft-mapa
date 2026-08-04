from __future__ import annotations

import math
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company, scope_company_queryset
from apps.network_map.kmz_import_models import CableElementPassage
from apps.network_map.models import (
    ContainerEquipment,
    ContainerEquipmentPort,
    FiberCable,
    NetworkElement,
    NetworkRoute,
)


def _distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = a
    lon2, lat2 = b
    dx = (lon2 - lon1) * 111320 * math.cos(math.radians((lat1 + lat2) / 2))
    dy = (lat2 - lat1) * 110540
    return math.hypot(dx, dy)


def _project_distance_m(point, a, b) -> float:
    px, py = point
    ax, ay = a
    bx, by = b
    vx, vy = bx - ax, by - ay
    denominator = vx * vx + vy * vy
    ratio = 0.0 if denominator == 0 else max(
        0.0,
        min(1.0, ((px - ax) * vx + (py - ay) * vy) / denominator),
    )
    projected = (ax + ratio * vx, ay + ratio * vy)
    return _distance_m(point, projected)


def _cable_distance_m(element: NetworkElement, cable: FiberCable) -> float:
    if not element.point or not cable.geometry:
        return float("inf")
    point = (element.point.x, element.point.y)
    values: list[float] = []
    for line in cable.geometry:
        coords = [tuple(value) for value in line.coords]
        values.extend(
            _project_distance_m(point, coords[index], coords[index + 1])
            for index in range(len(coords) - 1)
        )
    return min(values) if values else float("inf")


def _metadata(element: NetworkElement) -> dict[str, Any]:
    return dict(element.metadata or {})


def _excluded_ids(element: NetworkElement) -> set[int]:
    raw = _metadata(element).get("fusion_excluded_cable_ids", [])
    result: set[int] = set()
    for value in raw if isinstance(raw, list) else []:
        try:
            result.add(int(value))
        except (TypeError, ValueError):
            continue
    return result


def _save_excluded_ids(element: NetworkElement, values: set[int]) -> None:
    metadata = _metadata(element)
    metadata["fusion_excluded_cable_ids"] = sorted(values)
    element.metadata = metadata
    element.save(update_fields=["metadata", "updated_at"])


def _element_for_edit(request, element_id: int) -> NetworkElement:
    element = get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type__in=[
            NetworkElement.ElementType.CTO,
            NetworkElement.ElementType.SPLICE_BOX,
        ],
    )
    return element


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fusion_cable_state(request, element_id):
    element = _element_for_edit(request, element_id)
    try:
        radius = max(1.0, min(float(request.GET.get("radius_m") or 45), 500.0))
    except (TypeError, ValueError):
        radius = 45.0
    excluded = _excluded_ids(element)
    metadata = _metadata(element)
    element_route_id = metadata.get("route_id")
    try:
        element_route_id = element.cto.route_id or element_route_id
    except Exception:
        pass
    try:
        element_route_id = int(element_route_id) if element_route_id else None
    except (TypeError, ValueError):
        element_route_id = None
    passage_ids = set(element.cable_passages.values_list("cable_id", flat=True))
    endpoint_ids = set(
        FiberCable.objects.filter(Q(origin=element) | Q(destination=element)).values_list("id", flat=True)
    )
    queryset = FiberCable.objects.filter(
        company=element.company,
        project=element.project,
        geometry__isnull=False,
    ).select_related("route", "origin", "destination")
    nearby = []
    for cable in queryset.iterator(chunk_size=250):
        distance = _cable_distance_m(element, cable)
        related = cable.id in passage_ids or cable.id in endpoint_ids
        if not related and element_route_id and cable.route_id and cable.route_id != element_route_id:
            continue
        if distance > radius and not related:
            continue
        nearby.append({
            "id": cable.id,
            "name": cable.name,
            "code": cable.code,
            "distance_m": round(distance, 2) if math.isfinite(distance) else None,
            "route_id": cable.route_id,
            "route": cable.route.name if cable.route else "",
            "endpoint": cable.id in endpoint_ids,
            "passage": cable.id in passage_ids,
            "excluded": cable.id in excluded,
        })
    nearby.sort(key=lambda item: (
        item["excluded"],
        item["distance_m"] is None,
        item["distance_m"] if item["distance_m"] is not None else 10**9,
        item["name"],
    ))
    return JsonResponse({
        "element": {"id": element.id, "name": element.name},
        "radius_m": radius,
        "route_id": element_route_id,
        "excluded_cable_ids": sorted(excluded),
        "cables": nearby,
    })


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def fusion_cable_membership(request, element_id, cable_id):
    element = _element_for_edit(request, element_id)
    if not can_edit_company(request.user, element.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    cable = get_object_or_404(
        FiberCable.objects.select_related("route"),
        pk=cable_id,
        company=element.company,
        project=element.project,
    )
    excluded = _excluded_ids(element)
    is_endpoint = cable.origin_id == element.id or cable.destination_id == element.id
    if request.method == "DELETE":
        if is_endpoint:
            return JsonResponse(
                {
                    "detail": (
                        "Este cabo termina fisicamente nesta caixa. Para removê-lo, "
                        "edite ou corte a topologia do cabo; ele não é apenas uma associação de proximidade."
                    )
                },
                status=409,
            )
        CableElementPassage.objects.filter(cable=cable, element=element).delete()
        excluded.add(cable.id)
        _save_excluded_ids(element, excluded)
        return JsonResponse({"success": True, "excluded": True, "cable_id": cable.id})

    action = str(request.data.get("action") or "pass").strip().lower()
    excluded.discard(cable.id)
    _save_excluded_ids(element, excluded)
    if not is_endpoint and action == "pass":
        distance = _cable_distance_m(element, cable)
        try:
            max_distance = max(1.0, min(float(request.data.get("max_distance_m") or 80), 500.0))
        except (TypeError, ValueError):
            max_distance = 80.0
        if distance > max_distance:
            return JsonResponse(
                {"detail": f"O cabo está a {distance:.1f} m da caixa; limite configurado: {max_distance:.1f} m."},
                status=409,
            )
        CableElementPassage.objects.update_or_create(
            cable=cable,
            element=element,
            action=CableElementPassage.Action.PASS,
            defaults={
                "sequence": 1,
                "distance_m": distance,
                "metadata": {"manual_membership": True, "route_id": cable.route_id},
            },
        )
    return JsonResponse({"success": True, "excluded": False, "cable_id": cable.id})


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def container_layout_v3(request, element_id):
    # MAP_V07528_CTO_TORRE_ENGINE: CTO liberada -- sem isso, a posição
    # dos nós arrastados no Canvas da CTO nunca seria salva.
    element = get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type__in=[
            NetworkElement.ElementType.RACK,
            NetworkElement.ElementType.TOWER,
            NetworkElement.ElementType.CTO,
        ],
    )
    metadata = _metadata(element)
    if request.method == "GET":
        return JsonResponse({"layout": metadata.get("container_layout_v3", {})})
    if not can_edit_company(request.user, element.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    incoming = request.data.get("layout")
    if not isinstance(incoming, dict):
        return JsonResponse({"detail": "Layout inválido."}, status=400)
    metadata["container_layout_v3"] = incoming
    element.metadata = metadata
    element.save(update_fields=["metadata", "updated_at"])
    return JsonResponse({"layout": incoming})


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def container_equipment_details_v3(request, element_id, equipment_id):
    visible_containers = scope_company_queryset(NetworkElement.objects, request.user)
    equipment = get_object_or_404(
        ContainerEquipment.objects.select_related("container").prefetch_related("ports"),
        pk=equipment_id,
        container_id=element_id,
        container__in=visible_containers,
    )
    if request.method == "PATCH":
        if not can_edit_company(request.user, equipment.company_id):
            return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
        for field in ("name", "description", "vendor", "model", "serial_number"):
            if field in request.data:
                setattr(equipment, field, str(request.data.get(field) or "").strip())
        management_ip = request.data.get("management_ip", "__missing__")
        if management_ip != "__missing__":
            equipment.management_ip = str(management_ip).strip() or None
        metadata = dict(equipment.metadata or {})
        for key in ("photo_url", "notes"):
            if key in request.data:
                metadata[key] = str(request.data.get(key) or "").strip()
        if isinstance(request.data.get("port_modules"), dict):
            metadata["port_modules"] = request.data["port_modules"]
        equipment.metadata = metadata
        equipment.save()
    metadata = dict(equipment.metadata or {})
    return JsonResponse({
        "equipment": {
            "id": equipment.id,
            "name": equipment.name,
            "description": equipment.description,
            "type": equipment.equipment_type,
            "type_label": equipment.get_equipment_type_display(),
            "vendor": equipment.vendor,
            "model": equipment.model,
            "serial_number": equipment.serial_number,
            "management_ip": equipment.management_ip,
            "photo_url": metadata.get("photo_url", ""),
            "notes": metadata.get("notes", ""),
            "port_modules": metadata.get("port_modules", {}),
            "ports": [
                {
                    "id": port.id,
                    "label": port.label,
                    "type": port.port_type,
                    "type_label": port.get_port_type_display(),
                }
                for port in equipment.ports.all()
            ],
        }
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_passive_endpoint_v3(request, element_id):
    # MAP_V07528_CTO_TORRE_ENGINE: CTO liberada, mesma cópia geral do
    # Canvas do Rack/Torre pedida pelo usuário.
    container = get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type__in=[
            NetworkElement.ElementType.RACK,
            NetworkElement.ElementType.TOWER,
            NetworkElement.ElementType.CTO,
        ],
    )
    if not can_edit_company(request.user, container.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    subtype = str(request.data.get("subtype") or "pto").strip().lower()
    if subtype not in {"pto", "direct_connector"}:
        return JsonResponse({"detail": "Tipo de terminação inválido."}, status=400)
    connector_type = str(request.data.get("connector_type") or "sc_apc").strip().lower()
    allowed_connectors = dict(ContainerEquipment.ConnectorType.choices)
    if connector_type not in allowed_connectors:
        return JsonResponse({"detail": "Tipo de conector inválido."}, status=400)
    default_name = "PTO" if subtype == "pto" else "Conector direto"
    requested_name = str(request.data.get("name") or default_name).strip() or default_name
    name = requested_name
    suffix = 2
    while ContainerEquipment.objects.filter(container=container, name=name).exists():
        name = f"{requested_name} {suffix}"
        suffix += 1
    with transaction.atomic():
        equipment = ContainerEquipment.objects.create(
            company=container.company,
            container=container,
            name=name,
            description=(
                "Ponto de terminação óptica criado no mapa."
                if subtype == "pto"
                else "Conector direto do cabo DROP criado no mapa."
            ),
            equipment_type=ContainerEquipment.EquipmentType.OTHER,
            connector_type=connector_type,
            metadata={"subtype": subtype, "passive_endpoint": True},
        )
        port = ContainerEquipmentPort.objects.create(
            equipment=equipment,
            port_type=ContainerEquipmentPort.PortType.DIO,
            number=1,
            port_number=1,
            label=f"{default_name} 1 · {allowed_connectors[connector_type]}",
        )
    return JsonResponse({
        "equipment": {"id": equipment.id, "name": equipment.name, "subtype": subtype},
        "port": {"id": port.id, "label": port.label},
    }, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assign_asset_route_v3(request):
    element_id = request.data.get("element_id")
    cable_id = request.data.get("cable_id")
    if bool(element_id) == bool(cable_id):
        return JsonResponse({"detail": "Informe um elemento ou um cabo."}, status=400)

    route_id = request.data.get("route_id")
    if not route_id:
        if cable_id:
            cable = get_object_or_404(
                scope_company_queryset(FiberCable.objects, request.user),
                pk=cable_id,
            )
            if not can_edit_company(request.user, cable.company_id):
                return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
            cable.route = None
            cable.save(update_fields=["route", "updated_at"])
            return JsonResponse({"success": True, "asset": "cable", "route": ""})
        element = get_object_or_404(
            scope_company_queryset(NetworkElement.objects, request.user),
            pk=element_id,
        )
        if not can_edit_company(request.user, element.company_id):
            return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
        try:
            cto = element.cto
        except Exception:
            cto = None
        if cto is not None:
            cto.route = None
            cto.save(update_fields=["route", "updated_at"])
        metadata = _metadata(element)
        metadata.pop("route_id", None)
        metadata.pop("route_name", None)
        element.metadata = metadata
        element.save(update_fields=["metadata", "updated_at"])
        return JsonResponse({"success": True, "asset": "element", "route": ""})

    route = get_object_or_404(
        scope_company_queryset(NetworkRoute.objects, request.user),
        pk=route_id,
    )
    if cable_id:
        cable = get_object_or_404(FiberCable, pk=cable_id, project=route.project, company=route.company)
        if not can_edit_company(request.user, cable.company_id):
            return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
        cable.route = route
        cable.save(update_fields=["route", "updated_at"])
        return JsonResponse({"success": True, "asset": "cable", "route": route.name})
    element = get_object_or_404(NetworkElement, pk=element_id, project=route.project, company=route.company)
    if not can_edit_company(request.user, element.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    try:
        cto = element.cto
    except Exception:
        cto = None
    if cto is not None:
        cto.route = route
        cto.save(update_fields=["route", "updated_at"])
    metadata = _metadata(element)
    metadata["route_id"] = route.id
    metadata["route_name"] = route.name
    element.metadata = metadata
    element.save(update_fields=["metadata", "updated_at"])
    return JsonResponse({"success": True, "asset": "element", "route": route.name})
