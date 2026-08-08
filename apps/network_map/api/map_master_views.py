from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import models, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company, scope_company_queryset
from apps.access.models import AccessPoint
from apps.network_map.map_master_models import (
    MapDiagramRevision,
    MapIconStyle,
    NetworkAssetLifecycle,
)
from apps.network_map.models import (
    CTO,
    CTOSplitter,
    CTOSplitterPort,
    SpliceTraySplitterPort,
    ContainerEquipment,
    ContainerEquipmentPort,
    FiberCable,
    NetworkElement,
    NetworkProject,
    NetworkRoute,
    CableReserve,
    ContainerPortLink,
)
from apps.network_map.map_master_topology import (
    project_route_topology,
    shortest_optical_path,
)


def _project_for_user(request, project_id: int) -> NetworkProject:
    return get_object_or_404(
        scope_company_queryset(NetworkProject.objects.all(), request.user),
        pk=project_id,
    )


def _require_edit(request, company_id: int) -> JsonResponse | None:
    if not can_edit_company(request.user, company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    return None


def _icon_payload(style: MapIconStyle) -> dict[str, Any]:
    return {
        "id": style.id,
        "element_type": style.element_type,
        "subtype": style.subtype,
        "display_name": style.display_name,
        "svg_markup": style.svg_markup,
        "image_url": style.image_url,
        "foreground_color": style.foreground_color,
        "background_color": style.background_color,
        "border_color": style.border_color,
        "size_px": style.size_px,
        "show_label": style.show_label,
        "show_name_inside_icon": style.show_name_inside_icon,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def map_master_bootstrap(request):
    project_id = request.GET.get("project_id")
    if not project_id:
        return JsonResponse({"detail": "Informe project_id."}, status=400)
    project = _project_for_user(request, int(project_id))
    topology = project_route_topology(project)
    icons = MapIconStyle.objects.filter(company=project.company, enabled=True)
    return JsonResponse({
        "version": "1.0.0",
        "project": {"id": project.id, "name": project.name, "code": project.code},
        "topology": topology,
        "icons": [_icon_payload(style) for style in icons],
        "ui": {
            "route_drawer_collapsed": True,
            "sidebar_compact": True,
            "fusion_toolbar_compact": True,
            "container_workspace_tabs": [
                "equipment", "canvas", "matrix", "fibers", "models",
            ],
        },
        "equipment_types": [
            ["olt", "OLT"], ["dio", "DIO"], ["switch", "Switch"],
            ["router", "Roteador"], ["firewall", "Firewall"],
            ["server", "Servidor"], ["access_point", "Access point"],
            ["ptp", "Rádio PTP"], ["onu", "ONU / ONT"],
            ["pto", "PTO"], ["other", "Outro"],
        ],
        "port_types": [
            ["pon", "PON"], ["dio", "Porta óptica/DIO"],
            ["rj45_100m", "RJ45 100 Mb"], ["rj45_1g", "RJ45 1 Gb"],
            ["rj45_2g5", "RJ45 2.5 Gb"], ["sfp_1g", "SFP 1 Gb"],
            ["sfp_plus_10g", "SFP+ 10 Gb"], ["sfp28_25g", "SFP28 25 Gb"],
            ["qsfp_plus_40g", "QSFP+ 40 Gb"], ["qsfp28_100g", "QSFP28 100 Gb"],
            ["sc_apc", "SC/APC"], ["sc_upc", "SC/UPC"],
            ["lc", "LC"], ["wireless", "Wireless"], ["power", "Energia"],
        ],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def route_topology_master(request, project_id):
    project = _project_for_user(request, project_id)
    return JsonResponse(project_route_topology(project))


@api_view(["POST", "PATCH"])
@permission_classes([IsAuthenticated])
def assign_cable_route_master(request, cable_id):
    cable = get_object_or_404(
        scope_company_queryset(FiberCable.objects.all(), request.user).select_related("project"),
        pk=cable_id,
    )
    denied = _require_edit(request, cable.company_id)
    if denied:
        return denied
    route_id = request.data.get("route_id")
    if route_id in (None, "", 0, "0"):
        cable.route = None
    else:
        cable.route = get_object_or_404(
            NetworkRoute,
            pk=route_id,
            project=cable.project,
            company=cable.company,
        )
    cable.save(update_fields=["route", "updated_at"])
    return JsonResponse({
        "success": True,
        "cable_id": cable.id,
        "route": None if not cable.route else {
            "id": cable.route.id,
            "name": cable.route.name,
            "code": cable.route.code,
        },
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def optical_trace_master(request, project_id):
    project = _project_for_user(request, project_id)
    start = str(request.GET.get("start") or "").strip()
    end = str(request.GET.get("end") or "").strip()
    if not start or not end:
        return JsonResponse(
            {"detail": "Informe start e end, por exemplo element:10 e port:25."},
            status=400,
        )
    route_id = request.GET.get("route_id")
    try:
        route_id = int(route_id) if route_id else None
    except (TypeError, ValueError):
        return JsonResponse({"detail": "route_id inválido."}, status=400)
    return JsonResponse(shortest_optical_path(project, start, end, route_id=route_id))


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def diagram_revisions_master(request, project_id):
    project = _project_for_user(request, project_id)
    queryset = MapDiagramRevision.objects.filter(project=project).select_related("element", "created_by")
    element_id = request.GET.get("element_id")
    diagram_type = request.GET.get("diagram_type")
    if element_id:
        queryset = queryset.filter(element_id=element_id)
    if diagram_type:
        queryset = queryset.filter(diagram_type=diagram_type)
    if request.method == "GET":
        rows = queryset[:100]
        return JsonResponse({"revisions": [{
            "id": item.id,
            "diagram_type": item.diagram_type,
            "element_id": item.element_id,
            "element": item.element.name if item.element else "",
            "note": item.note,
            "payload": item.payload,
            "created_by": item.created_by.get_username() if item.created_by else "",
            "created_at": item.created_at.isoformat(),
        } for item in rows]})

    denied = _require_edit(request, project.company_id)
    if denied:
        return denied
    diagram_type = str(request.data.get("diagram_type") or "").strip()
    if diagram_type not in dict(MapDiagramRevision.DiagramType.choices):
        return JsonResponse({"detail": "Tipo de diagrama inválido."}, status=400)
    element = None
    if request.data.get("element_id"):
        element = get_object_or_404(
            NetworkElement,
            pk=request.data["element_id"],
            project=project,
            company=project.company,
        )
    payload = request.data.get("payload")
    if not isinstance(payload, dict):
        return JsonResponse({"detail": "payload deve ser um objeto JSON."}, status=400)
    revision = MapDiagramRevision.objects.create(
        company=project.company,
        project=project,
        element=element,
        diagram_type=diagram_type,
        payload=payload,
        note=str(request.data.get("note") or "")[:240],
        created_by=request.user,
    )
    return JsonResponse({"id": revision.id, "created_at": revision.created_at.isoformat()}, status=201)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def lifecycle_master(request, project_id):
    project = _project_for_user(request, project_id)
    queryset = NetworkAssetLifecycle.objects.filter(project=project).select_related("changed_by")
    asset_type = request.GET.get("asset_type")
    asset_id = request.GET.get("asset_id")
    if asset_type:
        queryset = queryset.filter(asset_type=asset_type)
    if asset_id:
        queryset = queryset.filter(asset_id=asset_id)
    if request.method == "GET":
        return JsonResponse({"events": [{
            "id": item.id,
            "asset_type": item.asset_type,
            "asset_id": item.asset_id,
            "stage": item.stage,
            "stage_label": item.get_stage_display(),
            "note": item.note,
            "metadata": item.metadata,
            "changed_by": item.changed_by.get_username() if item.changed_by else "",
            "created_at": item.created_at.isoformat(),
        } for item in queryset[:200]]})

    denied = _require_edit(request, project.company_id)
    if denied:
        return denied
    asset_type = str(request.data.get("asset_type") or "")
    stage = str(request.data.get("stage") or "")
    if asset_type not in dict(NetworkAssetLifecycle.AssetType.choices):
        return JsonResponse({"detail": "Tipo de ativo inválido."}, status=400)
    if stage not in dict(NetworkAssetLifecycle.Stage.choices):
        return JsonResponse({"detail": "Etapa inválida."}, status=400)
    try:
        asset_id = int(request.data.get("asset_id"))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "asset_id inválido."}, status=400)
    event = NetworkAssetLifecycle.objects.create(
        company=project.company,
        project=project,
        asset_type=asset_type,
        asset_id=asset_id,
        stage=stage,
        note=str(request.data.get("note") or ""),
        metadata=request.data.get("metadata") if isinstance(request.data.get("metadata"), dict) else {},
        changed_by=request.user,
    )
    return JsonResponse({"id": event.id, "stage": event.stage}, status=201)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def splitter_ports_master(request, cto_id):
    cto = get_object_or_404(
        scope_company_queryset(CTO.objects.all(), request.user),
        pk=cto_id,
    )
    ports = CTOSplitterPort.objects.filter(splitter__cto=cto).select_related(
        "splitter",
        "access_point",
        "direct_drop_cable",
        "direct_drop_cable__origin",
        "direct_drop_cable__destination",
    )
    # A ligação física desenhada no canvas usa SpliceTraySplitterPort.output_fiber.
    # Derivamos a ocupação comercial pela mesma posição de splitter/porta, sem
    # criar fibra sintética para associação ERP.
    graphic_drop_rows = (
        SpliceTraySplitterPort.objects.filter(
            splitter__tray__splice_box=cto,
            output_fiber__cable__cable_type=FiberCable.CableType.DROP,
        )
        .select_related(
            "splitter",
            "output_fiber__cable",
            "output_fiber__cable__origin",
            "output_fiber__cable__destination",
        )
        .order_by("splitter__position", "number")
    )
    physical_drop_by_port = {
        (row.splitter.position, row.number): row.output_fiber.cable
        for row in graphic_drop_rows
        if row.output_fiber_id
    }
    if request.method == "PATCH":
        denied = _require_edit(request, cto.company_id)
        if denied:
            return denied
        port = get_object_or_404(ports, pk=request.data.get("port_id"))

        if "notes" in request.data:
            port.notes = str(request.data.get("notes") or "")
        if "direct_drop_label" in request.data:
            port.direct_drop_label = str(request.data.get("direct_drop_label") or "").strip()

        access_point_id = request.data.get("access_point_id", "__missing__")
        if access_point_id != "__missing__":
            if access_point_id:
                port.access_point = get_object_or_404(
                    AccessPoint,
                    pk=access_point_id,
                    company_id=cto.company_id,
                )
            else:
                port.access_point = None

        direct_drop_cable_id = request.data.get("direct_drop_cable_id", "__missing__")
        if direct_drop_cable_id != "__missing__":
            if direct_drop_cable_id:
                candidate_drop_cable = get_object_or_404(
                    FiberCable,
                    pk=direct_drop_cable_id,
                    company_id=cto.company_id,
                    project_id=cto.project_id,
                    cable_type=FiberCable.CableType.DROP,
                )
                # MAP_V076_DROP_PORT_CONFLICT: direct_drop_cable é OneToOne
                # (um DROP não pode ocupar duas portas) -- sem essa checagem,
                # o save() abaixo estoura IntegrityError não tratado (500)
                # em vez de devolver um erro claro pro operador.
                conflict = (
                    CTOSplitterPort.objects.filter(direct_drop_cable=candidate_drop_cable)
                    .exclude(pk=port.pk)
                    .exists()
                )
                if conflict:
                    return JsonResponse(
                        {"detail": "Esse cabo DROP já está vinculado a outra porta."},
                        status=409,
                    )
                port.direct_drop_cable = candidate_drop_cable
            else:
                port.direct_drop_cable = None
                if "direct_drop_label" not in request.data:
                    port.direct_drop_label = ""

        explicit_status = request.data.get("status")
        if explicit_status:
            status_value = str(explicit_status)
            if status_value not in dict(CTOSplitterPort.Status.choices):
                return JsonResponse({"detail": "Status inválido."}, status=400)
            port.status = status_value

        if port.access_point_id or port.direct_drop_cable_id:
            port.status = CTOSplitterPort.Status.OCCUPIED
        elif not explicit_status and port.status == CTOSplitterPort.Status.OCCUPIED:
            port.status = CTOSplitterPort.Status.FREE

        port.save(
            update_fields=[
                "status",
                "notes",
                "access_point",
                "direct_drop_cable",
                "direct_drop_label",
                "updated_at",
            ]
        )

    splitters = (
        CTOSplitter.objects.filter(cto=cto, enabled=True)
        .prefetch_related(
            models.Prefetch(
                "ports",
                queryset=ports.order_by("number"),
            )
        )
        .order_by("position")
    )

    def port_payload(port):
        access_label = ""
        if port.access_point:
            access_label = (
                port.access_point.customer_name
                or port.access_point.username
                or str(port.access_point)
            )
        physical_drop = physical_drop_by_port.get(
            (port.splitter.position, port.number)
        )
        drop_cable = port.direct_drop_cable or physical_drop
        drop_endpoint = ""
        if drop_cable:
            endpoint = drop_cable.destination
            if endpoint and endpoint.id == cto.id:
                endpoint = drop_cable.origin
            drop_endpoint = port.direct_drop_label or (
                endpoint.name if endpoint else drop_cable.name
            )
        effective_status = (
            CTOSplitterPort.Status.OCCUPIED
            if port.access_point_id or drop_cable
            else port.status
        )
        occupied_label = access_label or drop_endpoint
        return {
            "id": port.id,
            "number": port.number,
            "label": port.label or f"Porta {port.number}",
            "status": effective_status,
            "status_label": dict(CTOSplitterPort.Status.choices).get(
                effective_status, effective_status
            ),
            "access_point_id": port.access_point_id,
            "access_point": None if not port.access_point else {
                "id": port.access_point.id,
                "pppoe": port.access_point.username,
                "customer_name": port.access_point.customer_name,
                "label": access_label,
            },
            "direct_drop_cable_id": drop_cable.id if drop_cable else None,
            "direct_drop": None if not drop_cable else {
                "cable_id": drop_cable.id,
                "cable": drop_cable.name,
                "endpoint": drop_endpoint,
                "source": "manual_canvas" if physical_drop else "port_binding",
            },
            "occupied_by": occupied_label,
            "notes": port.notes,
        }

    return JsonResponse({
        "cto": {"id": cto.id, "name": cto.name, "capacity": cto.capacity},
        "splitters": [{
            "id": splitter.id,
            "name": splitter.name,
            "ratio": splitter.ratio,
            "output_ports": splitter.output_ports,
            "ports": [port_payload(port) for port in splitter.ports.all()],
        } for splitter in splitters],
    })




@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def equipment_master_detail(request, element_id, equipment_id):
    equipment = get_object_or_404(
        ContainerEquipment.objects.select_related("container").prefetch_related("ports", "cards"),
        pk=equipment_id,
        container_id=element_id,
        container__in=scope_company_queryset(NetworkElement.objects.all(), request.user),
    )
    if request.method == "PATCH":
        denied = _require_edit(request, equipment.company_id)
        if denied:
            return denied
        metadata = dict(equipment.metadata or {})
        for key in (
            "photo_url", "notes", "asset_tag", "rack_unit", "rack_face", "documentation_url",
            "firmware", "role", "power_feed", "snmp_profile", "canvas_group",
            "chassis_slots", "uplink_count", "tray_count", "ports_per_tray",
            "height_units", "rack_position",
        ):
            if key in request.data:
                metadata[key] = request.data.get(key)
        if isinstance(request.data.get("port_modules"), dict):
            metadata["port_modules"] = request.data["port_modules"]
        if isinstance(request.data.get("custom_fields"), dict):
            metadata["custom_fields"] = request.data["custom_fields"]
        equipment.metadata = metadata
        for field in ("name", "description", "vendor", "model", "serial_number"):
            if field in request.data:
                setattr(equipment, field, str(request.data.get(field) or "").strip())
        if "management_ip" in request.data:
            equipment.management_ip = str(request.data.get("management_ip") or "").strip() or None
        if "connector_type" in request.data:
            connector = str(request.data.get("connector_type") or "").strip()
            if connector and connector not in dict(ContainerEquipment.ConnectorType.choices):
                return JsonResponse({"detail": "Conector inválido."}, status=400)
            equipment.connector_type = connector
        if "tx_power_dbm" in request.data:
            raw_power = request.data.get("tx_power_dbm")
            try:
                equipment.tx_power_dbm = Decimal(str(raw_power).replace(",", ".")) if raw_power not in (None, "") else None
            except (InvalidOperation, ValueError):
                return JsonResponse({"detail": "Potência óptica inválida."}, status=400)
        equipment.save()

    metadata = dict(equipment.metadata or {})
    return JsonResponse({"equipment": {
        "id": equipment.id,
        "name": equipment.name,
        "description": equipment.description,
        "type": equipment.equipment_type,
        "type_label": equipment.get_equipment_type_display(),
        "management_ip": equipment.management_ip,
        "vendor": equipment.vendor,
        "model": equipment.model,
        "serial_number": equipment.serial_number,
        "connector_type": equipment.connector_type,
        "tx_power_dbm": equipment.tx_power_dbm,
        "metadata": metadata,
        "cards": [{
            "id": card.id, "slot": card.slot, "name": card.name,
            "model": card.model, "pon_count": card.pon_count,
        } for card in equipment.cards.all()],
        "ports": [{
            "id": port.id, "label": port.label, "type": port.port_type,
            "type_label": port.get_port_type_display(), "number": port.number,
            "module": (metadata.get("port_modules") or {}).get(str(port.id), ""),
        } for port in equipment.ports.all()],
    }})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_cable_reserve_master(request, cable_id):
    from django.contrib.gis.geos import Point
    from apps.network_map.models import CableReserve

    cable = get_object_or_404(
        scope_company_queryset(FiberCable.objects.all(), request.user),
        pk=cable_id,
    )
    denied = _require_edit(request, cable.company_id)
    if denied:
        return denied
    try:
        latitude = float(request.data.get("latitude"))
        longitude = float(request.data.get("longitude"))
        length_m = str(request.data.get("length_m") or "20").replace(",", ".")
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Coordenadas ou metragem inválidas."}, status=400)
    reserve = CableReserve.objects.create(
        cable=cable,
        point=Point(longitude, latitude, srid=4326),
        length_m=length_m,
        label=str(request.data.get("label") or "")[:100],
        notes=str(request.data.get("notes") or ""),
    )
    return JsonResponse({
        "reserve": {
            "id": reserve.id,
            "cable_id": cable.id,
            "length_m": float(reserve.length_m),
            "label": reserve.label,
            "latitude": reserve.point.y,
            "longitude": reserve.point.x,
        }
    }, status=201)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def asset_report_master(request, project_id):
    """Ficha técnica serializável para impressão, auditoria e exportação."""
    project = _project_for_user(request, project_id)
    asset_type = str(request.GET.get("asset_type") or "").strip()
    try:
        asset_id = int(request.GET.get("asset_id"))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "asset_id inválido."}, status=400)

    lifecycle = NetworkAssetLifecycle.objects.filter(
        project=project, asset_type=asset_type, asset_id=asset_id,
    ).select_related("changed_by")[:50]
    history = [{
        "stage": item.stage,
        "stage_label": item.get_stage_display(),
        "note": item.note,
        "changed_by": item.changed_by.get_username() if item.changed_by else "",
        "created_at": item.created_at.isoformat(),
    } for item in lifecycle]

    if asset_type == "element":
        element = get_object_or_404(
            NetworkElement.objects.prefetch_related("internal_equipments__ports"),
            pk=asset_id, project=project, company=project.company,
        )
        cables = FiberCable.objects.filter(
            project=project,
        ).filter(models.Q(origin=element) | models.Q(destination=element)).select_related("route")
        data = {
            "id": element.id, "name": element.name, "code": element.code,
            "type": element.element_type, "status": element.status,
            "description": element.description, "metadata": element.metadata,
            "latitude": element.point.y if element.point else None,
            "longitude": element.point.x if element.point else None,
            "cables": [{
                "id": cable.id, "name": cable.name, "code": cable.code,
                "type": cable.cable_type, "fibers": cable.fiber_count,
                "route": cable.route.name if cable.route else "",
            } for cable in cables],
            "equipment": [{
                "id": item.id, "name": item.name,
                "type": item.get_equipment_type_display(),
                "vendor": item.vendor, "model": item.model,
                "management_ip": item.management_ip,
                "serial_number": item.serial_number,
                "ports": item.ports.count(), "metadata": item.metadata,
            } for item in element.internal_equipments.all()],
        }
    elif asset_type == "cable":
        cable = get_object_or_404(
            FiberCable.objects.select_related("route", "origin", "destination", "cable_model"),
            pk=asset_id, project=project, company=project.company,
        )
        data = {
            "id": cable.id, "name": cable.name, "code": cable.code,
            "type": cable.cable_type, "status": cable.status,
            "fiber_count": cable.fiber_count, "used_fibers": cable.used_fibers,
            "model": str(cable.cable_model) if cable.cable_model else "",
            "route": cable.route.name if cable.route else "",
            "origin": cable.origin.name if cable.origin else "",
            "destination": cable.destination.name if cable.destination else "",
            "reserves": [{
                "id": reserve.id, "length_m": float(reserve.length_m),
                "label": reserve.label, "notes": reserve.notes,
                "latitude": reserve.point.y, "longitude": reserve.point.x,
            } for reserve in cable.reserves.all()],
        }
    elif asset_type == "equipment":
        equipment = get_object_or_404(
            ContainerEquipment.objects.select_related("container").prefetch_related("ports", "cards"),
            pk=asset_id, container__project=project, company=project.company,
        )
        data = {
            "id": equipment.id, "name": equipment.name,
            "type": equipment.get_equipment_type_display(),
            "container": equipment.container.name, "container_id": equipment.container_id,
            "latitude": equipment.container.point.y if equipment.container.point else None,
            "longitude": equipment.container.point.x if equipment.container.point else None,
            "vendor": equipment.vendor,
            "model": equipment.model, "serial_number": equipment.serial_number,
            "management_ip": equipment.management_ip, "metadata": equipment.metadata,
            "ports": [{"id": port.id, "label": port.label, "type": port.get_port_type_display()} for port in equipment.ports.all()],
            "cards": [{"id": card.id, "slot": card.slot, "name": card.name, "pon_count": card.pon_count} for card in equipment.cards.all()],
        }
    else:
        return JsonResponse({"detail": "asset_type deve ser element, cable ou equipment."}, status=400)

    return JsonResponse({
        "project": {"id": project.id, "name": project.name, "code": project.code},
        "asset_type": asset_type,
        "asset": data,
        "lifecycle": history,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def asset_qr_master(request, project_id):
    """QR SVG que abre o ativo diretamente no mapa."""
    project = _project_for_user(request, project_id)
    asset_type = str(request.GET.get("asset_type") or "").strip()
    try:
        asset_id = int(request.GET.get("asset_id"))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "asset_id inválido."}, status=400)
    if asset_type not in {"element", "cable", "equipment"}:
        return JsonResponse({"detail": "Tipo de ativo inválido."}, status=400)
    target = request.build_absolute_uri(
        f"/mapa/?project={project.id}&focus={asset_type}:{asset_id}"
    )
    try:
        import qrcode
        from qrcode.image.svg import SvgPathImage
    except ImportError:
        return JsonResponse({"detail": "Dependência qrcode não instalada."}, status=503)
    image = qrcode.make(target, image_factory=SvgPathImage, box_size=8, border=2)
    response = HttpResponse(content_type="image/svg+xml")
    image.save(response)
    response["Content-Disposition"] = f'inline; filename="mapa-{asset_type}-{asset_id}.svg"'
    return response

