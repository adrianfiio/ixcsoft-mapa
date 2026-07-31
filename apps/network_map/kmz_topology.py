from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

from apps.network_map.kmz_import import normalize

PENDING_VALUES = {None, "", "review", "unknown", "ask", "pending"}
JUNCTION_ACTIONS = {"connect", "cut", "pass", "branch", "ignore"}


def distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = a
    lon2, lat2 = b
    dx = (lon2 - lon1) * 111320 * math.cos(math.radians((lat1 + lat2) / 2))
    dy = (lat2 - lat1) * 110540
    return math.hypot(dx, dy)


def project_on_segment(
    point: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
) -> tuple[tuple[float, float], float, float]:
    px, py = point
    ax, ay = a
    bx, by = b
    vx, vy = bx - ax, by - ay
    denom = vx * vx + vy * vy
    t = 0.0 if denom == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / denom))
    projected = (ax + t * vx, ay + t * vy)
    return projected, t, distance_m(point, projected)


def polyline_length_m(coords: Iterable[tuple[float, float]]) -> float:
    values = list(coords)
    return sum(distance_m(values[index - 1], values[index]) for index in range(1, len(values)))


def route_slug(value: str) -> str:
    normalized = normalize(value).upper()
    result = []
    for char in normalized:
        if char.isalnum():
            result.append(char)
        elif result and result[-1] != "-":
            result.append("-")
    return "".join(result).strip("-") or "SEM-ROTA"


def canonical_decisions(decisions: dict) -> dict:
    """Remove campos de estado da prévia para gerar um token reproduzível."""
    copied = json.loads(json.dumps(decisions or {}, sort_keys=True, default=str))
    copied.pop("preview_token", None)
    copied.pop("preview_generated_at", None)
    return copied


def preview_token(file_sha256: str, decisions: dict) -> str:
    payload = json.dumps(canonical_decisions(decisions), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{file_sha256}:{payload}".encode("utf-8")).hexdigest()


def point_group_key(classification: dict) -> str:
    reason = classification.get("reason") or "unknown"
    if reason == "unknown":
        return f"prefix:{classification.get('prefix') or 'SEM_PREFIXO'}"
    return reason


def effective_point_rule(point_record: dict, decisions: dict) -> dict:
    item_rule = (decisions.get("point_items") or {}).get(point_record["source_id"])
    if item_rule:
        return item_rule
    return (decisions.get("point_groups") or {}).get(point_record["group_key"], {})


def effective_line_rule(line_record: dict, decisions: dict) -> dict:
    item_rule = (decisions.get("line_items") or {}).get(line_record["source_id"])
    if item_rule:
        return item_rule
    return (decisions.get("line_groups") or {}).get(line_record["group_key"], {})


def route_for_folder(selected_routes: set[str], folder: str) -> str | None:
    matches = [path for path in selected_routes if folder == path or folder.startswith(path + " / ")]
    return max(matches, key=len) if matches else None


def resolved_points(analysis: dict, decisions: dict) -> list[dict]:
    selected_routes = set(decisions.get("routes") or [])
    result = []
    for point in analysis.get("points", []):
        rule = effective_point_rule(point, decisions)
        target = rule.get("type") or "review"
        route_path = route_for_folder(selected_routes, point.get("folder") or "")
        result.append({**point, "rule": rule, "target_type": target, "route_path": route_path})
    return result


def resolved_lines(analysis: dict, decisions: dict) -> list[dict]:
    result = []
    for line in analysis.get("lines", []):
        rule = effective_line_rule(line, decisions)
        result.append({**line, "rule": rule, "action": rule.get("action") or "review"})
    return result


def validate_decisions(analysis: dict, decisions: dict, require_preview: bool = True) -> list[str]:
    errors: list[str] = []
    for line in resolved_lines(analysis, decisions):
        action = line["action"]
        if action in PENDING_VALUES:
            errors.append(f"Linha “{line['name']}” ainda está em Revisar.")
            continue
        if action == "cable":
            if not line["rule"].get("fiber_count"):
                errors.append(f"Cabo “{line['name']}” não possui quantidade de fibras.")
            if not line["rule"].get("cable_type"):
                errors.append(f"Cabo “{line['name']}” não possui tipo de cabo.")
        if action == "reserve_line" and not (
            line["rule"].get("length_m") or line.get("length_hint_m") or line.get("length_m")
        ):
            errors.append(f"Reserva em linha “{line['name']}” não possui metragem.")

    for point in resolved_points(analysis, decisions):
        target = point["target_type"]
        if target in PENDING_VALUES:
            errors.append(f"Ponto “{point['name']}” ainda está em Revisar.")
            continue
        rule = point["rule"]
        if target == "cto" and not rule.get("capacity"):
            errors.append(f"CTO “{point['name']}” não possui quantidade de portas.")
        if target == "technical_reserve" and not (
            rule.get("length_m") or point.get("length_hint_m")
        ):
            errors.append(f"Reserva “{point['name']}” não possui metragem.")
        if target == "dio" and not rule.get("port_capacity"):
            errors.append(f"DIO “{point['name']}” não possui capacidade de portas.")

    if require_preview and not decisions.get("preview_token"):
        errors.append("A prévia topológica ainda não foi gerada.")
    return errors


def _nearest_projection(
    point: tuple[float, float], coords: list[tuple[float, float]]
) -> dict | None:
    if len(coords) < 2:
        return None
    segment_lengths = [distance_m(coords[index], coords[index + 1]) for index in range(len(coords) - 1)]
    passed = 0.0
    best = None
    for index, segment_length in enumerate(segment_lengths):
        projected, t, distance = project_on_segment(point, coords[index], coords[index + 1])
        position = passed + segment_length * t
        candidate = {
            "segment": index,
            "t": t,
            "projected": projected,
            "distance_m": distance,
            "position_m": position,
            "total_length_m": sum(segment_lengths),
        }
        if best is None or distance < best["distance_m"]:
            best = candidate
        passed += segment_length
    return best


def _junction_id(line_source_id: str, point_source_id: str) -> str:
    return hashlib.sha1(f"{line_source_id}:{point_source_id}".encode("utf-8")).hexdigest()[:16]


def detect_junctions(
    analysis: dict,
    decisions: dict,
    proximity_m: float = 12.0,
    endpoint_tolerance_m: float = 18.0,
) -> list[dict]:
    points = [
        point
        for point in resolved_points(analysis, decisions)
        if point["target_type"] in {"cto", "splice_box", "pop", "dio", "olt", "other"}
    ]
    lines = [line for line in resolved_lines(analysis, decisions) if line["action"] == "cable"]
    overrides = decisions.get("junctions") or {}
    defaults = decisions.get("topology_defaults") or {
        "cto": "cut",
        "splice_box": "cut",
        "pop": "connect",
        "dio": "connect",
        "olt": "connect",
        "other": "pass",
    }
    result: list[dict] = []
    for line in lines:
        for point in points:
            nearest = _nearest_projection(tuple(point["coordinates"]), [tuple(value) for value in line["coordinates"]])
            if nearest is None or nearest["distance_m"] > proximity_m:
                continue
            endpoint = (
                nearest["position_m"] <= endpoint_tolerance_m
                or nearest["total_length_m"] - nearest["position_m"] <= endpoint_tolerance_m
            )
            suggested = "connect" if endpoint else defaults.get(point["target_type"], "pass")
            junction_id = _junction_id(line["source_id"], point["source_id"])
            selected = (overrides.get(junction_id) or {}).get("action") or suggested
            if selected not in JUNCTION_ACTIONS:
                selected = suggested
            result.append(
                {
                    "junction_id": junction_id,
                    "line_source_id": line["source_id"],
                    "line_name": line["name"],
                    "line_group_key": line["group_key"],
                    "point_source_id": point["source_id"],
                    "point_name": point["name"],
                    "point_type": point["target_type"],
                    "point_route_path": point.get("route_path"),
                    "distance_m": round(nearest["distance_m"], 2),
                    "position_m": round(nearest["position_m"], 2),
                    "total_length_m": round(nearest["total_length_m"], 2),
                    "segment": nearest["segment"],
                    "t": nearest["t"],
                    "projected": nearest["projected"],
                    "is_endpoint": endpoint,
                    "suggested_action": suggested,
                    "action": selected,
                }
            )
    return sorted(result, key=lambda item: (item["line_source_id"], item["position_m"], item["point_name"]))


def _deduplicate_cuts(junctions: list[dict], minimum_spacing_m: float = 1.0) -> list[dict]:
    output: list[dict] = []
    for item in sorted(junctions, key=lambda row: row["position_m"]):
        if item["action"] not in {"cut", "branch"}:
            continue
        if output and abs(item["position_m"] - output[-1]["position_m"]) < minimum_spacing_m:
            # Prefere a caixa em vez de um elemento genérico quando há sobreposição.
            priority = {"splice_box": 4, "cto": 3, "pop": 2, "dio": 2, "olt": 2, "other": 1}
            if priority.get(item["point_type"], 0) > priority.get(output[-1]["point_type"], 0):
                output[-1] = item
        else:
            output.append(item)
    return output


def split_coordinates(
    coords: list[tuple[float, float]],
    cuts: list[dict],
) -> list[dict]:
    """Divide uma LineString e devolve segmentos com os nós de início/fim."""
    if len(coords) < 2:
        return []
    cuts = _deduplicate_cuts(cuts)
    by_segment: dict[int, list[dict]] = defaultdict(list)
    for cut in cuts:
        by_segment[int(cut["segment"])].append(cut)

    parts: list[dict] = []
    current = [coords[0]]
    start_node = None
    for index in range(len(coords) - 1):
        for cut in sorted(by_segment.get(index, []), key=lambda value: value["t"]):
            projected = tuple(cut["projected"])
            if current[-1] != projected:
                current.append(projected)
            if len(current) >= 2 and polyline_length_m(current) >= 0.5:
                parts.append(
                    {
                        "coordinates": current,
                        "origin_junction": start_node,
                        "destination_junction": cut,
                    }
                )
            current = [projected]
            start_node = cut
        current.append(coords[index + 1])
    if len(current) >= 2 and polyline_length_m(current) >= 0.5:
        parts.append(
            {
                "coordinates": current,
                "origin_junction": start_node,
                "destination_junction": None,
            }
        )
    return parts


def infer_line_route(line: dict, junctions: list[dict], selected_routes: set[str]) -> str | None:
    direct = route_for_folder(selected_routes, line.get("folder") or "")
    if direct:
        return direct
    votes = Counter(
        item["point_route_path"]
        for item in junctions
        if item.get("point_route_path") and item["action"] != "ignore"
    )
    return votes.most_common(1)[0][0] if votes else None


def build_topology_plan(analysis: dict, decisions: dict) -> dict:
    proximity = float((decisions.get("topology") or {}).get("proximity_m") or 12)
    endpoint_tolerance = float((decisions.get("topology") or {}).get("endpoint_tolerance_m") or 18)
    junctions = detect_junctions(analysis, decisions, proximity, endpoint_tolerance)
    selected_routes = set(decisions.get("routes") or [])
    points = resolved_points(analysis, decisions)
    lines = resolved_lines(analysis, decisions)
    point_by_id = {point["source_id"]: point for point in points}

    cable_plans = []
    route_sequences = Counter()
    for line in lines:
        if line["action"] != "cable":
            continue
        line_junctions = [item for item in junctions if item["line_source_id"] == line["source_id"]]
        line_route_path = infer_line_route(line, line_junctions, selected_routes)
        pieces = split_coordinates([tuple(value) for value in line["coordinates"]], line_junctions)
        if not pieces:
            pieces = [{"coordinates": line["coordinates"], "origin_junction": None, "destination_junction": None}]
        connect_items = [item for item in line_junctions if item["action"] == "connect"]
        start_connect = min(connect_items, key=lambda item: item["position_m"], default=None)
        end_connect = max(connect_items, key=lambda item: item["position_m"], default=None)
        for piece_index, piece in enumerate(pieces):
            origin_junction = piece["origin_junction"]
            destination_junction = piece["destination_junction"]
            origin_route = point_by_id.get(origin_junction["point_source_id"], {}).get("route_path") if origin_junction else None
            destination_route = point_by_id.get(destination_junction["point_source_id"], {}).get("route_path") if destination_junction else None
            if origin_route and destination_route and origin_route == destination_route:
                route_path = origin_route
            else:
                route_path = origin_route or destination_route or line_route_path
            route_key = route_slug(route_path.split(" / ")[-1]) if route_path else "SEM-ROTA"
            route_sequences[route_key] += 1
            cable_type = line["rule"].get("cable_type") or line.get("cable_type_hint") or "distribution"
            prefix = "DROP" if cable_type == "drop" else "CAB"
            proposed_code = f"{prefix}-{{PROJECT}}-{route_key}-{route_sequences[route_key]:03d}"
            if piece_index == 0 and origin_junction is None and start_connect:
                origin_junction = start_connect
            if piece_index == len(pieces) - 1 and destination_junction is None and end_connect:
                destination_junction = end_connect
            origin_id = origin_junction["point_source_id"] if origin_junction else None
            destination_id = destination_junction["point_source_id"] if destination_junction else None
            cable_plans.append(
                {
                    "source_id": line["source_id"],
                    "source_name": line["name"],
                    "source_folder": line.get("folder") or "",
                    "group_key": line["group_key"],
                    "coordinates": piece["coordinates"],
                    "length_m": round(polyline_length_m(piece["coordinates"]), 2),
                    "fiber_count": int(line["rule"].get("fiber_count") or line.get("fiber_count_hint") or 1),
                    "cable_type": cable_type,
                    "route_path": route_path,
                    "proposed_code": proposed_code,
                    "origin_source_id": origin_id,
                    "destination_source_id": destination_id,
                    "origin_name": point_by_id.get(origin_id, {}).get("name") if origin_id else None,
                    "destination_name": point_by_id.get(destination_id, {}).get("name") if destination_id else None,
                }
            )

    passages = [item for item in junctions if item["action"] == "pass"]
    ignored_junctions = [item for item in junctions if item["action"] == "ignore"]
    reserve_points = [point for point in points if point["target_type"] == "technical_reserve"]
    reserve_lines = [line for line in lines if line["action"] == "reserve_line"]

    return {
        "junctions": junctions,
        "cables": cable_plans,
        "passages": passages,
        "ignored_junctions": ignored_junctions,
        "reserve_points": reserve_points,
        "reserve_lines": reserve_lines,
        "points": points,
        "lines": lines,
        "summary": {
            "cables": len(cable_plans),
            "junctions": len(junctions),
            "cuts": sum(item["action"] == "cut" for item in junctions),
            "branches": sum(item["action"] == "branch" for item in junctions),
            "passes": len(passages),
            "connected_endpoints": sum(item["action"] == "connect" for item in junctions),
            "reserve_points": len(reserve_points),
            "reserve_lines": len(reserve_lines),
        },
    }
