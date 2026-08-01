from __future__ import annotations

import math

from django.contrib.gis.geos import LineString, MultiLineString
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company
from apps.network_map.kmz_import_models import CableElementPassage, KMZImportObject
from apps.network_map.models import FiberCable, NetworkElement
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


def _cable_has_optical_work(cable):
    return cable.fibers.filter(
        Q(splice_outputs__isnull=False)
        | Q(splice_inputs__isnull=False)
        | Q(splice_box_splitter_inputs__isnull=False)
        | Q(splice_box_splitter_outputs__isnull=False)
        | Q(container_port_links__isnull=False)
    ).exists()


def _next_code(cable):
    base = (cable.code or cable.name or f"CAB-{cable.pk}").strip()
    for index in range(2, 1000):
        suffix = f"-{index}"
        candidate = f"{base[: max(1, 100 - len(suffix))]}{suffix}"
        if not FiberCable.objects.filter(project=cable.project, code=candidate).exists():
            return candidate
    raise ValueError("Não foi possível gerar código para o novo segmento.")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cut_cable_at_element(request, element_id, cable_id):
    """Corta com segurança um cabo de passagem na CTO/CEO/CDO.

    A ação é pensada para o fluxo importado: primeiro o cabo pode apenas passar
    pela caixa; depois, na tela de fusões, o operador decide cortá-lo. Para não
    corromper emendas existentes, o corte é bloqueado caso qualquer fibra do
    cabo já esteja utilizada.
    """
    element = get_object_or_404(
        NetworkElement,
        pk=element_id,
        element_type__in=[NetworkElement.ElementType.SPLICE_BOX, NetworkElement.ElementType.CTO],
    )
    cable = get_object_or_404(FiberCable.objects.select_related("project", "company"), pk=cable_id)
    if not can_edit_company(request.user, element.company_id):
        return JsonResponse({"success": False, "error": "Sem permissão para editar esta empresa."}, status=403)
    if cable.company_id != element.company_id or cable.project_id != element.project_id:
        return JsonResponse({"success": False, "error": "O cabo e a caixa não pertencem ao mesmo projeto."}, status=400)
    if cable.origin_id == element.id or cable.destination_id == element.id:
        return JsonResponse({"success": True, "already_cut": True, "cables": [cable.id]})
    if not cable.geometry or not cable.geometry.num_geom:
        return JsonResponse({"success": False, "error": "O cabo não possui geometria válida."}, status=400)
    if _cable_has_optical_work(cable):
        return JsonResponse(
            {
                "success": False,
                "error": "Este cabo já possui fusões/terminações. Desfaça essas ligações antes de cortá-lo na caixa.",
            },
            status=409,
        )

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
    # O cálculo usa a projeção para descobrir o segmento correto, mas o
    # traçado final encaixa no ponto real da caixa. Assim origem/destino e
    # geometria permanecem coerentes no mapa mesmo quando o KMZ veio alguns
    # metros deslocado.
    cut_point = target
    first = coords[: segment + 1]
    if first[-1] != cut_point:
        first.append(cut_point)
    second = [cut_point]
    if coords[segment + 1] != cut_point:
        second.append(coords[segment + 1])
    second.extend(coords[segment + 2 :])
    if len(first) < 2 or len(second) < 2:
        return JsonResponse({"success": False, "error": "O corte geraria um segmento inválido."}, status=409)

    old_destination = cable.destination
    try:
        new_code = _next_code(cable)
        with transaction.atomic():
            cable.destination = element
            cable.geometry = MultiLineString(LineString(first, srid=4326), srid=4326)
            cable.save(update_fields=["destination", "geometry", "updated_at"])

            new_cable = FiberCable.objects.create(
                project=cable.project,
                company=cable.company,
                name=f"{cable.name} · trecho 2",
                code=new_code,
                description=cable.description,
                cable_type=cable.cable_type,
                cable_model=cable.cable_model,
                geometry=MultiLineString(LineString(second, srid=4326), srid=4326),
                fiber_count=cable.fiber_count,
                origin=element,
                destination=old_destination,
                route=cable.route,
                status=cable.status,
            )
            if new_cable.cable_model and not new_cable.fibers.exists():
                try:
                    generate_cable_fibers(new_cable)
                except FiberStructureError as exc:
                    raise ValueError(f"Não foi possível gerar as fibras do novo segmento: {exc}") from exc

            # Reservas posteriores ao ponto de corte pertencem ao segundo trecho.
            for reserve in list(cable.reserves.all()):
                point = (reserve.point.x, reserve.point.y)
                if _line_distance(point, second) < _line_distance(point, first):
                    reserve.cable = new_cable
                    reserve.save(update_fields=["cable", "updated_at"])

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
                    "metadata": {"manual_cut": True, "segment": "after", "source_cable_id": cable.id},
                },
            )

            # Se o cabo nasceu de um lote KMZ, o novo segmento entra no mesmo
            # lote. Assim “Desfazer lote” continua removendo tudo, inclusive
            # cortes manuais realizados posteriormente na tela de fusões.
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
            "cables": [
                {"id": cable.id, "name": cable.name, "code": cable.code},
                {"id": new_cable.id, "name": new_cable.name, "code": new_cable.code},
            ],
        },
        status=201,
    )
