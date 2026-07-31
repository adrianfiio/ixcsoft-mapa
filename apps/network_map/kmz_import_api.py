from __future__ import annotations

import hashlib
import io
import json
import math
import re
import uuid
from collections import Counter, defaultdict

from django.contrib.gis.geos import LineString, MultiLineString, Point
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company, can_view_company
from apps.network_map.kmz_import import KMZAnalyzer, METERS_RE, normalize
from apps.network_map.kmz_import_models import (
    CableElementPassage,
    KMZImportBatch,
    KMZImportObject,
)
from apps.network_map.kmz_topology import (
    build_topology_plan,
    canonical_decisions,
    distance_m,
    effective_line_rule,
    effective_point_rule,
    point_group_key,
    preview_token,
    route_for_folder,
    route_slug,
    validate_decisions,
)
from apps.network_map.models import (
    CableModel,
    CableReserve,
    CTO,
    FiberCable,
    NetworkElement,
    NetworkProject,
    NetworkRoute,
)

OBJECT_MODELS = {
    "cable_element_passage": CableElementPassage,
    "cable_reserve": CableReserve,
    "fiber_cable": FiberCable,
    "cto": CTO,
    "network_element": NetworkElement,
    "network_route": NetworkRoute,
}


def _project_for_edit(request, project_id):
    project = get_object_or_404(NetworkProject, pk=project_id, enabled=True)
    if not can_edit_company(request.user, project.company_id):
        return None, JsonResponse(
            {"success": False, "error": "Seu acesso é somente VIEW."}, status=403
        )
    return project, None


def _read_upload_and_analysis(upload):
    raw = upload.read()
    upload.seek(0)
    analyzer = KMZAnalyzer.from_upload(upload)
    analysis = analyzer.analyze(getattr(upload, "name", "import.kmz"))
    upload.seek(0)
    return raw, analyzer, analysis


def _cable_models(company_id):
    return list(
        CableModel.objects.filter(company_id=company_id)
        .order_by("fiber_count", "manufacturer", "model")
        .values("id", "name", "manufacturer", "model", "fiber_count", "construction")
    )


def _analysis_payload(upload, project):
    _raw, _analyzer, analysis = _read_upload_and_analysis(upload)
    analysis["cable_models"] = _cable_models(project.company_id)
    analysis["warnings"].extend(
        [
            "Itens em Revisar bloqueiam a prévia final e a importação.",
            "A prévia final recebe um token ligado ao arquivo e às decisões; qualquer alteração exige nova prévia.",
            "CTO/CEO/CDO próximos ao cabo geram sugestões de conexão, corte, passagem ou derivação.",
        ]
    )
    return analysis


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def analyze_kmz_import(request, project_id):
    project, error = _project_for_edit(request, project_id)
    if error:
        return error
    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse(
            {"success": False, "error": "Selecione um KML ou KMZ."}, status=400
        )
    try:
        return JsonResponse(
            {"success": True, "analysis": _analysis_payload(upload, project)}
        )
    except (ValueError, TypeError) as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


def _load_decisions(request):
    try:
        return json.loads(request.POST.get("decisions") or "{}"), None
    except json.JSONDecodeError:
        return None, JsonResponse(
            {"success": False, "error": "Decisões inválidas."}, status=400
        )


def _topology_payload(upload, decisions, project, issue_token=False):
    raw, _analyzer, analysis = _read_upload_and_analysis(upload)
    errors = validate_decisions(analysis, decisions, require_preview=False)
    if errors:
        return None, JsonResponse(
            {
                "success": False,
                "error": "Existem classificações pendentes.",
                "errors": errors,
            },
            status=409,
        )
    plan = build_topology_plan(analysis, decisions)
    file_hash = hashlib.sha256(raw).hexdigest()
    token = preview_token(file_hash, decisions) if issue_token else ""
    return {
        "analysis": analysis,
        "plan": plan,
        "file_sha256": file_hash,
        "preview_token": token,
        "preview_geojson": _preview_geojson(plan, decisions),
    }, None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def topology_kmz_import(request, project_id):
    project, error = _project_for_edit(request, project_id)
    if error:
        return error
    upload = request.FILES.get("file")
    decisions, error = _load_decisions(request)
    if error:
        return error
    if not upload:
        return JsonResponse({"success": False, "error": "Envie o KML/KMZ."}, status=400)
    try:
        payload, error = _topology_payload(upload, decisions, project, issue_token=False)
        if error:
            return error
        return JsonResponse(
            {
                "success": True,
                "junctions": payload["plan"]["junctions"],
                "summary": payload["plan"]["summary"],
            }
        )
    except (ValueError, TypeError) as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def preview_kmz_import(request, project_id):
    project, error = _project_for_edit(request, project_id)
    if error:
        return error
    upload = request.FILES.get("file")
    decisions, error = _load_decisions(request)
    if error:
        return error
    if not upload:
        return JsonResponse({"success": False, "error": "Envie o KML/KMZ."}, status=400)
    try:
        payload, error = _topology_payload(upload, decisions, project, issue_token=True)
        if error:
            return error
        return JsonResponse(
            {
                "success": True,
                "preview_token": payload["preview_token"],
                "summary": payload["plan"]["summary"],
                "junctions": payload["plan"]["junctions"],
                "preview_geojson": payload["preview_geojson"],
            }
        )
    except (ValueError, TypeError) as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


def _preview_geojson(plan, decisions):
    features = []
    point_colors = {
        "cto": "#0ea5e9",
        "splice_box": "#a855f7",
        "technical_reserve": "#f59e0b",
        "pop": "#22c55e",
        "dio": "#14b8a6",
        "pole": "#64748b",
        "other": "#94a3b8",
    }
    for point in plan["points"]:
        target = point["target_type"]
        if target == "ignore":
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": point["coordinates"]},
                "properties": {
                    "kind": "point",
                    "source_id": point["source_id"],
                    "name": point["name"],
                    "target_type": target,
                    "route": point.get("route_path"),
                    "color": point_colors.get(target, "#94a3b8"),
                },
            }
        )
    for cable in plan["cables"]:
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": cable["coordinates"]},
                "properties": {
                    "kind": "cable_segment",
                    "source_id": cable["source_id"],
                    "source_name": cable["source_name"],
                    "proposed_code": cable["proposed_code"],
                    "fiber_count": cable["fiber_count"],
                    "cable_type": cable["cable_type"],
                    "route": cable.get("route_path"),
                    "origin": cable.get("origin_name"),
                    "destination": cable.get("destination_name"),
                    "length_m": cable["length_m"],
                    "color": "#111827" if cable["cable_type"] == "drop" else "#22d3ee",
                },
            }
        )
    for junction in plan["junctions"]:
        if junction["action"] == "ignore":
            continue
        colors = {
            "connect": "#22c55e",
            "cut": "#ef4444",
            "branch": "#f97316",
            "pass": "#facc15",
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": junction["projected"]},
                "properties": {
                    "kind": "junction",
                    "junction_id": junction["junction_id"],
                    "name": junction["point_name"],
                    "line_name": junction["line_name"],
                    "action": junction["action"],
                    "distance_m": junction["distance_m"],
                    "color": colors.get(junction["action"], "#facc15"),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _safe_prefix(value: str, fallback="PROJ") -> str:
    slug = route_slug(value)
    return slug[:24] or fallback


def _unique_route_code(company_id, base):
    base = base[:80]
    candidate = base
    sequence = 2
    while NetworkRoute.objects.filter(company_id=company_id, code=candidate).exists():
        suffix = f"-{sequence}"
        candidate = f"{base[:80-len(suffix)]}{suffix}"
        sequence += 1
    return candidate


def _unique_element_code(project_id, base):
    base = base[:100]
    candidate = base
    sequence = 2
    while NetworkElement.objects.filter(project_id=project_id, code=candidate).exists():
        suffix = f"-{sequence}"
        candidate = f"{base[:100-len(suffix)]}{suffix}"
        sequence += 1
    return candidate


def _unique_cable_code(project_id, base):
    base = base[:100]
    candidate = base
    sequence = 2
    while FiberCable.objects.filter(project_id=project_id, code=candidate).exists():
        suffix = f"-{sequence}"
        candidate = f"{base[:100-len(suffix)]}{suffix}"
        sequence += 1
    return candidate


def _track(batch, obj, object_type, source=None, metadata=None):
    KMZImportObject.objects.create(
        batch=batch,
        object_type=object_type,
        object_id=obj.pk,
        source_id=(source or {}).get("source_id", "") if isinstance(source, dict) else getattr(source, "source_id", ""),
        source_name=(source or {}).get("name", "") if isinstance(source, dict) else getattr(source, "name", ""),
        source_folder=(source or {}).get("folder", "") if isinstance(source, dict) else getattr(source, "folder_key", ""),
        metadata=metadata or {},
    )


def _resolve_cable_model(company_id, fiber_count, requested_id=None):
    if requested_id:
        model = CableModel.objects.filter(pk=requested_id, company_id=company_id).first()
        if model and model.fiber_count == fiber_count:
            return model
    return (
        CableModel.objects.filter(company_id=company_id, fiber_count=fiber_count)
        .order_by("id")
        .first()
    )


def _route_object_for_path(route_by_path, path):
    if not path:
        return None
    return route_by_path.get(path)


def _line_point_distance(point, coords):
    from apps.network_map.kmz_topology import project_on_segment

    best = float("inf")
    for index in range(len(coords) - 1):
        _projected, _t, current = project_on_segment(point, coords[index], coords[index + 1])
        best = min(best, current)
    return best


def _nearest_cable(point, imported_cables, exclude_source_id=None):
    candidates = [
        row
        for row in imported_cables
        if not exclude_source_id or row["source_id"] != exclude_source_id
    ]
    if not candidates:
        return None, float("inf")
    selected = min(candidates, key=lambda row: _line_point_distance(point, row["coordinates"]))
    return selected, _line_point_distance(point, selected["coordinates"])


def _line_midpoint(coords):
    if not coords:
        return (0, 0)
    total = sum(distance_m(coords[index], coords[index + 1]) for index in range(len(coords) - 1))
    if total <= 0:
        return coords[0]
    target = total / 2
    passed = 0.0
    for index in range(len(coords) - 1):
        segment = distance_m(coords[index], coords[index + 1])
        if passed + segment >= target:
            ratio = (target - passed) / segment if segment else 0
            a, b = coords[index], coords[index + 1]
            return (a[0] + (b[0] - a[0]) * ratio, a[1] + (b[1] - a[1]) * ratio)
        passed += segment
    return coords[-1]


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def execute_kmz_import(request, project_id):
    project, error = _project_for_edit(request, project_id)
    if error:
        return error
    upload = request.FILES.get("file")
    decisions, error = _load_decisions(request)
    if error:
        return error
    if not upload:
        return JsonResponse({"success": False, "error": "Envie o KML/KMZ."}, status=400)

    try:
        raw, analyzer, analysis = _read_upload_and_analysis(upload)
        errors = validate_decisions(analysis, decisions, require_preview=True)
        file_hash = hashlib.sha256(raw).hexdigest()
        expected_token = preview_token(file_hash, decisions)
        if decisions.get("preview_token") != expected_token:
            errors.append("A prévia não corresponde mais às decisões atuais. Gere a prévia novamente.")
        if errors:
            return JsonResponse(
                {"success": False, "error": "Importação bloqueada.", "errors": errors},
                status=409,
            )
        plan = build_topology_plan(analysis, decisions)
        selected_routes = set(decisions.get("routes") or [])
        naming = decisions.get("naming") or {}
        project_prefix = _safe_prefix(naming.get("project_prefix") or project.code or project.name)
        preserve_names = bool(naming.get("preserve_source_names", True))
        counts = defaultdict(int)
        warnings = []

        with transaction.atomic():
            batch = KMZImportBatch.objects.create(
                project=project,
                user=request.user,
                filename=getattr(upload, "name", "import.kmz"),
                file_sha256=file_hash,
                preview_token=expected_token,
                status=KMZImportBatch.Status.PREVIEW,
                decisions=canonical_decisions(decisions),
            )

            route_by_path = {}
            for path in sorted(selected_routes):
                leaf = path.split(" / ")[-1]
                base = f"{project_prefix}-{route_slug(leaf)}"
                route = NetworkRoute.objects.create(
                    project=project,
                    company=project.company,
                    name=leaf,
                    code=_unique_route_code(project.company_id, base),
                    geometry=None,
                )
                route_by_path[path] = route
                _track(batch, route, "network_route", metadata={"source_folder": path})
                counts["routes"] += 1

            point_by_source = {}
            point_sequence = Counter()
            for point in plan["points"]:
                target = point["target_type"]
                if target in {"ignore", "technical_reserve"}:
                    if target == "ignore":
                        counts["ignored_points"] += 1
                    continue
                route = _route_object_for_path(route_by_path, point.get("route_path"))
                route_code = (
                    route_slug(point["route_path"].split(" / ")[-1])
                    if point.get("route_path")
                    else "SEM-ROTA"
                )
                rule = point["rule"]
                subtype = rule.get("subtype") or point.get("subtype_hint")
                prefix_by_type = {
                    "cto": "CTO",
                    "splice_box": "CDO" if subtype == "cdo" else "CEO",
                    "dio": "DIO",
                    "pop": "POP",
                    "olt": "OLT",
                    "pole": "POSTE",
                    "rack": "RACK",
                    "tower": "TORRE",
                    "other": "EQP",
                }
                prefix = prefix_by_type.get(target, "EQP")
                point_sequence[(prefix, route_code)] += 1
                base_code = f"{prefix}-{project_prefix}-{route_code}-{point_sequence[(prefix, route_code)]:03d}"
                code = _unique_element_code(project.id, base_code)
                object_name = point["name"] if preserve_names else code
                metadata = {
                    "kmz_batch_id": batch.pk,
                    "kmz_source_id": point["source_id"],
                    "kmz_folder": point.get("folder") or "",
                    "kmz_original_name": point["name"],
                    "kmz_standard_code": code,
                    "import_subtype": subtype or target,
                }
                geo_point = Point(*point["coordinates"], srid=4326)
                if target == "cto":
                    obj = CTO.objects.create(
                        project=project,
                        company=project.company,
                        name=object_name,
                        code=code,
                        element_type=NetworkElement.ElementType.CTO,
                        point=geo_point,
                        capacity=int(rule.get("capacity") or 16),
                        route=route,
                        metadata=metadata,
                    )
                    _track(batch, obj, "cto", point)
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
                    if target == "dio":
                        metadata["port_capacity"] = int(rule.get("port_capacity") or 24)
                    obj = NetworkElement.objects.create(
                        project=project,
                        company=project.company,
                        name=object_name,
                        code=code,
                        element_type=type_map.get(target, NetworkElement.ElementType.OTHER),
                        point=geo_point,
                        metadata=metadata,
                    )
                    _track(batch, obj, "network_element", point)
                    counts["elements"] += 1
                point_by_source[point["source_id"]] = obj

            imported_cables = []
            for cable_plan in plan["cables"]:
                rule = effective_line_rule(
                    next(line for line in analysis["lines"] if line["source_id"] == cable_plan["source_id"]),
                    decisions,
                )
                route = _route_object_for_path(route_by_path, cable_plan.get("route_path"))
                code = _unique_cable_code(
                    project.id,
                    cable_plan["proposed_code"].replace("{PROJECT}", project_prefix),
                )
                cable_model = _resolve_cable_model(
                    project.company_id,
                    cable_plan["fiber_count"],
                    rule.get("cable_model_id"),
                )
                cable = FiberCable.objects.create(
                    project=project,
                    company=project.company,
                    name=code,
                    code=code,
                    cable_type=cable_plan["cable_type"],
                    cable_model=cable_model,
                    geometry=MultiLineString(
                        LineString(cable_plan["coordinates"], srid=4326), srid=4326
                    ),
                    fiber_count=cable_plan["fiber_count"],
                    origin=point_by_source.get(cable_plan.get("origin_source_id")),
                    destination=point_by_source.get(cable_plan.get("destination_source_id")),
                    route=route,
                )
                _track(
                    batch,
                    cable,
                    "fiber_cable",
                    {
                        "source_id": cable_plan["source_id"],
                        "name": cable_plan["source_name"],
                        "folder": cable_plan["source_folder"],
                    },
                    metadata={
                        "original_name": cable_plan["source_name"],
                        "route_path": cable_plan.get("route_path"),
                        "length_m": cable_plan["length_m"],
                    },
                )
                imported_cables.append(
                    {
                        "object": cable,
                        "source_id": cable_plan["source_id"],
                        "coordinates": cable_plan["coordinates"],
                        "origin_source_id": cable_plan.get("origin_source_id"),
                        "destination_source_id": cable_plan.get("destination_source_id"),
                    }
                )
                if cable_model is None:
                    warnings.append(
                        f"{code}: não existe CableModel de {cable_plan['fiber_count']} fibras; "
                        "as fibras internas não serão geradas automaticamente."
                    )
                counts["cables"] += 1

            # Registra passagem e as decisões de corte/conexão nos segmentos afetados.
            for junction in plan["junctions"]:
                if junction["action"] == "ignore":
                    continue
                element = point_by_source.get(junction["point_source_id"])
                if not element:
                    continue
                related = [
                    row
                    for row in imported_cables
                    if row["source_id"] == junction["line_source_id"]
                    and (
                        junction["action"] == "pass"
                        or row.get("origin_source_id") == junction["point_source_id"]
                        or row.get("destination_source_id") == junction["point_source_id"]
                    )
                ]
                if junction["action"] == "pass" and related:
                    related = [
                        min(
                            related,
                            key=lambda row: _line_point_distance(
                                tuple(junction["projected"]), row["coordinates"]
                            ),
                        )
                    ]
                for sequence, row in enumerate(related, 1):
                    action = junction["action"]
                    passage = CableElementPassage.objects.create(
                        cable=row["object"],
                        element=element,
                        action=action,
                        sequence=sequence,
                        position_m=junction["position_m"],
                        distance_m=junction["distance_m"],
                        metadata={
                            "kmz_batch_id": batch.pk,
                            "junction_id": junction["junction_id"],
                            "source_line": junction["line_name"],
                        },
                    )
                    _track(batch, passage, "cable_element_passage")
                    counts["cable_relations"] += 1

            max_reserve_distance = float(decisions.get("reserve_max_distance_m") or 150)
            for point in plan["reserve_points"]:
                nearest, distance = _nearest_cable(tuple(point["coordinates"]), imported_cables)
                if not nearest or distance > max_reserve_distance:
                    warnings.append(
                        f"RT {point['name']}: nenhum cabo até {max_reserve_distance:.0f} m; não criada."
                    )
                    counts["skipped_reserves"] += 1
                    continue
                length = float(
                    point["rule"].get("length_m") or point.get("length_hint_m") or 20
                )
                reserve = CableReserve.objects.create(
                    cable=nearest["object"],
                    point=Point(*point["coordinates"], srid=4326),
                    length_m=length,
                    label=point["name"],
                    notes=f"KMZ lote {batch.pk}; distância ao cabo {distance:.1f} m",
                )
                _track(batch, reserve, "cable_reserve", point)
                counts["reserves"] += 1

            line_by_id = {line["source_id"]: line for line in analysis["lines"]}
            for line in plan["reserve_lines"]:
                midpoint = _line_midpoint([tuple(value) for value in line["coordinates"]])
                nearest, distance = _nearest_cable(
                    midpoint, imported_cables, exclude_source_id=line["source_id"]
                )
                if not nearest or distance > max_reserve_distance:
                    warnings.append(
                        f"Reserva desenhada {line['name']}: nenhum cabo até {max_reserve_distance:.0f} m."
                    )
                    counts["skipped_reserves"] += 1
                    continue
                source = line_by_id[line["source_id"]]
                rule = effective_line_rule(source, decisions)
                length = float(
                    rule.get("length_m")
                    or line.get("length_hint_m")
                    or line.get("length_m")
                    or 20
                )
                reserve = CableReserve.objects.create(
                    cable=nearest["object"],
                    point=Point(*midpoint, srid=4326),
                    length_m=length,
                    label=line["name"],
                    notes=f"Reserva em linha; KMZ lote {batch.pk}; distância {distance:.1f} m",
                )
                _track(batch, reserve, "cable_reserve", source)
                counts["reserves"] += 1

            # Linhas explicitamente classificadas como rota continuam disponíveis.
            for line in plan["lines"]:
                if line["action"] != "route":
                    continue
                route = NetworkRoute.objects.create(
                    project=project,
                    company=project.company,
                    name=line["name"],
                    code=_unique_route_code(
                        project.company_id,
                        f"{project_prefix}-TRACADO-{uuid.uuid4().hex[:6].upper()}",
                    ),
                    geometry=MultiLineString(
                        LineString(line["coordinates"], srid=4326), srid=4326
                    ),
                )
                _track(batch, route, "network_route", line)
                counts["route_lines"] += 1

            batch.status = KMZImportBatch.Status.IMPORTED
            batch.summary = dict(counts)
            batch.warning_messages = warnings
            batch.save(
                update_fields=[
                    "status",
                    "summary",
                    "warning_messages",
                    "updated_at",
                ]
            )

        return JsonResponse(
            {
                "success": True,
                "batch_id": batch.pk,
                "imported": dict(counts),
                "warnings": warnings,
            }
        )
    except (ValueError, TypeError, StopIteration) as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def kmz_import_batches(request, project_id):
    project, error = _project_for_edit(request, project_id)
    if error:
        return error
    batches = list(
        KMZImportBatch.objects.filter(project=project)
        .select_related("user")[:30]
    )
    return JsonResponse(
        {
            "success": True,
            "batches": [
                {
                    "id": batch.pk,
                    "filename": batch.filename,
                    "status": batch.status,
                    "status_label": batch.get_status_display(),
                    "created_at": batch.created_at.isoformat(),
                    "user": batch.user.get_username() if batch.user else None,
                    "summary": batch.summary,
                    "warnings": batch.warning_messages,
                }
                for batch in batches
            ],
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def undo_kmz_import(request, project_id, batch_id):
    project, error = _project_for_edit(request, project_id)
    if error:
        return error
    batch = get_object_or_404(KMZImportBatch, pk=batch_id, project=project)
    if batch.status != KMZImportBatch.Status.IMPORTED:
        return JsonResponse(
            {"success": False, "error": "Esse lote não está em estado importado."},
            status=409,
        )
    deleted = defaultdict(int)
    with transaction.atomic():
        for object_type in [
            "cable_element_passage",
            "cable_reserve",
            "fiber_cable",
            "cto",
            "network_element",
            "network_route",
        ]:
            model = OBJECT_MODELS[object_type]
            ids = list(
                batch.objects.filter(object_type=object_type).values_list(
                    "object_id", flat=True
                )
            )
            count, _details = model.objects.filter(pk__in=ids).delete()
            deleted[object_type] += count
        batch.status = KMZImportBatch.Status.UNDONE
        batch.save(update_fields=["status", "updated_at"])
    return JsonResponse({"success": True, "deleted": dict(deleted)})


def _legacy_candidate_querysets(project):
    elements = NetworkElement.objects.filter(project=project).filter(
        Q(code__startswith="KMZ-")
        | Q(code__startswith="IMP-")
        | Q(metadata__has_key="kmz_source_id")
        | Q(metadata__has_key="kmz_original_name")
    )
    cables = FiberCable.objects.filter(project=project).filter(
        Q(code__startswith="KMZ-") | Q(code__startswith="IMP-")
    )
    routes = NetworkRoute.objects.filter(project=project).filter(
        Q(code__startswith="KMZ-") | Q(code__startswith="KML-")
    )
    reserves = CableReserve.objects.filter(cable__project=project).filter(
        Q(cable__in=cables) | Q(notes__icontains="Importado do KMZ")
    )
    return elements, cables, routes, reserves


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def cleanup_legacy_kmz_import(request, project_id):
    project, error = _project_for_edit(request, project_id)
    if error:
        return error
    elements, cables, routes, reserves = _legacy_candidate_querysets(project)
    counts = {
        "elements": elements.count(),
        "cables": cables.count(),
        "routes": routes.count(),
        "reserves": reserves.count(),
    }
    candidate_hash = hashlib.sha256(
        json.dumps(counts, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    if request.method == "GET":
        return JsonResponse(
            {
                "success": True,
                "candidates": counts,
                "candidate_hash": candidate_hash,
                "confirmation": f"LIMPAR {project.code}",
                "warning": "A limpeza considera somente códigos/metadata criados pelos importadores antigos.",
            }
        )
    confirmation = str(request.data.get("confirmation") or "")
    if confirmation != f"LIMPAR {project.code}":
        return JsonResponse(
            {
                "success": False,
                "error": f"Digite LIMPAR {project.code} para confirmar.",
            },
            status=400,
        )
    if str(request.data.get("candidate_hash") or "") != candidate_hash:
        return JsonResponse(
            {
                "success": False,
                "error": "A lista de candidatos mudou. Atualize a prévia da limpeza.",
            },
            status=409,
        )
    deleted = {}
    with transaction.atomic():
        deleted["reserves"] = reserves.delete()[0]
        deleted["cables"] = cables.delete()[0]
        deleted["elements"] = elements.delete()[0]
        deleted["routes"] = routes.delete()[0]
    return JsonResponse({"success": True, "deleted": deleted})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def element_cable_topology(request, element_id):
    """Mostra cabos de entrada, saída e passagem de CTO/CEO/CDO.

    O endpoint também funciona para outros NetworkElement e é útil no detalhe
    do mapa depois da importação. Ele não altera a rede.
    """
    element = get_object_or_404(NetworkElement, pk=element_id)
    if not can_view_company(request.user, element.company_id):
        return JsonResponse({"success": False, "error": "Elemento não disponível."}, status=403)

    incoming = list(
        element.incoming_cables.select_related("route").order_by("name")
    )
    outgoing = list(
        element.outgoing_cables.select_related("route").order_by("name")
    )
    passages = list(
        element.cable_passages.select_related("cable", "cable__route").order_by(
            "cable__name", "sequence"
        )
    )

    def cable_payload(cable, relation):
        return {
            "id": cable.pk,
            "name": cable.name,
            "code": cable.code,
            "fiber_count": cable.fiber_count,
            "cable_type": cable.cable_type,
            "route_id": cable.route_id,
            "route_name": cable.route.name if cable.route else None,
            "relation": relation,
        }

    result = {
        "incoming": [cable_payload(cable, "incoming") for cable in incoming],
        "outgoing": [cable_payload(cable, "outgoing") for cable in outgoing],
        "passages": [
            {
                **cable_payload(item.cable, item.action),
                "passage_id": item.pk,
                "action": item.action,
                "action_label": item.get_action_display(),
                "position_m": float(item.position_m) if item.position_m is not None else None,
                "distance_m": float(item.distance_m),
            }
            for item in passages
        ],
    }
    return JsonResponse(
        {
            "success": True,
            "element": {
                "id": element.pk,
                "name": element.name,
                "code": element.code,
                "type": element.element_type,
                "subtype": element.metadata.get("import_subtype"),
            },
            "connections": result,
            "counts": {key: len(value) for key, value in result.items()},
        }
    )
