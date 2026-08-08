from __future__ import annotations

import html
import io
import json
import math
import re
import zipfile
from collections import defaultdict, deque
from xml.sax.saxutils import escape as xml_escape

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import scope_company_queryset
from apps.network_map.kmz_import_models import CableElementPassage
from apps.network_map.map_master_topology import project_route_topology
from apps.network_map.models import (
    FiberCable,
    FiberSplice,
    NetworkElement,
    NetworkRoute,
    SpliceTraySplitter,
)


VERSION = "0.78.0"


def _route_for_user(request, route_id: int) -> NetworkRoute:
    return get_object_or_404(
        scope_company_queryset(NetworkRoute.objects, request.user).select_related("project", "company"),
        pk=route_id,
        enabled=True,
    )


def _route_row(route: NetworkRoute) -> dict:
    topology = project_route_topology(route.project)
    return next((item for item in topology.get("routes", []) if item.get("id") == route.id), {
        "id": route.id,
        "name": route.name or route.code or f"Rota {route.id}",
        "cable_ids": [],
        "element_ids": [],
        "reserve_ids": [],
    })


def _safe_filename(value: str, fallback: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "").strip()).strip("-.")
    return value[:100] or fallback


def _geometry_lines(cable: FiberCable):
    geometry = cable.geometry
    if not geometry:
        return []
    if geometry.geom_type == "LineString":
        return [list(geometry.coords)]
    if geometry.geom_type == "MultiLineString":
        return [list(line.coords) for line in geometry]
    return []


def _route_assets(route: NetworkRoute):
    row = _route_row(route)
    cable_ids = list(dict.fromkeys(int(value) for value in row.get("cable_ids", []) if value))
    element_ids = set(int(value) for value in row.get("element_ids", []) if value)
    cables = list(
        FiberCable.objects.filter(project=route.project, id__in=cable_ids)
        .select_related("origin", "destination", "route")
        .prefetch_related("reserves")
        .order_by("name", "id")
    )
    passages = list(
        CableElementPassage.objects.filter(cable_id__in=cable_ids)
        .select_related("element", "cable")
        .order_by("cable_id", "sequence", "id")
    )
    passages_by_cable = defaultdict(list)
    for passage in passages:
        passages_by_cable[passage.cable_id].append(passage)
        element_ids.add(passage.element_id)
    for cable in cables:
        if cable.origin_id:
            element_ids.add(cable.origin_id)
        if cable.destination_id:
            element_ids.add(cable.destination_id)
    elements = list(
        NetworkElement.objects.filter(project=route.project, id__in=element_ids, enabled=True)
        .order_by("name", "id")
    )
    return row, cables, passages_by_cable, elements


def _kml_coordinates(lines) -> str:
    parts = []
    for coords in lines:
        if not coords:
            continue
        values = " ".join(f"{float(lon):.8f},{float(lat):.8f},0" for lon, lat, *_rest in coords)
        parts.append(f"<LineString><tessellate>1</tessellate><coordinates>{values}</coordinates></LineString>")
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return f"<MultiGeometry>{''.join(parts)}</MultiGeometry>"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def route_export_kmz_v078(request, route_id):
    route = _route_for_user(request, route_id)
    row, cables, _passages_by_cable, elements = _route_assets(route)
    route_name = route.name or route.code or f"Rota {route.id}"

    placemarks = []
    for cable in cables:
        geometry = _kml_coordinates(_geometry_lines(cable))
        if not geometry:
            continue
        description = xml_escape(
            f"Cabo: {cable.name}\nCódigo: {cable.code or '-'}\nFibras: {cable.fiber_count}\nTipo: {cable.get_cable_type_display()}"
        )
        placemarks.append(
            f"<Placemark><name>{xml_escape(cable.name)}</name><description>{description}</description>"
            f"<styleUrl>#cable</styleUrl>{geometry}</Placemark>"
        )
    for element in elements:
        if not element.point:
            continue
        metadata = element.metadata or {}
        subtype = str(metadata.get("import_subtype") or metadata.get("subtype") or "").upper()
        label = subtype or element.get_element_type_display()
        description = xml_escape(
            f"{label}: {element.name}\nCódigo: {element.code or '-'}\nDescrição: {element.description or '-'}"
        )
        placemarks.append(
            f"<Placemark><name>{xml_escape(element.name)}</name><description>{description}</description>"
            f"<styleUrl>#node</styleUrl><Point><coordinates>{element.point.x:.8f},{element.point.y:.8f},0</coordinates></Point></Placemark>"
        )

    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<name>{xml_escape(route_name)}</name>
<description>AFService Map {VERSION} · exportação da rota · {len(cables)} cabo(s) · {len(elements)} elemento(s)</description>
<Style id="cable"><LineStyle><color>ffffb52b</color><width>4</width></LineStyle></Style>
<Style id="node"><IconStyle><scale>1.1</scale><Icon><href>http://maps.google.com/mapfiles/kml/paddle/blu-circle.png</href></Icon></IconStyle></Style>
{''.join(placemarks)}
</Document></kml>'''
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("doc.kml", kml.encode("utf-8"))
        archive.writestr(
            "README.txt",
            (
                f"AFService Map {VERSION}\nRota: {route_name}\n"
                f"Cabos: {len(cables)}\nElementos: {len(elements)}\n"
                "O KMZ contém somente os ativos pertencentes à rota selecionada.\n"
            ).encode("utf-8"),
        )
    response = HttpResponse(buffer.getvalue(), content_type="application/vnd.google-earth.kmz")
    response["Content-Disposition"] = f'attachment; filename="{_safe_filename(route_name, f"rota-{route.id}")}.kmz"'
    response["X-AFService-Route-Assets"] = f"{len(cables)} cables; {len(elements)} elements"
    return response


def _ordered_element_ids(cable, passages):
    rows = []
    if cable.origin_id:
        rows.append((0, -1.0, cable.origin_id))
    for passage in passages:
        rows.append((1, float(passage.sequence or 0), passage.element_id))
    if cable.destination_id:
        rows.append((2, 10**12, cable.destination_id))
    rows.sort(key=lambda value: (value[0], value[1], value[2]))
    result = []
    for _group, _seq, element_id in rows:
        if not result or result[-1] != element_id:
            result.append(element_id)
    return result


def _diagram_layout(elements, edges):
    ids = [item.id for item in elements]
    adjacency = defaultdict(set)
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source and target:
            adjacency[source].add(target)
            adjacency[target].add(source)
    indegree_hint = {item.id: 0 for item in elements}
    for edge in edges:
        if edge.get("target") in indegree_hint:
            indegree_hint[edge["target"]] += 1
    starts = [item.id for item in elements if item.element_type in {"rack", "tower"}]
    if not starts:
        starts = sorted(ids, key=lambda value: (indegree_hint.get(value, 0), value))[:1]
    levels = {}
    queue = deque((node, 0) for node in starts)
    while queue:
        node, level = queue.popleft()
        if node in levels and levels[node] <= level:
            continue
        levels[node] = level
        for neighbor in sorted(adjacency.get(node, ())):
            queue.append((neighbor, level + 1))
    fallback = max(levels.values(), default=-1) + 1
    for node in ids:
        if node not in levels:
            levels[node] = fallback
            fallback += 1
    grouped = defaultdict(list)
    for node in ids:
        grouped[levels[node]].append(node)
    positions = {}
    for level, nodes in sorted(grouped.items()):
        nodes.sort()
        for index, node in enumerate(nodes):
            positions[node] = {"x": 130 + level * 300, "y": 110 + index * 145}
    width = max((pos["x"] for pos in positions.values()), default=800) + 260
    height = max((pos["y"] for pos in positions.values()), default=520) + 170
    return positions, max(width, 920), max(height, 620)


def _fusion_details(elements):
    ids = [item.id for item in elements if item.element_type in {"cto", "splice_box"}]
    details = defaultdict(list)
    splices = FiberSplice.objects.filter(splice_box_id__in=ids).select_related(
        "input_fiber__cable", "input_fiber__color", "output_fiber__cable", "output_fiber__color", "splice_box"
    ).order_by("splice_box_id", "id")
    for splice in splices:
        details[splice.splice_box_id].append({
            "kind": "Fusão",
            "input": f"{splice.input_fiber.cable.name} · F{splice.input_fiber.number} · {splice.input_fiber.color.name}",
            "output": f"{splice.output_fiber.cable.name} · F{splice.output_fiber.number} · {splice.output_fiber.color.name}",
            "loss_db": float(splice.loss_db),
        })
    splitters = SpliceTraySplitter.objects.filter(tray__splice_box_id__in=ids).select_related(
        "tray__splice_box", "input_fiber__cable"
    ).prefetch_related("ports__output_fiber__cable").order_by("tray__splice_box_id", "tray__number", "position")
    for splitter in splitters:
        outputs = []
        for port in splitter.ports.all():
            if port.output_fiber_id:
                outputs.append(f"P{port.number} → {port.output_fiber.cable.name} · F{port.output_fiber.number}")
            else:
                outputs.append(f"P{port.number} livre")
        details[splitter.tray.splice_box_id].append({
            "kind": f"Splitter {splitter.ratio}",
            "input": (
                f"{splitter.input_fiber.cable.name} · F{splitter.input_fiber.number}"
                if splitter.input_fiber_id else "Entrada não ligada"
            ),
            "output": " | ".join(outputs),
            "loss_db": None,
        })
    return details


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def route_export_html_v078(request, route_id):
    route = _route_for_user(request, route_id)
    row, cables, passages_by_cable, elements = _route_assets(route)
    element_by_id = {item.id: item for item in elements}
    edges = []
    for cable in cables:
        ordered = _ordered_element_ids(cable, passages_by_cable.get(cable.id, []))
        for index in range(max(0, len(ordered) - 1)):
            edges.append({
                "id": f"{cable.id}:{index}",
                "cable_id": cable.id,
                "source": ordered[index],
                "target": ordered[index + 1],
                "name": cable.name,
                "code": cable.code,
                "fiber_count": cable.fiber_count,
                "type": cable.get_cable_type_display(),
            })
    positions, width, height = _diagram_layout(elements, edges)
    fusion = _fusion_details(elements)
    nodes = []
    for element in elements:
        metadata = element.metadata or {}
        subtype = str(metadata.get("import_subtype") or metadata.get("subtype") or "").lower()
        kind = "CDO" if element.element_type == "splice_box" and subtype == "cdo" else (
            "CEO" if element.element_type == "splice_box" else element.element_type.upper()
        )
        nodes.append({
            "id": element.id,
            "name": element.name,
            "code": element.code,
            "kind": kind,
            "description": element.description,
            "x": positions.get(element.id, {}).get("x", 100),
            "y": positions.get(element.id, {}).get("y", 100),
            "fusions": fusion.get(element.id, []),
        })
    payload = {
        "version": VERSION,
        "route": {"id": route.id, "name": route.name or route.code or f"Rota {route.id}", "code": route.code},
        "nodes": nodes,
        "edges": edges,
        "width": width,
        "height": height,
    }
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    title = html.escape(payload["route"]["name"])
    document = f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5">
<title>Diagrama · {title}</title>
<style>
*{{box-sizing:border-box}}:root{{--bg:#07111f;--panel:#0c1c2c;--line:#35c9ff;--text:#e9f5ff;--muted:#87a5bb;--accent:#20d6b5}}
body{{margin:0;background:var(--bg);color:var(--text);font:14px Inter,system-ui,sans-serif}}header{{position:sticky;top:0;z-index:8;display:flex;justify-content:space-between;gap:14px;padding:13px 18px;border-bottom:1px solid #18364d;background:#091725eF;backdrop-filter:blur(8px)}}header h1{{margin:0;font-size:17px}}header small{{color:var(--muted)}}main{{display:grid;grid-template-columns:minmax(0,1fr) 330px;min-height:calc(100vh - 58px)}}#viewport{{overflow:auto;padding:24px}}svg{{display:block;min-width:100%;border:1px solid #15364f;border-radius:14px;background:radial-gradient(circle at 50% 20%,#0d2940 0,#07111f 58%)}}.edge{{fill:none;stroke:var(--line);stroke-width:4;cursor:pointer;filter:drop-shadow(0 0 4px #1fb4ec66)}}.edge:hover{{stroke:#fff;stroke-width:6}}.node rect{{fill:#0b2133;stroke:#2ed7c2;stroke-width:2}}.node text{{fill:#f7fbff;font-weight:700;pointer-events:none}}.node .kind{{fill:#68a8c7;font-size:10px}}.node{{cursor:pointer}}.node:hover rect{{stroke:#fff;filter:drop-shadow(0 0 6px #20d6b588)}}aside{{border-left:1px solid #18364d;background:#091725;padding:18px;overflow:auto}}aside h2{{margin:0 0 8px;font-size:16px}}aside p,aside li{{color:#a9c0d0;font-size:12px;line-height:1.5}}.detail-card{{padding:11px;margin:8px 0;border:1px solid #25465d;border-radius:10px;background:#0d2233}}.detail-card strong{{display:block;color:#fff;margin-bottom:4px}}.badge{{display:inline-flex;padding:4px 7px;border-radius:999px;background:#103e4a;color:#75f1de;font-size:10px;font-weight:800}}@media(max-width:800px){{main{{grid-template-columns:1fr}}aside{{position:sticky;bottom:0;max-height:42vh;border-left:0;border-top:1px solid #18364d}}#viewport{{padding:10px}}}}
</style></head><body><header><div><h1>{title}</h1><small>AFService Map {VERSION} · diagrama interativo offline</small></div><span class="badge">{len(cables)} cabos · {len(elements)} pontos</span></header>
<main><section id="viewport"><svg id="diagram" viewBox="0 0 {width} {height}" width="{width}" height="{height}" aria-label="Diagrama da rota"></svg></section><aside id="details"><h2>Rota</h2><p>Clique num cabo para ver nome/tipo/fibras. Clique numa CTO/CEO/CDO para abrir as fusões e splitters exportados.</p></aside></main>
<script id="afservice-data" type="application/json">{data_json}</script>
<script>
const data=JSON.parse(document.getElementById('afservice-data').textContent);const svg=document.getElementById('diagram');const details=document.getElementById('details');const NS='http://www.w3.org/2000/svg';const nodes=new Map(data.nodes.map(n=>[n.id,n]));
function el(name,attrs={{}}){{const x=document.createElementNS(NS,name);Object.entries(attrs).forEach(([k,v])=>x.setAttribute(k,v));return x}}function esc(v){{const d=document.createElement('div');d.textContent=v??'';return d.innerHTML}}
for(const edge of data.edges){{const a=nodes.get(edge.source),b=nodes.get(edge.target);if(!a||!b)continue;const p=el('path',{{class:'edge',d:`M${{a.x+180}},${{a.y+36}} C${{a.x+230}},${{a.y+36}} ${{b.x-50}},${{b.y+36}} ${{b.x}},${{b.y+36}}`}});p.addEventListener('click',()=>{{details.innerHTML=`<h2>${{esc(edge.name)}}</h2><span class="badge">CABO</span><div class="detail-card"><strong>${{esc(edge.code||'Sem código')}}</strong><p>${{edge.fiber_count}} fibra(s) · ${{esc(edge.type)}}</p></div>`}});svg.appendChild(p)}}
for(const node of data.nodes){{const g=el('g',{{class:'node',transform:`translate(${{node.x}},${{node.y}})`}});g.appendChild(el('rect',{{width:180,height:72,rx:12}}));const t=el('text',{{x:14,y:30}});t.textContent=node.name;g.appendChild(t);const k=el('text',{{x:14,y:51,class:'kind'}});k.textContent=`${{node.kind}} · ${{node.code||'sem código'}}`;g.appendChild(k);g.addEventListener('click',()=>{{const fusion=(node.fusions||[]).map(f=>`<div class="detail-card"><strong>${{esc(f.kind)}}</strong><p><b>Entrada:</b> ${{esc(f.input)}}</p><p><b>Saída:</b> ${{esc(f.output)}}</p>${{f.loss_db==null?'':`<p>Perda: ${{f.loss_db}} dB</p>`}}</div>`).join('');details.innerHTML=`<h2>${{esc(node.name)}}</h2><span class="badge">${{esc(node.kind)}}</span><p>${{esc(node.description||'')}}</p>${{fusion||'<div class="detail-card">Sem fusões/splitters registrados neste ponto.</div>'}}`}});svg.appendChild(g)}}
</script></body></html>'''
    response = HttpResponse(document, content_type="text/html; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{_safe_filename(payload["route"]["name"], f"rota-{route.id}")}-diagrama.html"'
    return response
