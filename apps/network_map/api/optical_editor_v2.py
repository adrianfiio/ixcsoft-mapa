from __future__ import annotations

import math
from decimal import Decimal

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company
from apps.network_map.kmz_import_models import CableElementPassage
from apps.network_map.models import FiberCable, NetworkElement


def _distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distância aproximada em metros para trechos curtos de rede."""
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
    denominator = vx * vx + vy * vy
    ratio = 0.0 if denominator == 0 else max(
        0.0,
        min(1.0, ((px - ax) * vx + (py - ay) * vy) / denominator),
    )
    projected = (ax + ratio * vx, ay + ratio * vy)
    return projected, ratio, _distance_m(point, projected)


def nearest_position_m(coords, point):
    """Retorna posição longitudinal e distância da caixa ao cabo."""
    best = None
    passed = 0.0
    for index in range(max(0, len(coords) - 1)):
        start = coords[index]
        end = coords[index + 1]
        segment_length = _distance_m(start, end)
        projected, ratio, distance = _project(point, start, end)
        candidate = {
            "projected": projected,
            "distance_m": distance,
            "position_m": passed + segment_length * ratio,
        }
        if best is None or distance < best["distance_m"]:
            best = candidate
        passed += segment_length
    return best


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_cable_passage(request, element_id, cable_id):
    """Registra passagem manual de um cabo por uma CTO/CEO/CDO sem cortá-lo.

    O mapa usa esta ação após a prévia visual. Para corte físico, permanece sendo
    utilizado o endpoint seguro ``cut_cable_at_element`` já existente.
    """
    element = get_object_or_404(
        NetworkElement,
        pk=element_id,
        element_type__in=[
            NetworkElement.ElementType.CTO,
            NetworkElement.ElementType.SPLICE_BOX,
        ],
    )
    cable = get_object_or_404(
        FiberCable.objects.select_related("project", "company"),
        pk=cable_id,
    )
    if not can_edit_company(request.user, element.company_id):
        return JsonResponse(
            {"success": False, "error": "Sem permissão para editar esta empresa."},
            status=403,
        )
    if cable.company_id != element.company_id or cable.project_id != element.project_id:
        return JsonResponse(
            {"success": False, "error": "O cabo e a caixa não pertencem ao mesmo projeto."},
            status=400,
        )
    if not cable.geometry or not cable.geometry.num_geom or element.point is None:
        return JsonResponse(
            {"success": False, "error": "Cabo ou caixa sem geometria válida."},
            status=400,
        )

    coords = [tuple(value) for value in cable.geometry[0].coords]
    result = nearest_position_m(coords, (element.point.x, element.point.y))
    if result is None:
        return JsonResponse(
            {"success": False, "error": "Não foi possível projetar a caixa sobre o cabo."},
            status=400,
        )

    try:
        maximum = float(request.data.get("max_distance_m") or 60)
    except (TypeError, ValueError):
        maximum = 60.0
    maximum = min(500.0, max(0.5, maximum))
    if result["distance_m"] > maximum:
        return JsonResponse(
            {
                "success": False,
                "error": (
                    f"A caixa está a {result['distance_m']:.1f} m do cabo; "
                    f"o limite configurado é {maximum:.1f} m."
                ),
            },
            status=409,
        )

    passage, created = CableElementPassage.objects.update_or_create(
        cable=cable,
        element=element,
        action=CableElementPassage.Action.PASS,
        defaults={
            "sequence": 1,
            "position_m": Decimal(str(round(result["position_m"], 2))),
            "distance_m": Decimal(str(round(result["distance_m"], 2))),
            "metadata": {
                "manual": True,
                "source": "optical_editor_v2",
                "projected": {
                    "longitude": result["projected"][0],
                    "latitude": result["projected"][1],
                },
            },
        },
    )
    return JsonResponse(
        {
            "success": True,
            "created": created,
            "passage": {
                "id": passage.id,
                "action": passage.action,
                "position_m": float(passage.position_m or 0),
                "distance_m": float(passage.distance_m or 0),
            },
            "element": {"id": element.id, "name": element.name},
            "cable": {"id": cable.id, "name": cable.name},
        },
        status=201 if created else 200,
    )
