from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Iterable

from django.db.models import Prefetch, Q

from apps.network_map.kmz_import_models import CableElementPassage
from apps.network_map.models import (
    ContainerEquipment,
    ContainerPortLink,
    FiberCable,
    FiberSplice,
    SpliceTraySplitterPort,
    NetworkElement,
    NetworkProject,
    NetworkRoute,
)


SOURCE_EQUIPMENT_TYPES = {"olt", "dio"}
BOX_TYPES = {"cto", "splice_box"}
CONTAINER_TYPES = {"rack", "tower"}


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    cable_id: int | None = None
    link_id: int | None = None
    label: str = ""
    kind: str = "fiber"


def _element_subtype(element: NetworkElement) -> str:
    metadata = element.metadata or {}
    return str(
        metadata.get("element_subtype")
        or metadata.get("import_subtype")
        or metadata.get("subtype")
        or ""
    ).strip().lower()


def _is_source_element(element: NetworkElement, equipment_types: set[str]) -> bool:
    subtype = _element_subtype(element)
    if subtype in {"cpd", "pop"} and equipment_types & SOURCE_EQUIPMENT_TYPES:
        return True
    if element.element_type in CONTAINER_TYPES and equipment_types & SOURCE_EQUIPMENT_TYPES:
        return True
    if element.element_type in {"olt", "dio"}:
        return True
    return False


def _route_name(route: NetworkRoute) -> str:
    return route.name or route.code or f"Rota {route.pk}"


def _ordered_cable_elements(cable: FiberCable, passages: Iterable[CableElementPassage]) -> list[int]:
    rows: list[tuple[int, float, int]] = []
    if cable.origin_id:
        rows.append((0, -1.0, cable.origin_id))
    for passage in passages:
        rows.append((1, float(passage.sequence or 0), passage.element_id))
    if cable.destination_id:
        rows.append((2, 10**12, cable.destination_id))
    rows.sort(key=lambda item: (item[0], item[1], item[2]))
    result: list[int] = []
    for _group, _sequence, element_id in rows:
        if not result or result[-1] != element_id:
            result.append(element_id)
    return result


def project_route_topology(project: NetworkProject) -> dict[str, Any]:
    routes = list(
        NetworkRoute.objects.filter(project=project, enabled=True).order_by("name", "code")
    )
    route_ids = [route.id for route in routes]
    cables = list(
        FiberCable.objects.filter(project=project, route_id__in=route_ids)
        .select_related("route", "origin", "destination", "cable_model")
        .order_by("route_id", "name")
    )
    cable_ids = [cable.id for cable in cables]
    passages = list(
        CableElementPassage.objects.filter(cable_id__in=cable_ids)
        .select_related("element", "cable")
        .order_by("cable_id", "sequence", "id")
    )
    passages_by_cable: dict[int, list[CableElementPassage]] = defaultdict(list)
    for passage in passages:
        passages_by_cable[passage.cable_id].append(passage)

    element_ids: set[int] = set()
    for cable in cables:
        if cable.origin_id:
            element_ids.add(cable.origin_id)
        if cable.destination_id:
            element_ids.add(cable.destination_id)
    element_ids.update(passage.element_id for passage in passages)

    equipment_qs = ContainerEquipment.objects.filter(enabled=True).only(
        "id", "container_id", "equipment_type", "name"
    )
    elements = list(
        NetworkElement.objects.filter(project=project, id__in=element_ids, enabled=True)
        .prefetch_related(Prefetch("internal_equipments", queryset=equipment_qs))
    )
    elements_by_id = {element.id: element for element in elements}
    equipment_types_by_element = {
        element.id: {item.equipment_type for item in element.internal_equipments.all()}
        for element in elements
    }

    cables_by_route: dict[int, list[FiberCable]] = defaultdict(list)
    for cable in cables:
        cables_by_route[cable.route_id].append(cable)

    payload_routes: list[dict[str, Any]] = []
    for route in routes:
        route_cables = cables_by_route.get(route.id, [])
        route_element_ids: set[int] = set()
        route_reserve_ids: list[int] = []
        route_graph: dict[str, set[str]] = defaultdict(set)
        incomplete_cable_ids: list[int] = []
        for cable in route_cables:
            ordered = _ordered_cable_elements(cable, passages_by_cable.get(cable.id, []))
            route_element_ids.update(ordered)
            cable_node = f"cable:{cable.id}"
            if len(set(ordered)) < 2:
                incomplete_cable_ids.append(cable.id)
            for element_id in ordered:
                element_node = f"element:{element_id}"
                route_graph[cable_node].add(element_node)
                route_graph[element_node].add(cable_node)
            route_reserve_ids.extend(cable.reserves.values_list("id", flat=True))

        route_elements = [elements_by_id[element_id] for element_id in route_element_ids if element_id in elements_by_id]
        source_ids = [
            element.id for element in route_elements
            if _is_source_element(element, equipment_types_by_element.get(element.id, set()))
        ]
        box_ids = [element.id for element in route_elements if element.element_type in BOX_TYPES]
        cto_ids = [element.id for element in route_elements if element.element_type == "cto"]
        splice_ids = [element.id for element in route_elements if element.element_type == "splice_box"]
        container_ids = [element.id for element in route_elements if element.element_type in CONTAINER_TYPES]

        # A route is useful only when all cable segments belong to the same
        # connected component that starts at a POP/Rack/Tower with OLT/DIO.
        reachable: set[str] = set()
        queue: deque[str] = deque(f"element:{item}" for item in source_ids)
        while queue:
            node = queue.popleft()
            if node in reachable:
                continue
            reachable.add(node)
            queue.extend(route_graph.get(node, set()) - reachable)
        connected_cable_ids = sorted(
            cable.id for cable in route_cables if f"cable:{cable.id}" in reachable
        )
        connected_box_ids = sorted(
            element_id for element_id in box_ids if f"element:{element_id}" in reachable
        )
        disconnected_cable_ids = sorted(set(cable.id for cable in route_cables) - set(connected_cable_ids))
        valid = bool(
            route_cables
            and source_ids
            and connected_box_ids
            and not incomplete_cable_ids
            and not disconnected_cable_ids
        )
        payload_routes.append({
            "id": route.id,
            "name": _route_name(route),
            "code": route.code,
            "status": route.status,
            "valid": valid,
            "reason": "" if valid else (
                "Sem cabo ligado" if not route_cables
                else "Sem origem OLT/DIO" if not source_ids
                else "Sem CTO/CEO/CDO conectada" if not connected_box_ids
                else "Cabo sem duas pontas" if incomplete_cable_ids
                else "Trechos sem continuidade"
            ),
            "cable_ids": [cable.id for cable in route_cables],
            "element_ids": sorted(route_element_ids),
            "source_ids": sorted(source_ids),
            "cto_ids": sorted(cto_ids),
            "splice_box_ids": sorted(splice_ids),
            "container_ids": sorted(container_ids),
            "reserve_ids": sorted(set(route_reserve_ids)),
            "connected_cable_ids": connected_cable_ids,
            "disconnected_cable_ids": disconnected_cable_ids,
            "incomplete_cable_ids": sorted(incomplete_cable_ids),
            "counts": {
                "cables": len(route_cables),
                "elements": len(route_element_ids),
                "sources": len(source_ids),
                "ctos": len(cto_ids),
                "splice_boxes": len(splice_ids),
                "reserves": len(set(route_reserve_ids)),
            },
        })

    return {
        "project": {"id": project.id, "name": project.name},
        "routes": payload_routes,
        "valid_route_ids": [item["id"] for item in payload_routes if item["valid"]],
    }


def build_project_graph(project: NetworkProject, route_id: int | None = None) -> tuple[dict[str, list[GraphEdge]], dict[str, Any]]:
    cable_filter = Q(project=project)
    if route_id:
        cable_filter &= Q(route_id=route_id)
    cables = list(
        FiberCable.objects.filter(cable_filter)
        .select_related("origin", "destination", "route")
    )
    cable_ids = [cable.id for cable in cables]
    passages = list(
        CableElementPassage.objects.filter(cable_id__in=cable_ids)
        .order_by("cable_id", "sequence", "id")
    )
    passages_by_cable: dict[int, list[CableElementPassage]] = defaultdict(list)
    for passage in passages:
        passages_by_cable[passage.cable_id].append(passage)

    adjacency: dict[str, list[GraphEdge]] = defaultdict(list)
    catalog: dict[str, Any] = {
        "elements": {}, "cables": {}, "fibers": {}, "splitter_ports": {},
        "equipment": {}, "ports": {}, "links": {},
    }

    element_ids: set[int] = set()
    for cable in cables:
        ordered = _ordered_cable_elements(cable, passages_by_cable.get(cable.id, []))
        element_ids.update(ordered)
        catalog["cables"][cable.id] = {
            "id": cable.id,
            "name": cable.name,
            "code": cable.code,
            "route_id": cable.route_id,
            "fiber_count": cable.fiber_count,
            "type": cable.cable_type,
        }
        cable_node = f"cable:{cable.id}"
        for element_id in ordered:
            element_node = f"element:{element_id}"
            edge = GraphEdge(element_node, cable_node, cable_id=cable.id, label=cable.name)
            adjacency[element_node].append(edge)
            adjacency[cable_node].append(GraphEdge(cable_node, element_node, cable_id=cable.id, label=cable.name))

    elements = NetworkElement.objects.filter(project=project, id__in=element_ids)
    for element in elements:
        catalog["elements"][element.id] = {
            "id": element.id,
            "name": element.name,
            "code": element.code,
            "type": element.element_type,
            "subtype": _element_subtype(element),
        }

    # Fiber-level topology: every referenced strand belongs to a cable, splices
    # join two strands and splitter ports distribute one input to an output.
    fiber_ids: set[int] = set()
    splices = list(
        FiberSplice.objects.filter(splice_box__project=project)
        .select_related("input_fiber__cable", "output_fiber__cable", "splice_box")
    )
    for splice in splices:
        fiber_ids.update([splice.input_fiber_id, splice.output_fiber_id])
        source = f"fiber:{splice.input_fiber_id}"
        target = f"fiber:{splice.output_fiber_id}"
        box = f"element:{splice.splice_box_id}"
        adjacency[source].append(GraphEdge(source, target, kind="splice", label=splice.splice_box.name))
        adjacency[target].append(GraphEdge(target, source, kind="splice", label=splice.splice_box.name))
        adjacency[source].append(GraphEdge(source, box, kind="inside_box"))
        adjacency[box].append(GraphEdge(box, source, kind="inside_box"))
        adjacency[target].append(GraphEdge(target, box, kind="inside_box"))
        adjacency[box].append(GraphEdge(box, target, kind="inside_box"))

    splitter_ports = list(
        SpliceTraySplitterPort.objects.filter(splitter__tray__splice_box__project=project)
        .select_related(
            "splitter__input_fiber__cable", "splitter__input_splitter_port",
            "splitter__tray__splice_box", "output_fiber__cable",
        )
    )
    for port in splitter_ports:
        port_node = f"splitter_port:{port.id}"
        box_node = f"element:{port.splitter.tray.splice_box_id}"
        catalog["splitter_ports"][port.id] = {
            "id": port.id, "number": port.number, "ratio": port.splitter.ratio,
            "box": port.splitter.tray.splice_box.name,
        }
        adjacency[port_node].append(GraphEdge(port_node, box_node, kind="inside_box"))
        adjacency[box_node].append(GraphEdge(box_node, port_node, kind="inside_box"))
        if port.splitter.input_fiber_id:
            input_node = f"fiber:{port.splitter.input_fiber_id}"
            fiber_ids.add(port.splitter.input_fiber_id)
            adjacency[input_node].append(GraphEdge(input_node, port_node, kind="splitter"))
            adjacency[port_node].append(GraphEdge(port_node, input_node, kind="splitter"))
        elif port.splitter.input_splitter_port_id:
            input_node = f"splitter_port:{port.splitter.input_splitter_port_id}"
            adjacency[input_node].append(GraphEdge(input_node, port_node, kind="splitter_cascade"))
            adjacency[port_node].append(GraphEdge(port_node, input_node, kind="splitter_cascade"))
        if port.output_fiber_id:
            output_node = f"fiber:{port.output_fiber_id}"
            fiber_ids.add(port.output_fiber_id)
            adjacency[port_node].append(GraphEdge(port_node, output_node, kind="splitter"))
            adjacency[output_node].append(GraphEdge(output_node, port_node, kind="splitter"))

    from apps.network_map.models import FiberStrand
    for fiber in FiberStrand.objects.filter(id__in=fiber_ids).select_related("cable", "color"):
        fiber_node = f"fiber:{fiber.id}"
        cable_node = f"cable:{fiber.cable_id}"
        catalog["fibers"][fiber.id] = {
            "id": fiber.id, "number": fiber.number, "cable_id": fiber.cable_id,
            "cable": fiber.cable.name, "color": fiber.color.name,
            "color_hex": fiber.color.hex_color,
        }
        adjacency[fiber_node].append(GraphEdge(fiber_node, cable_node, cable_id=fiber.cable_id, kind="strand"))
        adjacency[cable_node].append(GraphEdge(cable_node, fiber_node, cable_id=fiber.cable_id, kind="strand"))

    links = (
        ContainerPortLink.objects.filter(container__project=project)
        .select_related(
            "container", "source_port__equipment", "destination_port__equipment",
            "cable", "cable_fiber",
        )
    )
    if route_id:
        links = links.filter(Q(cable__route_id=route_id) | Q(cable__isnull=True))
    for link in links:
        if link.source_port_id:
            source = f"port:{link.source_port_id}"
            catalog["ports"][link.source_port_id] = {
                "id": link.source_port_id,
                "label": link.source_port.label,
                "equipment": link.source_port.equipment.name,
                "equipment_id": link.source_port.equipment_id,
                "type": link.source_port.port_type,
            }
        elif link.cable_fiber_id:
            source = f"fiber:{link.cable_fiber_id}"
        elif link.cable_id:
            source = f"cable:{link.cable_id}"
        else:
            continue
        destination = f"port:{link.destination_port_id}"
        catalog["ports"][link.destination_port_id] = {
            "id": link.destination_port_id,
            "label": link.destination_port.label,
            "equipment": link.destination_port.equipment.name,
            "equipment_id": link.destination_port.equipment_id,
            "type": link.destination_port.port_type,
        }
        catalog["links"][link.id] = {
            "id": link.id,
            "type": link.link_type,
            "loss_db": float(link.loss_db),
            "fiber_id": link.cable_fiber_id,
        }
        edge = GraphEdge(source, destination, cable_id=link.cable_id, link_id=link.id, kind=link.link_type)
        adjacency[source].append(edge)
        adjacency[destination].append(GraphEdge(destination, source, cable_id=link.cable_id, link_id=link.id, kind=link.link_type))

        # Ports belong to equipment, and equipment belongs to a container element.
        for port in (link.source_port, link.destination_port):
            if not port:
                continue
            port_node = f"port:{port.id}"
            equipment_node = f"equipment:{port.equipment_id}"
            catalog["equipment"][port.equipment_id] = {
                "id": port.equipment_id, "name": port.equipment.name,
                "type": port.equipment.equipment_type,
                "container_id": port.equipment.container_id,
            }
            container_node = f"element:{port.equipment.container_id}"
            adjacency[port_node].append(GraphEdge(port_node, equipment_node, kind="internal"))
            adjacency[equipment_node].append(GraphEdge(equipment_node, port_node, kind="internal"))
            adjacency[equipment_node].append(GraphEdge(equipment_node, container_node, kind="internal"))
            adjacency[container_node].append(GraphEdge(container_node, equipment_node, kind="internal"))

    return adjacency, catalog


def shortest_optical_path(
    project: NetworkProject,
    start: str,
    end: str,
    route_id: int | None = None,
) -> dict[str, Any]:
    adjacency, catalog = build_project_graph(project, route_id=route_id)
    queue: deque[str] = deque([start])
    previous: dict[str, tuple[str, GraphEdge] | None] = {start: None}
    while queue:
        node = queue.popleft()
        if node == end:
            break
        for edge in adjacency.get(node, []):
            if edge.target in previous:
                continue
            previous[edge.target] = (node, edge)
            queue.append(edge.target)
    if end not in previous:
        return {"found": False, "nodes": [], "edges": [], "catalog": catalog}

    nodes: list[str] = []
    edges: list[dict[str, Any]] = []
    current = end
    while current != start:
        nodes.append(current)
        prior, edge = previous[current]  # type: ignore[misc]
        edges.append({
            "source": edge.source,
            "target": edge.target,
            "cable_id": edge.cable_id,
            "link_id": edge.link_id,
            "label": edge.label,
            "kind": edge.kind,
        })
        current = prior
    nodes.append(start)
    nodes.reverse()
    edges.reverse()
    return {"found": True, "nodes": nodes, "edges": edges, "catalog": catalog}
