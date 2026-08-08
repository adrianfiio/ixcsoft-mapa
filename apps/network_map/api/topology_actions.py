from __future__ import annotations

import math

from django.contrib.gis.geos import LineString, MultiLineString
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company
from apps.network_map.kmz_import_models import CableElementPassage, KMZImportObject
from apps.network_map.models import (
    CTOSplitter,
    ContainerPortLink,
    FiberCable,
    FiberSplice,
    FiberStrand,
    FiberTube,
    NetworkElement,
    PoleCableAttachment,
    SpliceTraySplitter,
    SpliceTraySplitterPort,
)
from apps.network_map.services import FiberStructureError, generate_cable_fibers


def _distance_m(a, b):
    lon1, lat1 = a
    lon2, lat2 = b
    dx = (lon2 - lon1) * 111320 * math.cos(math.radians((lat1 + lat2) / 2))
    dy = (lat2 - lat1) * 110540
    return math.hypot(dx, dy)


def _project(point, a, b):
    px, py = point
    ax, ay = a
    bx, by = b
    vx, vy = bx - ax, by - ay
    denom = vx * vx + vy * vy
    t = 0.0 if denom == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / denom))
    projected = (ax + t * vx, ay + t * vy)
    return projected, t, _distance_m(point, projected)


def _nearest_cut(coords, point):
    best = None
    passed = 0.0
    for index in range(len(coords) - 1):
        segment_length = _distance_m(coords[index], coords[index + 1])
        projected, t, distance = _project(point, coords[index], coords[index + 1])
        candidate = {
            "segment": index,
            "projected": projected,
            "t": t,
            "distance_m": distance,
            "position_m": passed + segment_length * t,
        }
        if best is None or distance < best["distance_m"]:
            best = candidate
        passed += segment_length
    if best is not None:
        best["total_length_m"] = passed
    return best


def _line_distance(point, coords):
    values = [_project(point, coords[index], coords[index + 1])[2] for index in range(len(coords) - 1)]
    return min(values) if values else float("inf")


def _next_code(cable):
    base = (cable.code or cable.name or f"CAB-{cable.pk}").strip()
    for index in range(2, 1000):
        suffix = f"-{index}"
        candidate = f"{base[: max(1, 100 - len(suffix))]}{suffix}"
        if not FiberCable.objects.filter(project=cable.project, code=candidate).exists():
            return candidate
    raise ValueError("Não foi possível gerar código para o novo segmento.")


def _auto_cable_name(origin, destination, fiber_count):
    origin_name = (origin.name if origin else "SEM ORIGEM").strip()
    destination_name = (destination.name if destination else "SEM DESTINO").strip()
    return f"CABO {origin_name} → {destination_name} {int(fiber_count or 0)} F"


def _is_downstream_element(host, cut_element, old_destination, first, second):
    if not host or host.pk == cut_element.pk:
        return False
    if old_destination and host.pk == old_destination.pk:
        return True
    if host.point is None:
        return False
    point = (host.point.x, host.point.y)
    return _line_distance(point, second) < _line_distance(point, first)


def _ensure_second_segment_fibers(source, target):
    """Garante a estrutura do segundo segmento sem gerar fibras duas vezes.

    FiberCable com cable_model já recebe tubos/fibras pelo signal post_save.
    O corte deve reutilizar essa estrutura. Só geramos manualmente quando o
    segmento realmente nasceu vazio.
    """
    source_fibers = list(source.fibers.select_related("tube", "color").order_by("number"))
    if not source_fibers:
        return {}, {}

    target_fibers = list(target.fibers.select_related("tube", "color").order_by("number"))
    target_tube_count = target.tubes.count()

    if not target_fibers:
        if target_tube_count:
            raise ValueError(
                "O novo segmento ficou com tubos sem fibras. O corte foi cancelado para não corromper a estrutura óptica."
            )
        if target.cable_model:
            try:
                generate_cable_fibers(target)
            except FiberStructureError as exc:
                raise ValueError(f"Não foi possível gerar as fibras do novo segmento: {exc}") from exc
        else:
            tube_map = {}
            for tube in source.tubes.select_related("color").order_by("number"):
                clone = FiberTube.objects.create(
                    cable=target,
                    number=tube.number,
                    color=tube.color,
                    identification=tube.identification,
                )
                tube_map[tube.id] = clone
            for fiber in source_fibers:
                FiberStrand.objects.create(
                    cable=target,
                    tube=tube_map.get(fiber.tube_id),
                    number=fiber.number,
                    position_in_tube=fiber.position_in_tube,
                    color=fiber.color,
                    status=fiber.status,
                    origin_element=None,
                    destination_element=None,
                    usage=fiber.usage,
                    notes=fiber.notes,
                )
        target_fibers = list(target.fibers.select_related("tube", "color").order_by("number"))

    target_by_number = {fiber.number: fiber for fiber in target_fibers}
    source_by_number = {fiber.number: fiber for fiber in source_fibers}
    missing = sorted(set(source_by_number) - set(target_by_number))
    if missing:
        raise ValueError(
            "O novo segmento não reproduziu todas as fibras do cabo original: "
            + ", ".join(f"F{number}" for number in missing)
        )

    # O signal cria a estrutura física, mas o estado operacional pertence ao
    # cabo que está sendo cortado. Copiamos esses dados para o novo trecho.
    for number, source_fiber in source_by_number.items():
        target_fiber = target_by_number[number]
        changed = []
        for field in ("status", "usage", "notes"):
            value = getattr(source_fiber, field)
            if getattr(target_fiber, field) != value:
                setattr(target_fiber, field, value)
                changed.append(field)
        if changed:
            target_fiber.save(update_fields=[*changed, "updated_at"])

    return source_by_number, target_by_number


def _copy_fiber_state(source_by_number, target_by_number, cut_element):
    for number, old_fiber in source_by_number.items():
        new_fiber = target_by_number[number]
        new_fiber.status = old_fiber.status
        new_fiber.usage = old_fiber.usage
        new_fiber.notes = old_fiber.notes
        new_fiber.origin_element = cut_element
        new_fiber.destination_element_id = old_fiber.destination_element_id
        new_fiber.save(
            update_fields=[
                "status", "usage", "notes", "origin_element",
                "destination_element", "updated_at",
            ]
        )
        old_fiber.destination_element = cut_element
        old_fiber.save(update_fields=["destination_element", "updated_at"])


def _move_optical_references(
    source_by_number,
    target_by_number,
    cut_element,
    old_destination,
    first,
    second,
    source_cable,
    target_cable,
):
    moved = {
        "splices": 0,
        "splitter_inputs": 0,
        "splitter_outputs": 0,
        "cto_splitter_inputs": 0,
        "container_links": 0,
    }

    for number, old_fiber in source_by_number.items():
        new_fiber = target_by_number[number]

        # Na caixa do corte, input é chegada e output é distribuição.
        # Em caixas posteriores, referências do cabo original passam ao novo trecho.
        for splice in FiberSplice.objects.filter(input_fiber=old_fiber).select_related("splice_box"):
            if _is_downstream_element(splice.splice_box, cut_element, old_destination, first, second):
                splice.input_fiber = new_fiber
                splice.save(update_fields=["input_fiber", "updated_at"])
                moved["splices"] += 1

        for splice in FiberSplice.objects.filter(output_fiber=old_fiber).select_related("splice_box"):
            if splice.splice_box_id == cut_element.id or _is_downstream_element(
                splice.splice_box, cut_element, old_destination, first, second
            ):
                splice.output_fiber = new_fiber
                splice.save(update_fields=["output_fiber", "updated_at"])
                moved["splices"] += 1

        for splitter in SpliceTraySplitter.objects.filter(input_fiber=old_fiber).select_related("tray__splice_box"):
            host = splitter.tray.splice_box
            if _is_downstream_element(host, cut_element, old_destination, first, second):
                splitter.input_fiber = new_fiber
                splitter.save(update_fields=["input_fiber", "updated_at"])
                moved["splitter_inputs"] += 1

        for port in SpliceTraySplitterPort.objects.filter(output_fiber=old_fiber).select_related("splitter__tray__splice_box"):
            host = port.splitter.tray.splice_box
            if host.id == cut_element.id or _is_downstream_element(
                host, cut_element, old_destination, first, second
            ):
                port.output_fiber = new_fiber
                port.save(update_fields=["output_fiber", "updated_at"])
                moved["splitter_outputs"] += 1

        for splitter in CTOSplitter.objects.filter(input_fiber=old_fiber).select_related("cto"):
            if _is_downstream_element(splitter.cto, cut_element, old_destination, first, second):
                splitter.input_fiber = new_fiber
                splitter.input_cable = target_cable
                splitter.save(update_fields=["input_fiber", "input_cable", "updated_at"])
                moved["cto_splitter_inputs"] += 1

        for link in ContainerPortLink.objects.filter(cable_fiber=old_fiber).select_related("container"):
            if _is_downstream_element(link.container, cut_element, old_destination, first, second):
                link.cable_fiber = new_fiber
                link.cable = target_cable
                link.save(update_fields=["cable_fiber", "cable", "updated_at"])
                moved["container_links"] += 1

    for link in ContainerPortLink.objects.filter(cable=source_cable, cable_fiber__isnull=True).select_related("container"):
        if _is_downstream_element(link.container, cut_element, old_destination, first, second):
            link.cable = target_cable
            link.save(update_fields=["cable", "updated_at"])
            moved["container_links"] += 1

    return moved


def _move_downstream_topology(source_cable, target_cable, cut_element, old_destination, first, second):
    moved = {"passages": 0, "reserves": 0, "poles": 0}

    for passage in list(
        CableElementPassage.objects.filter(cable=source_cable)
        .exclude(element=cut_element)
        .select_related("element")
    ):
        if _is_downstream_element(passage.element, cut_element, old_destination, first, second):
            passage.cable = target_cable
            passage.save(update_fields=["cable", "updated_at"])
            moved["passages"] += 1

    for reserve in list(source_cable.reserves.all()):
        point = (reserve.point.x, reserve.point.y)
        if _line_distance(point, second) < _line_distance(point, first):
            reserve.cable = target_cable
            reserve.save(update_fields=["cable", "updated_at"])
            moved["reserves"] += 1

    for attachment in list(PoleCableAttachment.objects.filter(cable=source_cable).select_related("pole")):
        if _is_downstream_element(attachment.pole, cut_element, old_destination, first, second):
            attachment.cable = target_cable
            attachment.save(update_fields=["cable", "updated_at"])
            moved["poles"] += 1

    return moved


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cut_cable_at_element(request, element_id, cable_id):
    """Corta um cabo na CTO/CEO/CDO sem destruir trabalho óptico já cadastrado."""
    element = get_object_or_404(
        NetworkElement,
        pk=element_id,
        element_type__in=[NetworkElement.ElementType.SPLICE_BOX, NetworkElement.ElementType.CTO],
    )
    cable = get_object_or_404(
        FiberCable.objects.select_related("project", "company", "origin", "destination", "route"),
        pk=cable_id,
    )
    if not can_edit_company(request.user, element.company_id):
        return JsonResponse({"success": False, "error": "Sem permissão para editar esta empresa."}, status=403)
    if cable.company_id != element.company_id or cable.project_id != element.project_id:
        return JsonResponse({"success": False, "error": "O cabo e a caixa não pertencem ao mesmo projeto."}, status=400)
    if cable.origin_id == element.id or cable.destination_id == element.id:
        return JsonResponse({"success": True, "already_cut": True, "cables": [cable.id]})
    if not cable.geometry or not cable.geometry.num_geom:
        return JsonResponse({"success": False, "error": "O cabo não possui geometria válida."}, status=400)

    coords = [tuple(value) for value in cable.geometry[0].coords]
    if len(coords) < 2 or element.point is None:
        return JsonResponse({"success": False, "error": "Geometria insuficiente para realizar o corte."}, status=400)
    target = (element.point.x, element.point.y)
    cut = _nearest_cut(coords, target)
    if cut is None:
        return JsonResponse({"success": False, "error": "Não foi possível projetar a caixa sobre o cabo."}, status=400)

    max_distance = float(request.data.get("max_distance_m") or 60)
    if cut["distance_m"] > max_distance:
        return JsonResponse(
            {
                "success": False,
                "error": f"A caixa está a {cut['distance_m']:.1f} m do cabo; o limite para corte é {max_distance:.1f} m.",
            },
            status=409,
        )
    endpoint_guard = float(request.data.get("endpoint_guard_m") or 0.75)
    if cut["position_m"] <= endpoint_guard or cut["total_length_m"] - cut["position_m"] <= endpoint_guard:
        return JsonResponse({"success": False, "error": "A caixa já está praticamente na ponta do cabo."}, status=409)

    segment = cut["segment"]
    cut_point = target
    first = coords[: segment + 1]
    if first[-1] != cut_point:
        first.append(cut_point)
    second = [cut_point]
    if coords[segment + 1] != cut_point:
        second.append(coords[segment + 1])
    second.extend(coords[segment + 2:])
    if len(first) < 2 or len(second) < 2:
        return JsonResponse({"success": False, "error": "O corte geraria um segmento inválido."}, status=409)

    old_destination = cable.destination
    first_name = _auto_cable_name(cable.origin, element, cable.fiber_count)
    second_name = _auto_cable_name(element, old_destination, cable.fiber_count)

    try:
        new_code = _next_code(cable)
        with transaction.atomic():
            cable = FiberCable.objects.select_for_update().get(pk=cable.pk)
            cable.name = first_name
            cable.destination = element
            cable.geometry = MultiLineString(LineString(first, srid=4326), srid=4326)
            cable.save(update_fields=["name", "destination", "geometry", "updated_at"])

            new_cable = FiberCable.objects.create(
                project=cable.project,
                company=cable.company,
                name=second_name,
                code=new_code,
                description=cable.description,
                cable_type=cable.cable_type,
                cable_model=cable.cable_model,
                geometry=MultiLineString(LineString(second, srid=4326), srid=4326),
                fiber_count=cable.fiber_count,
                used_fibers=cable.used_fibers,
                origin=element,
                destination=old_destination,
                route=cable.route,
                status=cable.status,
            )

            source_by_number, target_by_number = _ensure_second_segment_fibers(cable, new_cable)
            _copy_fiber_state(source_by_number, target_by_number, element)
            optical_moved = _move_optical_references(
                source_by_number, target_by_number, element, old_destination,
                first, second, cable, new_cable,
            )
            topology_moved = _move_downstream_topology(
                cable, new_cable, element, old_destination, first, second,
            )

            CableElementPassage.objects.filter(cable=cable, element=element).delete()
            CableElementPassage.objects.get_or_create(
                cable=cable,
                element=element,
                action=CableElementPassage.Action.CUT,
                defaults={
                    "sequence": 1,
                    "position_m": cut["position_m"],
                    "distance_m": cut["distance_m"],
                    "metadata": {"manual_cut": True, "segment": "before"},
                },
            )
            CableElementPassage.objects.get_or_create(
                cable=new_cable,
                element=element,
                action=CableElementPassage.Action.CUT,
                defaults={
                    "sequence": 2,
                    "position_m": 0,
                    "distance_m": cut["distance_m"],
                    "metadata": {
                        "manual_cut": True,
                        "segment": "after",
                        "source_cable_id": cable.id,
                    },
                },
            )

            tracked = (
                KMZImportObject.objects.filter(
                    object_type="fiber_cable",
                    object_id=cable.id,
                    batch__status="imported",
                )
                .select_related("batch")
                .order_by("-batch__created_at")
                .first()
            )
            if tracked:
                KMZImportObject.objects.get_or_create(
                    batch=tracked.batch,
                    object_type="fiber_cable",
                    object_id=new_cable.id,
                    defaults={
                        "source_id": tracked.source_id,
                        "source_name": tracked.source_name,
                        "source_folder": tracked.source_folder,
                        "metadata": {
                            **(tracked.metadata or {}),
                            "manual_cut": True,
                            "source_cable_id": cable.id,
                            "cut_element_id": element.id,
                        },
                    },
                )
                summary = dict(tracked.batch.summary or {})
                summary["cables"] = int(summary.get("cables") or 0) + 1
                summary["fibers"] = int(summary.get("fibers") or 0) + new_cable.fibers.count()
                summary["fiber_tubes"] = int(summary.get("fiber_tubes") or 0) + new_cable.tubes.count()
                tracked.batch.summary = summary
                tracked.batch.save(update_fields=["summary", "updated_at"])
    except (FiberStructureError, ValueError, TypeError) as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=409)

    return JsonResponse(
        {
            "success": True,
            "element": {"id": element.id, "name": element.name},
            "distance_m": round(cut["distance_m"], 2),
            "optical_references_moved": optical_moved,
            "topology_records_moved": topology_moved,
            "cables": [
                {"id": cable.id, "name": cable.name, "code": cable.code},
                {"id": new_cable.id, "name": new_cable.name, "code": new_cable.code},
            ],
        },
        status=201,
    )
