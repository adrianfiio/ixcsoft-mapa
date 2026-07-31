from __future__ import annotations

import json
import math
import re
import uuid
from collections import defaultdict

from django.contrib.gis.geos import LineString, MultiLineString, Point
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company
from apps.network_map.kmz_import import KMZAnalyzer, METERS_RE
from apps.network_map.models import (
    CableModel,
    CableReserve,
    CTO,
    FiberCable,
    NetworkElement,
    NetworkProject,
    NetworkRoute,
)

ROUTE_RE = re.compile(r"(?:^|\s|[-_/])rota(?:\s|[-_/]|$)", re.I)
EXCLUDED_ROUTE_NAMES = {"cabos", "cabo", "pop", "pops", "cto", "ctos", "ceo", "ceos", "cdo", "cdos"}


def _norm(value):
    return " ".join(str(value or "").strip().casefold().split())


def _group_key(classification):
    return classification.get("reason") or "unknown"


def _line_key(item):
    return item.color.get("hex") or "__no_color__"


def _folder_records(placemarks):
    folders = defaultdict(lambda: {"points": 0, "lines": 0, "types": defaultdict(int)})
    for item in placemarks:
        if not item.folder_key:
            continue
        rec = folders[item.folder_key]
        if item.geometry_type == "Point":
            rec["points"] += 1
            c = KMZAnalyzer.classify_point(item.name)
            rec["types"][c.get("suggested_type") or "unknown"] += 1
        elif item.geometry_type == "LineString":
            rec["lines"] += 1
    result = []
    for path, rec in folders.items():
        leaf = path.split(" / ")[-1]
        normalized = _norm(leaf)
        candidate = bool(ROUTE_RE.search(leaf)) and normalized not in EXCLUDED_ROUTE_NAMES
        result.append({
            "path": path,
            "name": leaf,
            "points": rec["points"],
            "lines": rec["lines"],
            "composition": dict(rec["types"]),
            "route_candidate": candidate,
        })
    return sorted(result, key=lambda x: x["path"])


def _analysis(upload, company_id):
    analyzer = KMZAnalyzer.from_upload(upload)
    placemarks = [p for p in analyzer.placemarks() if p.coordinates]
    point_groups = defaultdict(lambda: {"count": 0, "samples": [], "suggested_type": None, "confidence": 0})
    line_groups = defaultdict(lambda: {"count": 0, "total_length_m": 0, "samples": [], "folders": set(), "suggested_fibers": None})
    features = []

    for item in placemarks:
        if item.geometry_type == "Point":
            classification = analyzer.classify_point(item.name)
            key = _group_key(classification)
            group = point_groups[key]
            group["count"] += 1
            if len(group["samples"]) < 8:
                group["samples"].append(item.name)
            group["suggested_type"] = classification.get("suggested_type")
            group["confidence"] = max(group["confidence"], classification.get("confidence") or 0)
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": item.coordinates[0]},
                "properties": {"source_id": item.source_id, "name": item.name, "folder": item.folder_key, "group_key": key, "kind": "point"},
            })
        elif item.geometry_type == "LineString":
            key = _line_key(item)
            group = line_groups[key]
            group["count"] += 1
            group["total_length_m"] += item.length_m
            if len(group["samples"]) < 8:
                group["samples"].append(item.name)
            group["folders"].add(item.folder_key)
            guess = analyzer.classify_line(item.name)
            if guess.get("fiber_count_hint"):
                group["suggested_fibers"] = guess["fiber_count_hint"]
            features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": item.coordinates},
                "properties": {"source_id": item.source_id, "name": item.name, "folder": item.folder_key, "color": item.color.get("hex"), "color_key": key, "kind": "line", "length_m": round(item.length_m, 1)},
            })

    lines = []
    for key, group in line_groups.items():
        default_action = "review" if key in {"#000000", "__no_color__"} else "cable"
        lines.append({
            "key": key,
            "hex": None if key == "__no_color__" else key,
            "count": group["count"],
            "total_length_m": round(group["total_length_m"], 1),
            "samples": group["samples"],
            "folders": sorted(filter(None, group["folders"])),
            "suggested_fibers": group["suggested_fibers"],
            "default_action": default_action,
        })

    points = []
    for key, group in point_groups.items():
        points.append({"key": key, **group})

    total_points = sum(1 for p in placemarks if p.geometry_type == "Point")
    total_lines = sum(1 for p in placemarks if p.geometry_type == "LineString")
    cable_models = list(
        CableModel.objects.filter(company_id=company_id)
        .order_by("fiber_count", "name")
        .values("id", "name", "fiber_count")
    )
    return {
        "summary": {
            "placemarks": len(placemarks),
            "points": total_points,
            "lines": total_lines,
            "total_line_length_m": round(sum(p.length_m for p in placemarks), 1),
        },
        "line_color_groups": sorted(lines, key=lambda x: (-x["count"], x["key"])),
        "point_groups": sorted(points, key=lambda x: (-x["count"], x["key"])),
        "folders": _folder_records(placemarks),
        "supported_fiber_counts": [2, 4, 6, 8, 12, 16, 24, 36, 48, 72, 96, 144, 288],
        "cable_models": cable_models,
        "preview_geojson": {"type": "FeatureCollection", "features": features},
        "warnings": [
            "Linhas pretas ou sem estilo ficam como Revisar por padrão.",
            "Somente pastas cujo nome contém ROTA são sugeridas como rota; raiz, CABOS e POP ficam desmarcadas.",
        ],
    }


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def analyze_kmz_import(request, project_id):
    project = get_object_or_404(NetworkProject, pk=project_id, enabled=True)
    if not can_edit_company(request.user, project.company_id):
        return JsonResponse({"success": False, "error": "Seu acesso é somente VIEW."}, status=403)
    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"success": False, "error": "Selecione um KML ou KMZ."}, status=400)
    try:
        return JsonResponse({"success": True, "analysis": _analysis(upload, project.company_id)})
    except (ValueError, TypeError) as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


def _distance_point_to_vertices(point, coords):
    lon, lat = point
    best = float("inf")
    for x, y in coords:
        dx = (x - lon) * 111320 * math.cos(math.radians(lat))
        dy = (y - lat) * 110540
        best = min(best, math.hypot(dx, dy))
    return best


def _resolve_cable_model(company_id, fiber_count, requested_id=None):
    """Tenta casar o cabo importado com um modelo cadastrado (mesma empresa)
    para que o sinal de pós-gravação gere tubos/fibras automaticamente. Sem
    um modelo casado, o cabo é criado só com `fiber_count` (mesmo
    comportamento do desenho manual de cabo), e as fibras precisam ser
    geradas depois em /cables/<id>/generate-fibers/."""
    if requested_id:
        model = CableModel.objects.filter(pk=requested_id, company_id=company_id).first()
        if model:
            return model
    return (
        CableModel.objects.filter(company_id=company_id, fiber_count=fiber_count)
        .order_by("id")
        .first()
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def execute_kmz_import(request, project_id):
    project = get_object_or_404(NetworkProject, pk=project_id, enabled=True)
    if not can_edit_company(request.user, project.company_id):
        return JsonResponse({"success": False, "error": "Seu acesso é somente VIEW."}, status=403)
    upload = request.FILES.get("file")
    try:
        decisions = json.loads(request.POST.get("decisions") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Decisões inválidas."}, status=400)
    if not upload:
        return JsonResponse({"success": False, "error": "Envie novamente o KML/KMZ."}, status=400)

    try:
        analyzer = KMZAnalyzer.from_upload(upload)
        placemarks = [p for p in analyzer.placemarks() if p.coordinates]
        selected_routes = set(decisions.get("routes") or [])
        color_rules = decisions.get("line_groups") or {}
        point_rules = decisions.get("point_groups") or {}
        default_cto_capacity = int(decisions.get("default_cto_capacity") or 16)
        default_reserve_length = float(decisions.get("default_reserve_length_m") or 20)
        counts = defaultdict(int)
        warnings = []
        route_by_path = {}
        imported_cables = []

        with transaction.atomic():
            for path in sorted(selected_routes):
                leaf = path.split(" / ")[-1]
                route = NetworkRoute.objects.create(
                    project=project, company=project.company, name=leaf,
                    code=f"KMZ-ROTA-{uuid.uuid4().hex[:8].upper()}",
                    geometry=None,
                )
                route_by_path[path] = route
                counts["routes"] += 1

            for item in placemarks:
                if item.geometry_type != "LineString":
                    continue
                key = _line_key(item)
                rule = color_rules.get(key) or {}
                action = rule.get("action") or "ignore"
                if action == "ignore" or action == "review":
                    counts["ignored_lines"] += 1
                    continue
                line = LineString(item.coordinates, srid=4326)
                if action == "route":
                    NetworkRoute.objects.create(
                        project=project, company=project.company, name=item.name,
                        code=f"KMZ-LINHA-{uuid.uuid4().hex[:8].upper()}",
                        geometry=MultiLineString(line, srid=4326),
                    )
                    counts["routes"] += 1
                    continue
                fiber_count = int(rule.get("fiber_count") or 12)
                cable_model = _resolve_cable_model(project.company_id, fiber_count, rule.get("cable_model_id"))
                matched_route = next((route for path, route in route_by_path.items() if item.folder_key == path or item.folder_key.startswith(path + " / ")), None)
                cable = FiberCable.objects.create(
                    project=project, company=project.company, name=item.name,
                    code=f"KMZ-CABO-{uuid.uuid4().hex[:8].upper()}",
                    cable_type=rule.get("cable_type") or FiberCable.CableType.DISTRIBUTION,
                    geometry=MultiLineString(line, srid=4326), fiber_count=fiber_count,
                    cable_model=cable_model,
                    route=matched_route,
                )
                if cable_model is None:
                    warnings.append(
                        f"Cabo \"{item.name}\": nenhum modelo de {fiber_count} fibras cadastrado; "
                        "gere as fibras manualmente no cabo depois de importar."
                    )
                imported_cables.append((cable, item.coordinates))
                counts["cables"] += 1

            reserve_items = []
            for item in placemarks:
                if item.geometry_type != "Point":
                    continue
                classification = analyzer.classify_point(item.name)
                key = _group_key(classification)
                rule = point_rules.get(key) or {}
                target = rule.get("type") or "ignore"
                if target == "ignore" or target == "review":
                    counts["ignored_points"] += 1
                    continue
                point = Point(*item.coordinates[0], srid=4326)
                metadata = {"kmz_source_id": item.source_id, "kmz_folder": item.folder_key, "kmz_original_name": item.name}
                if target == "technical_reserve":
                    reserve_items.append((item, point, rule))
                    continue
                if target == "cto":
                    route = next((r for p, r in route_by_path.items() if item.folder_key == p or item.folder_key.startswith(p + " / ")), None)
                    CTO.objects.create(
                        project=project, company=project.company, name=item.name,
                        code=f"KMZ-CTO-{uuid.uuid4().hex[:8].upper()}",
                        element_type=NetworkElement.ElementType.CTO, point=point,
                        capacity=int(rule.get("capacity") or default_cto_capacity), route=route,
                        metadata=metadata,
                    )
                    counts["ctos"] += 1
                else:
                    type_map = {
                        "splice_box": NetworkElement.ElementType.SPLICE_BOX,
                        "pole": NetworkElement.ElementType.POLE,
                        "rack": NetworkElement.ElementType.RACK,
                        "tower": NetworkElement.ElementType.TOWER,
                        "olt": NetworkElement.ElementType.OLT,
                        "dio": NetworkElement.ElementType.DIO,
                        "pop": NetworkElement.ElementType.OTHER,
                        "other": NetworkElement.ElementType.OTHER,
                    }
                    if target == "pop":
                        metadata["import_subtype"] = "pop"
                    NetworkElement.objects.create(
                        project=project, company=project.company, name=item.name,
                        code=f"KMZ-EQP-{uuid.uuid4().hex[:8].upper()}",
                        element_type=type_map.get(target, NetworkElement.ElementType.OTHER), point=point,
                        metadata=metadata,
                    )
                    counts["elements"] += 1

            max_distance = float(decisions.get("reserve_max_distance_m") or 150)
            for item, point, rule in reserve_items:
                if not imported_cables:
                    warnings.append(f"RT {item.name}: nenhum cabo importado para associação.")
                    counts["skipped_reserves"] += 1
                    continue
                nearest = min(imported_cables, key=lambda c: _distance_point_to_vertices(item.coordinates[0], c[1]))
                distance = _distance_point_to_vertices(item.coordinates[0], nearest[1])
                if distance > max_distance:
                    warnings.append(f"RT {item.name}: cabo mais próximo a {distance:.0f} m; reserva não criada.")
                    counts["skipped_reserves"] += 1
                    continue
                meters_match = METERS_RE.search(item.name)
                length = float((meters_match.group(1).replace(",", ".") if meters_match else rule.get("length_m") or default_reserve_length))
                CableReserve.objects.create(cable=nearest[0], point=point, length_m=length, label=item.name, notes=f"Importado do KMZ; distância aproximada ao cabo: {distance:.1f} m")
                counts["reserves"] += 1

        return JsonResponse({"success": True, "imported": dict(counts), "warnings": warnings})
    except (ValueError, TypeError) as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
