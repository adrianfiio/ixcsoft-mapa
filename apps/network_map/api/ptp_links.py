from __future__ import annotations

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company, can_view_company, scope_company_queryset
from apps.network_map.models import (
    ContainerEquipmentPort,
    ContainerPortLink,
    NetworkElement,
    NetworkProject,
)


def _busy_port_ids(project_id: int) -> set[int]:
    links = ContainerPortLink.objects.filter(
        link_type=ContainerPortLink.LinkType.WIRELESS,
    ).filter(
        Q(source_port__equipment__container__project_id=project_id)
        | Q(destination_port__equipment__container__project_id=project_id)
    )
    result: set[int] = set()
    for source_id, destination_id in links.values_list(
        "source_port_id", "destination_port_id"
    ):
        if source_id:
            result.add(source_id)
        if destination_id:
            result.add(destination_id)
    return result


def _wireless_link_payload(link: ContainerPortLink) -> dict:
    source_port = link.source_port
    destination_port = link.destination_port
    source_equipment = source_port.equipment
    destination_equipment = destination_port.equipment
    source_tower = source_equipment.container
    destination_tower = destination_equipment.container
    return {
        "id": link.id,
        "source": {
            "tower_id": source_tower.id,
            "tower_name": source_tower.name,
            "latitude": source_tower.point.y,
            "longitude": source_tower.point.x,
            "equipment_id": source_equipment.id,
            "equipment_name": source_equipment.name,
            "port_id": source_port.id,
            "port_label": source_port.label,
        },
        "destination": {
            "tower_id": destination_tower.id,
            "tower_name": destination_tower.name,
            "latitude": destination_tower.point.y,
            "longitude": destination_tower.point.x,
            "equipment_id": destination_equipment.id,
            "equipment_name": destination_equipment.name,
            "port_id": destination_port.id,
            "port_label": destination_port.label,
        },
        "notes": link.notes,
        "created_at": link.created_at.isoformat(),
    }


def _wireless_links_queryset(project):
    return (
        ContainerPortLink.objects.filter(
            link_type=ContainerPortLink.LinkType.WIRELESS,
            source_port__equipment__container__project=project,
        )
        .select_related(
            "source_port__equipment__container",
            "destination_port__equipment__container",
        )
        .order_by("id")
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def ptp_links(request):
    if request.method == "GET":
        project_id = request.GET.get("project_id")
        if not project_id:
            return JsonResponse({"detail": "Informe project_id."}, status=400)
        project = get_object_or_404(
            scope_company_queryset(NetworkProject.objects, request.user),
            pk=project_id,
        )
        if not can_view_company(request.user, project.company_id):
            return JsonResponse({"detail": "Sem permissão para visualizar esta empresa."}, status=403)
        links = [
            link
            for link in _wireless_links_queryset(project)
            if (
                link.source_port.equipment.container_id
                != link.destination_port.equipment.container_id
            )
        ]
        return JsonResponse({
            "project_id": project.id,
            "links": [_wireless_link_payload(link) for link in links],
        })

    source_port_id = request.data.get("source_port_id")
    destination_port_id = request.data.get("destination_port_id")
    if not source_port_id or not destination_port_id:
        return JsonResponse(
            {"detail": "Informe as portas wireless de origem e destino."},
            status=400,
        )

    source = get_object_or_404(
        ContainerEquipmentPort.objects.select_related(
            "equipment__container__project"
        ),
        pk=source_port_id,
    )
    destination = get_object_or_404(
        ContainerEquipmentPort.objects.select_related(
            "equipment__container__project"
        ),
        pk=destination_port_id,
    )
    source_tower = source.equipment.container
    destination_tower = destination.equipment.container

    if not can_edit_company(request.user, source.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    if source.company_id != destination.company_id:
        return JsonResponse({"detail": "As duas pontas precisam pertencer à mesma empresa."}, status=400)
    if source_tower.project_id != destination_tower.project_id:
        return JsonResponse({"detail": "As torres precisam pertencer ao mesmo projeto."}, status=400)
    if source_tower.id == destination_tower.id:
        return JsonResponse({"detail": "Escolha uma torre de destino diferente."}, status=400)
    if (
        source_tower.element_type != NetworkElement.ElementType.TOWER
        or destination_tower.element_type != NetworkElement.ElementType.TOWER
    ):
        return JsonResponse({"detail": "Enlace PTP entre sites exige duas torres."}, status=400)
    if (
        source.port_type != ContainerEquipmentPort.PortType.WIRELESS
        or destination.port_type != ContainerEquipmentPort.PortType.WIRELESS
    ):
        return JsonResponse({"detail": "As duas portas precisam ser do tipo Wireless."}, status=400)

    used = ContainerPortLink.objects.filter(
        Q(source_port_id__in=[source.id, destination.id])
        | Q(destination_port_id__in=[source.id, destination.id])
    )
    if used.exists():
        return JsonResponse({"detail": "Uma das portas wireless já está ligada."}, status=409)

    with transaction.atomic():
        link = ContainerPortLink.objects.create(
            container=source_tower,
            source_port=source,
            destination_port=destination,
            link_type=ContainerPortLink.LinkType.WIRELESS,
            notes="Enlace PTP torre a torre",
        )
    return JsonResponse({"link": _wireless_link_payload(link)}, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ptp_link_candidates(request):
    source_port_id = request.GET.get("source_port_id")
    if not source_port_id:
        return JsonResponse({"detail": "Informe source_port_id."}, status=400)
    source = get_object_or_404(
        ContainerEquipmentPort.objects.select_related(
            "equipment__container__project"
        ),
        pk=source_port_id,
        port_type=ContainerEquipmentPort.PortType.WIRELESS,
    )
    source_tower = source.equipment.container
    if not can_view_company(request.user, source.company_id):
        return JsonResponse({"detail": "Sem permissão para visualizar esta empresa."}, status=403)

    busy = _busy_port_ids(source_tower.project_id)
    candidates = (
        ContainerEquipmentPort.objects.select_related("equipment__container")
        .filter(
            company_id=source.company_id,
            equipment__container__project_id=source_tower.project_id,
            equipment__container__element_type=NetworkElement.ElementType.TOWER,
            equipment__enabled=True,
            port_type=ContainerEquipmentPort.PortType.WIRELESS,
        )
        .exclude(equipment__container_id=source_tower.id)
        .order_by("equipment__container__name", "equipment__name", "label")
    )
    rows = [
        {
            "tower_id": port.equipment.container_id,
            "tower_name": port.equipment.container.name,
            "equipment_id": port.equipment_id,
            "equipment_name": port.equipment.name,
            "port_id": port.id,
            "port_label": port.label,
        }
        for port in candidates
        if port.id not in busy
    ]
    return JsonResponse({
        "source": {
            "tower_id": source_tower.id,
            "tower_name": source_tower.name,
            "equipment_id": source.equipment_id,
            "equipment_name": source.equipment.name,
            "port_id": source.id,
            "port_label": source.label,
        },
        "candidates": rows,
    })


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def ptp_link_detail(request, link_id):
    link = get_object_or_404(
        ContainerPortLink.objects.select_related("container"),
        pk=link_id,
        link_type=ContainerPortLink.LinkType.WIRELESS,
    )
    if not can_edit_company(request.user, link.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    link.delete()
    return HttpResponse(status=204)
