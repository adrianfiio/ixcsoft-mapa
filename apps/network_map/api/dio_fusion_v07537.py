from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction
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
    FiberCable,
    FiberSplice,
    FiberStrand,
    NetworkElement,
    SpliceTraySplitter,
    SpliceTraySplitterPort,
)


FUSION_CABLE_IDS_KEY = "dio_fusion_cable_ids_v07537"
MAX_AUTO_FUSIONS = 192


def _container_for_user(request, element_id: int) -> NetworkElement:
    return get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type__in=[
            NetworkElement.ElementType.RACK,
            NetworkElement.ElementType.TOWER,
        ],
    )


def _dio_for_container(container: NetworkElement, equipment_id: int) -> ContainerEquipment:
    return get_object_or_404(
        ContainerEquipment.objects.prefetch_related("ports"),
        pk=equipment_id,
        container=container,
        equipment_type=ContainerEquipment.EquipmentType.DIO,
    )


def _candidate_cables(container: NetworkElement):
    return (
        FiberCable.objects.filter(
            Q(origin=container)
            | Q(destination=container)
            | Q(container_port_links__container=container)
        )
        .distinct()
        .prefetch_related("fibers__color", "fibers__tube__color")
        .order_by("name", "id")
    )


def _linked_cable_ids(dio: ContainerEquipment, container: NetworkElement) -> set[int]:
    metadata = dict(dio.metadata or {})
    result: set[int] = set()
    values = metadata.get(FUSION_CABLE_IDS_KEY, [])
    for value in values if isinstance(values, list) else []:
        try:
            result.add(int(value))
        except (TypeError, ValueError):
            continue
    result.update(
        ContainerPortLink.objects.filter(
            container=container,
            destination_port__equipment=dio,
            cable_id__isnull=False,
        ).values_list("cable_id", flat=True)
    )
    return result


def _save_linked_cable_ids(dio: ContainerEquipment, values: set[int]) -> None:
    metadata = dict(dio.metadata or {})
    metadata[FUSION_CABLE_IDS_KEY] = sorted(values)
    dio.metadata = metadata
    dio.save(update_fields=["metadata", "updated_at"])


def _fiber_is_used(fiber: FiberStrand, *, exclude_link_id: int | None = None) -> bool:
    links = ContainerPortLink.objects.filter(cable_fiber=fiber)
    if exclude_link_id is not None:
        links = links.exclude(pk=exclude_link_id)
    return (
        links.exists()
        or FiberSplice.objects.filter(
            Q(input_fiber=fiber) | Q(output_fiber=fiber)
        ).exists()
        or SpliceTraySplitter.objects.filter(input_fiber=fiber).exists()
        or SpliceTraySplitterPort.objects.filter(output_fiber=fiber).exists()
    )


def _sync_fiber_status(fiber: FiberStrand) -> None:
    fiber.status = (
        FiberStrand.Status.USED if _fiber_is_used(fiber) else FiberStrand.Status.FREE
    )
    fiber.save(update_fields=["status", "updated_at"])


def _fusion_links(container: NetworkElement, dio: ContainerEquipment):
    return (
        ContainerPortLink.objects.filter(
            container=container,
            destination_port__equipment=dio,
            cable_fiber__isnull=False,
        )
        .select_related(
            "destination_port",
            "cable",
            "cable_fiber__color",
            "cable_fiber__tube__color",
        )
        .order_by("destination_port__number", "id")
    )


def _payload(container: NetworkElement, dio: ContainerEquipment) -> dict:
    candidates = list(_candidate_cables(container))
    candidate_by_id = {item.id: item for item in candidates}
    linked_ids = _linked_cable_ids(dio, container)
    links = list(_fusion_links(container, dio))
    linked_ids.update(link.cable_id for link in links if link.cable_id)
    link_by_port = {link.destination_port_id: link for link in links}
    link_by_fiber = {link.cable_fiber_id: link for link in links}

    def fiber_payload(fiber: FiberStrand) -> dict:
        link = link_by_fiber.get(fiber.id)
        tube = fiber.tube
        tube_color = getattr(tube, "color", None) if tube else None
        return {
            "id": fiber.id,
            "number": fiber.number,
            "position_in_tube": fiber.position_in_tube,
            "color_name": fiber.color.name,
            "color_hex": fiber.color.hex_color,
            "status": fiber.status,
            "tube_id": fiber.tube_id,
            "tube_number": tube.number if tube else 1,
            "tube_color_name": tube_color.name if tube_color else "",
            "tube_color_hex": tube_color.hex_color if tube_color else "#64748b",
            "fusion": None
            if not link
            else {
                "id": link.id,
                "port_id": link.destination_port_id,
                "port_number": link.destination_port.number,
            },
        }

    def cable_payload(cable: FiberCable) -> dict:
        return {
            "id": cable.id,
            "name": cable.name,
            "code": cable.code,
            "fiber_count": cable.fiber_count,
            "fibers": [fiber_payload(fiber) for fiber in cable.fibers.all()],
        }

    linked = [
        cable_payload(candidate_by_id[cable_id])
        for cable_id in sorted(linked_ids)
        if cable_id in candidate_by_id
    ]
    available = [
        {
            "id": cable.id,
            "name": cable.name,
            "code": cable.code,
            "fiber_count": cable.fiber_count,
        }
        for cable in candidates
        if cable.id not in linked_ids
    ]
    ports = []
    for port in dio.ports.all().order_by("number"):
        fusion = link_by_port.get(port.id)
        front_link = (
            ContainerPortLink.objects.filter(
                container=container,
                destination_port=port,
                source_port__isnull=False,
            )
            .select_related("source_port__equipment")
            .first()
        )
        ports.append(
            {
                "id": port.id,
                "number": port.number,
                "label": port.label,
                "front": None
                if not front_link
                else {
                    "link_id": front_link.id,
                    "equipment": front_link.source_port.equipment.name,
                    "port": front_link.source_port.label,
                },
                "fusion": None
                if not fusion
                else {
                    "id": fusion.id,
                    "cable_id": fusion.cable_id,
                    "cable": fusion.cable.name if fusion.cable else "",
                    "fiber_id": fusion.cable_fiber_id,
                    "fiber_number": fusion.cable_fiber.number,
                    "color_name": fusion.cable_fiber.color.name,
                    "color_hex": fusion.cable_fiber.color.hex_color,
                },
            }
        )
    return {
        "success": True,
        "container": {
            "id": container.id,
            "name": container.name,
            "type": container.element_type,
        },
        "dio": {
            "id": dio.id,
            "name": dio.name,
            "capacity": dio.dio_port_capacity or len(ports),
            "connector_type": dio.connector_type,
        },
        "linked_cable_ids": sorted(linked_ids),
        "linked_cables": linked,
        "available_cables": available,
        "ports": ports,
        "summary": {
            "linked_cables": len(linked),
            "fusions": len(links),
            "free_ports": sum(1 for item in ports if not item["fusion"]),
        },
    }


def _require_edit(request, container: NetworkElement):
    if not can_edit_company(request.user, container.company_id):
        return JsonResponse(
            {"success": False, "detail": "Sem permissão para editar esta empresa."},
            status=403,
        )
    return None


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def dio_fusion_matrix_v07537(request, element_id, equipment_id):
    container = _container_for_user(request, element_id)
    dio = _dio_for_container(container, equipment_id)
    if request.method == "GET":
        return JsonResponse(_payload(container, dio))

    denied = _require_edit(request, container)
    if denied:
        return denied

    action = str(request.data.get("action") or "").strip().lower()
    linked_ids = _linked_cable_ids(dio, container)
    candidates = _candidate_cables(container)

    if action == "attach_cable":
        cable = get_object_or_404(candidates, pk=request.data.get("cable_id"))
        linked_ids.add(cable.id)
        _save_linked_cable_ids(dio, linked_ids)
        return JsonResponse(_payload(container, dio))

    if action == "detach_cable":
        cable = get_object_or_404(candidates, pk=request.data.get("cable_id"))
        active = _fusion_links(container, dio).filter(cable=cable).count()
        if active:
            return JsonResponse(
                {
                    "success": False,
                    "detail": f"O cabo possui {active} fusão(ões) neste DIO. Rompa as fusões antes de desvincular.",
                },
                status=409,
            )
        linked_ids.discard(cable.id)
        _save_linked_cable_ids(dio, linked_ids)
        return JsonResponse(_payload(container, dio))

    if action == "create_fusion":
        fiber = get_object_or_404(
            FiberStrand.objects.select_related("cable", "color"),
            pk=request.data.get("fiber_id"),
            cable__in=candidates,
        )
        if fiber.cable_id not in linked_ids:
            return JsonResponse(
                {"success": False, "detail": "Vincule o cabo ao DIO antes de criar a fusão."},
                status=409,
            )
        port = get_object_or_404(
            ContainerEquipmentPort,
            pk=request.data.get("port_id"),
            equipment=dio,
        )
        if _fusion_links(container, dio).filter(destination_port=port).exists():
            return JsonResponse(
                {"success": False, "detail": "Esta porta já possui uma fibra fusionada."},
                status=409,
            )
        if _fiber_is_used(fiber):
            return JsonResponse(
                {"success": False, "detail": "Esta fibra já está utilizada em outra ligação."},
                status=409,
            )
        try:
            with transaction.atomic():
                link = ContainerPortLink.objects.create(
                    container=container,
                    source_port=None,
                    destination_port=port,
                    cable=fiber.cable,
                    cable_fiber=fiber,
                    link_type=ContainerPortLink.LinkType.FIBER,
                    loss_db=Decimal("0.05"),
                    notes="Fusão criada pela matriz do DIO v0.75.37",
                )
                fiber.status = FiberStrand.Status.USED
                fiber.save(update_fields=["status", "updated_at"])
        except IntegrityError:
            return JsonResponse(
                {"success": False, "detail": "A porta ou a fibra já foi utilizada por outra operação."},
                status=409,
            )
        response = _payload(container, dio)
        response["created_link_id"] = link.id
        return JsonResponse(response, status=201)

    if action == "delete_fusion" or request.method == "DELETE":
        link = get_object_or_404(
            _fusion_links(container, dio),
            pk=request.data.get("link_id"),
        )
        fiber = link.cable_fiber
        link.delete()
        if fiber:
            _sync_fiber_status(fiber)
        return JsonResponse(_payload(container, dio))

    if action == "auto_fuse":
        cable = get_object_or_404(candidates, pk=request.data.get("cable_id"))
        if cable.id not in linked_ids:
            return JsonResponse(
                {"success": False, "detail": "Vincule o cabo ao DIO antes da auto fusão."},
                status=409,
            )
        try:
            start_port_id = int(request.data.get("start_port_id") or 0)
            requested_count = int(request.data.get("count") or MAX_AUTO_FUSIONS)
        except (TypeError, ValueError):
            return JsonResponse(
                {"success": False, "detail": "Porta inicial ou quantidade inválida."},
                status=400,
            )
        all_ports = list(dio.ports.all().order_by("number"))
        start_index = 0
        if start_port_id:
            for index, port in enumerate(all_ports):
                if port.id == start_port_id:
                    start_index = index
                    break
            else:
                return JsonResponse(
                    {"success": False, "detail": "A porta inicial não pertence a este DIO."},
                    status=400,
                )
        occupied_port_ids = set(
            _fusion_links(container, dio).values_list("destination_port_id", flat=True)
        )
        free_ports = [port for port in all_ports[start_index:] if port.id not in occupied_port_ids]
        free_fibers = [
            fiber
            for fiber in cable.fibers.select_related("color").order_by("number")
            if not _fiber_is_used(fiber)
        ]
        pairs = list(zip(free_fibers, free_ports))[: max(1, min(requested_count, MAX_AUTO_FUSIONS))]
        if not pairs:
            return JsonResponse(
                {"success": False, "detail": "Não há fibras e portas livres para auto fusão."},
                status=409,
            )
        created = []
        try:
            with transaction.atomic():
                for fiber, port in pairs:
                    link = ContainerPortLink.objects.create(
                        container=container,
                        source_port=None,
                        destination_port=port,
                        cable=cable,
                        cable_fiber=fiber,
                        link_type=ContainerPortLink.LinkType.FIBER,
                        loss_db=Decimal("0.05"),
                        notes="Auto fusão sequencial DIO v0.75.37",
                    )
                    fiber.status = FiberStrand.Status.USED
                    fiber.save(update_fields=["status", "updated_at"])
                    created.append(link.id)
        except IntegrityError:
            return JsonResponse(
                {"success": False, "detail": "A matriz mudou durante a auto fusão. Recarregue e tente novamente."},
                status=409,
            )
        response = _payload(container, dio)
        response["auto_fused"] = len(created)
        response["created_link_ids"] = created
        return JsonResponse(response, status=201)

    return JsonResponse(
        {"success": False, "detail": "Ação inválida para a matriz de fusão do DIO."},
        status=400,
    )
