from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from django.contrib.gis.geos import LineString, MultiLineString, Point
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company, scope_company_queryset
from apps.network_map.kmz_import_models import CableElementPassage
from apps.network_map.models import (
    CTO,
    CableReserve,
    ContainerEquipment,
    ContainerEquipmentCard,
    ContainerEquipmentPort,
    ContainerPortLink,
    FiberCable,
    FiberSplice,
    FiberStrand,
    NetworkElement,
    SpliceTraySplitter,
    SpliceTraySplitterPort,
)


VERSION = "0.75.39"
RESERVE_PREFIX = "MAPV07539:"
OPTICAL_PORT_TYPES = {
    ContainerEquipmentPort.PortType.PON,
    ContainerEquipmentPort.PortType.DIO,
    ContainerEquipmentPort.PortType.SFP_1G,
    ContainerEquipmentPort.PortType.SFP_PLUS_10G,
    ContainerEquipmentPort.PortType.SFP28_25G,
    ContainerEquipmentPort.PortType.QSFP_PLUS_40G,
    ContainerEquipmentPort.PortType.QSFP28_100G,
    ContainerEquipmentPort.PortType.SC_APC,
    ContainerEquipmentPort.PortType.SC_UPC,
    ContainerEquipmentPort.PortType.LC,
}


def _json_body(request):
    data = request.data
    return data if isinstance(data, dict) else dict(data or {})


def _decimal(value, default="0.00"):
    try:
        return Decimal(str(value if value not in (None, "") else default))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Valor decimal inválido.")


def _point(data):
    try:
        latitude = float(data.get("latitude"))
        longitude = float(data.get("longitude"))
    except (TypeError, ValueError):
        raise ValueError("Latitude e longitude são obrigatórias.")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Coordenadas inválidas.")
    return Point(longitude, latitude, srid=4326)


def _element_payload(element):
    if not element:
        return None
    metadata = element.metadata or {}
    subtype = str(metadata.get("subtype") or metadata.get("element_subtype") or "")
    label = (
        "CDO" if element.element_type == NetworkElement.ElementType.SPLICE_BOX and subtype == "cdo"
        else "CEO" if element.element_type == NetworkElement.ElementType.SPLICE_BOX
        else element.element_type.upper()
    )
    return {
        "id": element.id,
        "name": element.name,
        "code": element.code,
        "type": element.element_type,
        "subtype": subtype,
        "type_label": label,
        "latitude": element.point.y if element.point else None,
        "longitude": element.point.x if element.point else None,
    }


def _equipment_kind(equipment):
    if equipment.equipment_type == ContainerEquipment.EquipmentType.ONU:
        return "onu"
    if equipment.equipment_type == ContainerEquipment.EquipmentType.OTHER and (
        equipment.metadata or {}
    ).get("equipment_subtype") == "onu":
        return "onu"
    return equipment.equipment_type


def _port_payload(port):
    return {
        "id": port.id,
        "number": port.number,
        "card_number": port.card_number,
        "port_number": port.port_number,
        "label": port.label,
        "type": port.port_type,
        "type_label": port.get_port_type_display(),
        "equipment_id": port.equipment_id,
        "equipment_name": port.equipment.name,
        "equipment_type": _equipment_kind(port.equipment),
    }


def _front_link(port):
    return next((item for item in port.incoming_links.all() if item.source_port_id), None)


def _rear_link(port):
    return next(
        (
            item
            for item in port.incoming_links.all()
            if item.cable_fiber_id or (item.source_port_id is None and item.cable_id)
        ),
        None,
    )


def _front_payload(link):
    if not link:
        return None
    return {
        "id": link.id,
        "source_port_id": link.source_port_id,
        "source_equipment": link.source_port.equipment.name if link.source_port_id else "",
        "source_port": link.source_port.label if link.source_port_id else "",
        "loss_db": float(link.loss_db),
        "notes": link.notes,
    }


def _rear_payload(link):
    if not link:
        return None
    fiber = link.cable_fiber
    cable = fiber.cable if fiber else link.cable
    return {
        "id": link.id,
        "kind": "fusion" if fiber else "drop_termination",
        "cable_id": cable.id if cable else None,
        "cable": cable.name if cable else "",
        "fiber_id": fiber.id if fiber else None,
        "fiber_number": fiber.number if fiber else None,
        "color_name": fiber.color.name if fiber else "",
        "color_hex": fiber.color.hex_color if fiber else "#f97316",
        "loss_db": float(link.loss_db),
        "notes": link.notes,
    }


def _dio_payload(equipment):
    ports = equipment.ports.select_related("equipment").prefetch_related(
        "incoming_links__source_port__equipment",
        "incoming_links__cable",
        "incoming_links__cable_fiber__cable",
        "incoming_links__cable_fiber__color",
    )
    rows = []
    for port in ports:
        front = _front_link(port)
        rear = _rear_link(port)
        rows.append({
            **_port_payload(port),
            "front": _front_payload(front),
            "rear": _rear_payload(rear),
            "state": (
                "both" if front and rear
                else "front" if front
                else "rear" if rear
                else "free"
            ),
        })
    return {
        "version": VERSION,
        "dio": {
            "id": equipment.id,
            "name": equipment.name,
            "capacity": equipment.dio_port_capacity or len(rows),
            "connector_type": equipment.connector_type,
            "connector_type_label": equipment.get_connector_type_display(),
            "metadata": equipment.metadata or {},
        },
        "ports": rows,
        "summary": {
            "free": sum(1 for item in rows if item["state"] == "free"),
            "front": sum(1 for item in rows if item["front"]),
            "rear": sum(1 for item in rows if item["rear"]),
            "both": sum(1 for item in rows if item["state"] == "both"),
        },
    }


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def dio_dual_face_v07539(request, element_id, equipment_id):
    container = get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type__in=[NetworkElement.ElementType.RACK, NetworkElement.ElementType.TOWER],
    )
    equipment = get_object_or_404(
        ContainerEquipment.objects,
        pk=equipment_id,
        container=container,
        equipment_type=ContainerEquipment.EquipmentType.DIO,
    )
    if request.method == "GET":
        return JsonResponse(_dio_payload(equipment))
    if not can_edit_company(request.user, container.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)

    data = _json_body(request)
    action = str(data.get("action") or "")
    if request.method == "POST" and action == "connect_front":
        source = get_object_or_404(
            ContainerEquipmentPort.objects.select_related("equipment"),
            pk=data.get("source_port_id"),
            equipment__container=container,
        )
        destination = get_object_or_404(
            ContainerEquipmentPort.objects.select_related("equipment"),
            pk=data.get("destination_port_id"),
            equipment=equipment,
        )
        if (
            source.equipment.equipment_type != ContainerEquipment.EquipmentType.OLT
            or source.port_type != ContainerEquipmentPort.PortType.PON
        ):
            return JsonResponse({"detail": "A frente do DIO deve receber uma porta PON de OLT."}, status=400)
        if (
            destination.equipment.equipment_type != ContainerEquipment.EquipmentType.DIO
            or destination.port_type != ContainerEquipmentPort.PortType.DIO
        ):
            return JsonResponse({"detail": "O destino precisa ser uma porta do DIO."}, status=400)
        if source.equipment_id == destination.equipment_id:
            return JsonResponse({"detail": "A frente do DIO deve ser ligada a outro equipamento."}, status=400)
        if ContainerPortLink.objects.filter(source_port=source).exists():
            return JsonResponse({"detail": "A porta de origem já possui uma ligação frontal."}, status=409)
        if ContainerPortLink.objects.filter(destination_port=destination, source_port__isnull=False).exists():
            return JsonResponse({"detail": "A frente desta porta do DIO já está ligada."}, status=409)
        try:
            with transaction.atomic():
                ContainerPortLink.objects.create(
                    container=container,
                    source_port=source,
                    destination_port=destination,
                    link_type=ContainerPortLink.LinkType.FIBER,
                    loss_db=_decimal(data.get("loss_db"), "0.50"),
                    notes=str(data.get("notes") or "Cordão frontal OLT/equipamento → DIO")[:180],
                )
        except IntegrityError:
            return JsonResponse({"detail": "Uma das portas já foi utilizada por outra ligação."}, status=409)
        return JsonResponse(_dio_payload(equipment), status=201)

    if request.method == "DELETE" and action in {"disconnect_front", "disconnect_rear"}:
        link = get_object_or_404(ContainerPortLink.objects, pk=data.get("link_id"), container=container)
        if action == "disconnect_front" and not link.source_port_id:
            return JsonResponse({"detail": "Esta ligação não pertence à frente do DIO."}, status=400)
        if action == "disconnect_rear" and not (
            link.cable_fiber_id or (link.source_port_id is None and link.cable_id)
        ):
            return JsonResponse({"detail": "Esta ligação não pertence à traseira do DIO."}, status=400)
        link.delete()
        return JsonResponse(_dio_payload(equipment))

    return JsonResponse({"detail": "Ação inválida para a dupla face do DIO."}, status=400)


def _equipment_payload(equipment):
    metadata = equipment.metadata or {}
    return {
        "id": equipment.id,
        "container_id": equipment.container_id,
        "name": equipment.name,
        "description": equipment.description,
        "type": _equipment_kind(equipment),
        "type_label": equipment.get_equipment_type_display(),
        "vendor": equipment.vendor,
        "model": equipment.model,
        "serial_number": equipment.serial_number,
        "management_ip": equipment.management_ip,
        "provisioning_mode": equipment.provisioning_mode,
        "tx_power_dbm": float(equipment.tx_power_dbm) if equipment.tx_power_dbm is not None else None,
        "connector_type": equipment.connector_type,
        "connector_type_label": equipment.get_connector_type_display(),
        "card_count": equipment.card_count,
        "pons_per_card": equipment.pons_per_card,
        "dio_port_capacity": equipment.dio_port_capacity,
        "enabled": equipment.enabled,
        "metadata": metadata,
        "onu_lan_count": int(metadata.get("onu_lan_count") or 4),
        "pon_connector": metadata.get("pon_connector") or "SC/APC",
        "rx_power_dbm": metadata.get("rx_power_dbm"),
        "port_count": int(metadata.get("port_count") or equipment.ports.count() or 0),
        "ports": [_port_payload(port) for port in equipment.ports.select_related("equipment")],
    }


def _create_equipment_ports_v07539(equipment):
    ports = []
    kind = _equipment_kind(equipment)
    if kind == "dio":
        ports = [
            ContainerEquipmentPort(
                equipment=equipment,
                port_type=ContainerEquipmentPort.PortType.DIO,
                number=number,
                port_number=number,
                label=f"Porta {number}",
            )
            for number in range(1, equipment.dio_port_capacity + 1)
        ]
    elif kind == "pto":
        connector_type = (
            ContainerEquipmentPort.PortType.SC_UPC
            if equipment.connector_type == ContainerEquipment.ConnectorType.SC_UPC
            else ContainerEquipmentPort.PortType.SC_APC
        )
        ports = [
            ContainerEquipmentPort(
                equipment=equipment,
                port_type=ContainerEquipmentPort.PortType.DIO,
                number=1,
                port_number=1,
                label="Entrada fibra",
            ),
            ContainerEquipmentPort(
                equipment=equipment,
                port_type=connector_type,
                number=2,
                port_number=1,
                label=f"Saída {equipment.get_connector_type_display() or 'SC/APC'}",
            ),
        ]
    elif kind == "onu":
        lan_count = max(1, min(int((equipment.metadata or {}).get("onu_lan_count") or 4), 16))
        ports = [
            ContainerEquipmentPort(
                equipment=equipment,
                port_type=ContainerEquipmentPort.PortType.PON,
                number=1,
                port_number=1,
                label=f"PON 1 · {(equipment.metadata or {}).get('pon_connector') or 'SC/APC'}",
            )
        ]
        ports.extend(
            ContainerEquipmentPort(
                equipment=equipment,
                port_type=ContainerEquipmentPort.PortType.RJ45_1G,
                number=index + 1,
                port_number=index,
                label=f"LAN {index}",
            )
            for index in range(1, lan_count + 1)
        )
    elif kind in {"switch", "router", "firewall"}:
        port_count = max(1, min(int((equipment.metadata or {}).get("port_count") or (24 if kind == "switch" else 8)), 96))
        ports = [
            ContainerEquipmentPort(
                equipment=equipment,
                port_type=ContainerEquipmentPort.PortType.RJ45_1G,
                number=number,
                port_number=number,
                label=f"Porta {number}",
            )
            for number in range(1, port_count + 1)
        ]
    elif kind == "olt":
        number = 0
        for slot in range(1, equipment.card_count + 1):
            card = ContainerEquipmentCard.objects.create(
                equipment=equipment,
                slot=slot,
                name=f"Placa {slot}",
                pon_count=equipment.pons_per_card,
            )
            for pon in range(1, equipment.pons_per_card + 1):
                number += 1
                ports.append(ContainerEquipmentPort(
                    equipment=equipment,
                    card=card,
                    port_type=ContainerEquipmentPort.PortType.PON,
                    number=number,
                    card_number=slot,
                    port_number=pon,
                    label=f"Placa {slot} / PON {pon}",
                ))
    ContainerEquipmentPort.objects.bulk_create(ports)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def equipment_collection_v07539(request, element_id):
    container = get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type__in=[NetworkElement.ElementType.RACK, NetworkElement.ElementType.TOWER],
    )
    if not can_edit_company(request.user, container.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    data = _json_body(request)
    requested_type = str(data.get("equipment_type") or "").strip()
    rack_allowed = {
        ContainerEquipment.EquipmentType.OLT,
        ContainerEquipment.EquipmentType.DIO,
        ContainerEquipment.EquipmentType.SWITCH,
        ContainerEquipment.EquipmentType.ROUTER,
        ContainerEquipment.EquipmentType.FIREWALL,
    }
    tower_allowed = {
        *rack_allowed,
        ContainerEquipment.EquipmentType.ACCESS_POINT,
        ContainerEquipment.EquipmentType.PTP,
        ContainerEquipment.EquipmentType.ONU,
        ContainerEquipment.EquipmentType.PTO,
        ContainerEquipment.EquipmentType.OTHER,
    }
    allowed = rack_allowed if container.element_type == NetworkElement.ElementType.RACK else tower_allowed
    if requested_type not in allowed:
        return JsonResponse({"detail": "Tipo de equipamento inválido."}, status=400)
    name = str(data.get("name") or "").strip()
    if not name:
        return JsonResponse({"detail": "Informe o nome do equipamento."}, status=400)
    try:
        card_count = max(0, min(int(data.get("card_count") or 0), 64))
        pons_per_card = max(0, min(int(data.get("pons_per_card") or 0), 64))
        dio_capacity = int(data.get("dio_port_capacity") or 0)
        onu_lan_count = max(1, min(int(data.get("onu_lan_count") or 4), 16))
        port_count = max(1, min(int(data.get("port_count") or 24), 96))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Capacidades informadas são inválidas."}, status=400)
    if requested_type == ContainerEquipment.EquipmentType.DIO and dio_capacity not in {12, 24, 36, 48, 72, 96, 144, 192, 244}:
        return JsonResponse({"detail": "Escolha uma capacidade padrão para o DIO."}, status=400)
    connector = str(data.get("connector_type") or "")
    if requested_type in {ContainerEquipment.EquipmentType.DIO, ContainerEquipment.EquipmentType.PTO}:
        connector = connector or ContainerEquipment.ConnectorType.SC_APC
        if connector not in dict(ContainerEquipment.ConnectorType.choices):
            return JsonResponse({"detail": "Conector inválido."}, status=400)
    else:
        connector = ""
    metadata = {}
    if requested_type in {
        ContainerEquipment.EquipmentType.SWITCH,
        ContainerEquipment.EquipmentType.ROUTER,
        ContainerEquipment.EquipmentType.FIREWALL,
    }:
        metadata["port_count"] = port_count
        metadata["height_units"] = 1 if port_count <= 16 else 2 if port_count <= 24 else 3
        metadata["rack_form_factor"] = "19-inch"
    if requested_type == ContainerEquipment.EquipmentType.ONU:
        metadata.update({
            "equipment_subtype": "onu",
            "onu_lan_count": onu_lan_count,
            "pon_connector": str(data.get("pon_connector") or "SC/APC"),
            "rx_power_dbm": data.get("rx_power_dbm") or None,
        })
    try:
        with transaction.atomic():
            equipment = ContainerEquipment.objects.create(
                company=container.company,
                container=container,
                name=name,
                description=str(data.get("description") or "").strip(),
                equipment_type=requested_type,
                management_ip=data.get("management_ip") or None,
                provisioning_mode=str(data.get("provisioning_mode") or "manual"),
                tx_power_dbm=None if data.get("tx_power_dbm") in (None, "") else _decimal(data.get("tx_power_dbm")),
                connector_type=connector,
                vendor=str(data.get("vendor") or "").strip(),
                model=str(data.get("model") or "").strip(),
                serial_number=str(data.get("serial_number") or "").strip(),
                card_count=card_count,
                pons_per_card=pons_per_card,
                dio_port_capacity=dio_capacity if requested_type == ContainerEquipment.EquipmentType.DIO else 0,
                enabled=bool(data.get("enabled", True)),
                metadata=metadata,
            )
            _create_equipment_ports_v07539(equipment)
    except IntegrityError:
        return JsonResponse({"detail": "Já existe um equipamento com este nome na estrutura."}, status=409)
    return JsonResponse({"equipment": _equipment_payload(equipment)}, status=201)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def equipment_editor_v07539(request, element_id, equipment_id):
    container = get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type__in=[NetworkElement.ElementType.RACK, NetworkElement.ElementType.TOWER],
    )
    equipment = get_object_or_404(ContainerEquipment.objects, pk=equipment_id, container=container)
    if request.method == "GET":
        return JsonResponse({
            "version": VERSION,
            "equipment": _equipment_payload(equipment),
            "connector_types": list(ContainerEquipment.ConnectorType.choices),
            "provisioning_modes": list(ContainerEquipment.ProvisioningMode.choices),
        })
    if not can_edit_company(request.user, container.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    data = _json_body(request)
    update_fields = []
    for field in ("name", "description", "vendor", "model", "serial_number"):
        if field in data:
            value = str(data.get(field) or "").strip()
            if field == "name" and not value:
                return JsonResponse({"detail": "Informe o nome do equipamento."}, status=400)
            setattr(equipment, field, value)
            update_fields.append(field)
    if "management_ip" in data and equipment.equipment_type != ContainerEquipment.EquipmentType.DIO:
        equipment.management_ip = data.get("management_ip") or None
        update_fields.append("management_ip")
    if "provisioning_mode" in data:
        mode = str(data.get("provisioning_mode") or "manual")
        if mode not in dict(ContainerEquipment.ProvisioningMode.choices):
            return JsonResponse({"detail": "Modo de provisionamento inválido."}, status=400)
        equipment.provisioning_mode = mode
        update_fields.append("provisioning_mode")
    if "connector_type" in data:
        connector = str(data.get("connector_type") or "")
        if connector and connector not in dict(ContainerEquipment.ConnectorType.choices):
            return JsonResponse({"detail": "Conector inválido."}, status=400)
        equipment.connector_type = connector
        update_fields.append("connector_type")
    if "tx_power_dbm" in data:
        raw = data.get("tx_power_dbm")
        equipment.tx_power_dbm = None if raw in (None, "") else _decimal(raw)
        update_fields.append("tx_power_dbm")
    if "enabled" in data:
        equipment.enabled = bool(data.get("enabled"))
        update_fields.append("enabled")

    metadata = dict(equipment.metadata or {})
    metadata_changed = False
    metadata_fields = {
        "asset_tag", "rack_unit", "rack_face", "photo_url", "documentation_url",
        "firmware", "role", "notes", "onu_lan_count", "pon_connector",
        "rx_power_dbm", "width", "height", "cavity_columns", "collapsed_cavities",
        "port_count", "height_units", "rack_form_factor",
    }
    for field in metadata_fields:
        if field in data:
            metadata[field] = data.get(field)
            metadata_changed = True
    if "layout" in data and isinstance(data.get("layout"), dict):
        metadata["v07539_layout"] = data["layout"]
        metadata_changed = True
    if metadata_changed:
        equipment.metadata = metadata
        update_fields.append("metadata")
    if update_fields:
        equipment.save(update_fields=[*dict.fromkeys(update_fields), "updated_at"])
    return JsonResponse({"equipment": _equipment_payload(equipment)})


def _target_kind(port):
    kind = _equipment_kind(port.equipment)
    if kind == ContainerEquipment.EquipmentType.DIO:
        return "dio"
    if kind == ContainerEquipment.EquipmentType.PTO:
        return "pto"
    if kind == "onu":
        return "onu"
    return None


def _valid_drop_port(port):
    kind = _target_kind(port)
    if kind == "dio":
        return port.port_type == ContainerEquipmentPort.PortType.DIO
    if kind == "pto":
        return port.port_type == ContainerEquipmentPort.PortType.DIO and "entrada" in port.label.lower()
    if kind == "onu":
        return port.port_type == ContainerEquipmentPort.PortType.PON
    return False


def _drop_target_payload(port):
    kind = _target_kind(port)
    connector = (
        port.equipment.get_connector_type_display()
        or (port.equipment.metadata or {}).get("pon_connector")
        or port.get_port_type_display()
    )
    rear = _rear_link(port) if kind == "dio" else next(
        (
            item for item in port.incoming_links.all()
            if item.source_port_id is None and item.cable_id
        ),
        None,
    )
    return {
        **_port_payload(port),
        "target_kind": kind,
        "connector": connector,
        "occupied": bool(rear),
        "termination": _rear_payload(rear),
    }


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def drop_terminations_v07539(request, element_id):
    container = get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type__in=[NetworkElement.ElementType.RACK, NetworkElement.ElementType.TOWER],
    )
    ports = ContainerEquipmentPort.objects.filter(
        equipment__container=container,
        equipment__equipment_type__in=[
            ContainerEquipment.EquipmentType.DIO,
            ContainerEquipment.EquipmentType.PTO,
            ContainerEquipment.EquipmentType.ONU,
            ContainerEquipment.EquipmentType.OTHER,
        ],
    ).select_related("equipment").prefetch_related(
        "incoming_links__source_port__equipment",
        "incoming_links__cable",
        "incoming_links__cable_fiber__cable",
        "incoming_links__cable_fiber__color",
    )
    valid_ports = [port for port in ports if _valid_drop_port(port)]
    drop_cables = FiberCable.objects.filter(
        company=container.company,
        cable_type=FiberCable.CableType.DROP,
    ).filter(Q(origin=container) | Q(destination=container)).order_by("name")
    if request.method == "GET":
        return JsonResponse({
            "version": VERSION,
            "container": _element_payload(container),
            "drop_cables": [{"id": item.id, "name": item.name, "fiber_count": item.fiber_count} for item in drop_cables],
            "targets": [_drop_target_payload(port) for port in valid_ports],
        })
    if not can_edit_company(request.user, container.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    data = _json_body(request)
    action = str(data.get("action") or "")
    if request.method == "POST" and action == "terminate":
        cable = get_object_or_404(drop_cables, pk=data.get("cable_id"))
        port = get_object_or_404(ContainerEquipmentPort.objects.select_related("equipment"), pk=data.get("port_id"), equipment__container=container)
        if not _valid_drop_port(port):
            return JsonResponse({"detail": "O DROP só pode terminar em DIO, PTO ou PON de ONU/ONT."}, status=400)
        kind = _target_kind(port)
        occupied = _rear_link(port) if kind == "dio" else ContainerPortLink.objects.filter(
            destination_port=port, source_port__isnull=True, cable__isnull=False
        ).first()
        if occupied:
            return JsonResponse({"detail": "A entrada óptica deste destino já está ocupada."}, status=409)
        connector = str(data.get("connector") or port.equipment.get_connector_type_display() or "SC/APC")
        notes = str(data.get("notes") or "").strip()
        stored_notes = f"MAPV07539:DROP:{connector}:{notes}"[:180]
        try:
            with transaction.atomic():
                link = ContainerPortLink.objects.create(
                    container=container,
                    destination_port=port,
                    cable=cable,
                    link_type=ContainerPortLink.LinkType.FIBER,
                    loss_db=_decimal(data.get("loss_db"), "0.10"),
                    notes=stored_notes,
                )
        except IntegrityError:
            return JsonResponse({"detail": "O destino foi ocupado por outra ligação."}, status=409)
        return JsonResponse({"termination": {**_drop_target_payload(port), "link_id": link.id}}, status=201)
    if request.method == "DELETE" and action == "disconnect":
        link = get_object_or_404(
            ContainerPortLink.objects.select_related("cable", "destination_port__equipment"),
            pk=data.get("link_id"),
            container=container,
            source_port__isnull=True,
            cable__isnull=False,
        )
        if link.cable.cable_type != FiberCable.CableType.DROP:
            return JsonResponse({"detail": "Esta terminação não pertence a um cabo DROP."}, status=400)
        link.delete()
        return HttpResponse(status=204)
    return JsonResponse({"detail": "Ação inválida para terminação DROP."}, status=400)


def _reserve_metadata(reserve):
    raw = reserve.notes or ""
    if raw.startswith(RESERVE_PREFIX):
        try:
            data = json.loads(raw[len(RESERVE_PREFIX):])
        except json.JSONDecodeError:
            data = {"notes": raw}
    else:
        data = {"notes": raw}
    return {
        "id": reserve.id,
        "length_m": float(reserve.length_m),
        "label": reserve.label,
        "latitude": reserve.point.y,
        "longitude": reserve.point.x,
        "reserve_type": data.get("reserve_type") or "technical",
        "position": data.get("position") or "rota",
        "responsible": data.get("responsible") or "",
        "notes": data.get("notes") or "",
        "created_at": reserve.created_at.isoformat() if reserve.created_at else None,
    }


def _cable_length_m(cable):
    if not cable.geometry:
        return 0.0
    try:
        geometry = cable.geometry.clone()
        geometry.transform(3857)
        return round(float(geometry.length), 2)
    except Exception:
        return 0.0


def _fiber_usage(cable):
    fibers = list(cable.fibers.select_related("color"))
    used_ids = set(
        ContainerPortLink.objects.filter(cable_fiber__cable=cable).values_list("cable_fiber_id", flat=True)
    )
    for input_id, output_id in FiberSplice.objects.filter(
        Q(input_fiber__cable=cable) | Q(output_fiber__cable=cable)
    ).values_list("input_fiber_id", "output_fiber_id"):
        if input_id:
            used_ids.add(input_id)
        if output_id:
            used_ids.add(output_id)
    used_ids.update(
        SpliceTraySplitter.objects.filter(input_fiber__cable=cable).values_list("input_fiber_id", flat=True)
    )
    used_ids.update(
        SpliceTraySplitterPort.objects.filter(output_fiber__cable=cable).values_list("output_fiber_id", flat=True)
    )
    counts = {"total": len(fibers), "used": 0, "free": 0, "reserved": 0, "damaged": 0}
    rows = []
    for fiber in fibers:
        actual_used = fiber.id in used_ids or fiber.status == FiberStrand.Status.USED
        if fiber.status == FiberStrand.Status.RESERVED:
            counts["reserved"] += 1
        elif fiber.status == FiberStrand.Status.DAMAGED:
            counts["damaged"] += 1
        elif actual_used:
            counts["used"] += 1
        else:
            counts["free"] += 1
        rows.append({
            "id": fiber.id,
            "number": fiber.number,
            "status": fiber.status,
            "used": actual_used,
            "color_name": fiber.color.name,
            "color_hex": fiber.color.hex_color,
            "usage": fiber.usage,
            "notes": fiber.notes,
        })
    return counts, rows


def _cable_connections(cable):
    rows = []
    for splice in FiberSplice.objects.filter(
        Q(input_fiber__cable=cable) | Q(output_fiber__cable=cable)
    ).select_related("splice_box", "input_fiber__cable", "output_fiber__cable"):
        rows.append({
            "type": "fusion",
            "type_label": "Fusão cabo ↔ cabo",
            "id": splice.id,
            "element": splice.splice_box.name,
            "description": f"{splice.input_fiber.cable.name} F{splice.input_fiber.number} ↔ {splice.output_fiber.cable.name} F{splice.output_fiber.number}",
            "loss_db": float(splice.loss_db),
        })
    for splitter in SpliceTraySplitter.objects.filter(input_fiber__cable=cable).select_related("tray__splice_box", "input_fiber"):
        rows.append({
            "type": "splitter_input",
            "type_label": "Ligação de entrada do splitter",
            "id": splitter.id,
            "element": splitter.tray.splice_box.name,
            "description": f"Fibra F{splitter.input_fiber.number} → splitter {splitter.ratio}",
        })
    for port in SpliceTraySplitterPort.objects.filter(output_fiber__cable=cable).select_related("splitter__tray__splice_box", "output_fiber"):
        rows.append({
            "type": "splitter_output",
            "type_label": "Ligação de saída do splitter",
            "id": port.id,
            "element": port.splitter.tray.splice_box.name,
            "description": f"Splitter {port.splitter.ratio} P{port.number} → fibra F{port.output_fiber.number}",
        })
    for link in ContainerPortLink.objects.filter(
        Q(cable=cable) | Q(cable_fiber__cable=cable)
    ).select_related("destination_port__equipment", "source_port__equipment", "cable_fiber"):
        if link.cable_fiber_id:
            kind = "dio_fusion"
            label = "Fusão na traseira do DIO"
            description = f"F{link.cable_fiber.number} → {link.destination_port.equipment.name} · {link.destination_port.label}"
        else:
            kind = "termination"
            label = "Terminação DROP"
            description = f"{cable.name} → {link.destination_port.equipment.name} · {link.destination_port.label}"
        rows.append({
            "type": kind,
            "type_label": label,
            "id": link.id,
            "element": link.destination_port.equipment.container.name,
            "description": description,
            "loss_db": float(link.loss_db),
        })
    return rows



def _cable_optical_budget(cable, connections=None):
    """Resumo conservador do orçamento óptico do cabo.

    Soma a atenuação estimada do trecho e as perdas registradas nas conexões
    ligadas ao cabo. Quando uma fibra termina na traseira de um DIO cuja
    frente recebe uma OLT com potência TX cadastrada, também estima a potência
    disponível no início/fim do trecho.
    """
    length_km = _cable_length_m(cable) / 1000.0
    fiber_loss = round(length_km * 0.35, 2)
    rows = connections if connections is not None else _cable_connections(cable)
    connection_loss = round(sum(float(item.get("loss_db") or 0) for item in rows), 2)
    tx_values = []
    rear_links = ContainerPortLink.objects.filter(
        cable_fiber__cable=cable,
        destination_port__equipment__equipment_type=ContainerEquipment.EquipmentType.DIO,
    ).select_related("destination_port")
    for rear in rear_links:
        front = ContainerPortLink.objects.filter(
            destination_port=rear.destination_port,
            source_port__isnull=False,
        ).select_related("source_port__equipment").first()
        if front and front.source_port.equipment.tx_power_dbm is not None:
            tx_values.append(float(front.source_port.equipment.tx_power_dbm))
    tx_power = max(tx_values) if tx_values else None
    total_loss = round(fiber_loss + connection_loss, 2)
    return {
        "attenuation_db_per_km": 0.35,
        "fiber_loss_db": fiber_loss,
        "connection_loss_db": connection_loss,
        "total_loss_db": total_loss,
        "tx_power_dbm": tx_power,
        "estimated_rx_dbm": round(tx_power - total_loss, 2) if tx_power is not None else None,
        "source_count": len(tx_values),
    }

def _available_boxes(cable):
    associated = set(cable.element_passages.values_list("element_id", flat=True))
    if cable.origin_id:
        associated.add(cable.origin_id)
    if cable.destination_id:
        associated.add(cable.destination_id)
    rows = NetworkElement.objects.filter(
        company=cable.company,
        project=cable.project,
        element_type__in=[NetworkElement.ElementType.CTO, NetworkElement.ElementType.SPLICE_BOX],
    ).exclude(id__in=associated).order_by("name")[:250]
    return [_element_payload(item) for item in rows]


def _cable_payload(cable, include_fibers=True):
    counts, fibers = _fiber_usage(cable)
    connections = _cable_connections(cable)
    passages = [
        {
            "id": item.id,
            "element": _element_payload(item.element),
            "action": item.action,
            "action_label": item.get_action_display(),
            "distance_m": float(item.distance_m),
            "position_m": float(item.position_m) if item.position_m is not None else None,
            "metadata": item.metadata or {},
        }
        for item in cable.element_passages.select_related("element")
    ]
    return {
        "version": VERSION,
        "cable": {
            "id": cable.id,
            "name": cable.name,
            "code": cable.code,
            "type": cable.cable_type,
            "type_label": cable.get_cable_type_display(),
            "fiber_count": cable.fiber_count,
            "status": cable.status,
            "origin": _element_payload(cable.origin),
            "destination": _element_payload(cable.destination),
            "route": {"id": cable.route_id, "name": cable.route.name} if cable.route_id else None,
            "project_id": cable.project_id,
            "length_m": _cable_length_m(cable),
            "geometry": json.loads(cable.geometry.geojson) if cable.geometry else None,
            "fiber_summary": counts,
            "fibers": fibers if include_fibers else [],
        },
        "reserves": [_reserve_metadata(item) for item in cable.reserves.all()],
        "passages": passages,
        "connections": connections,
        "optical_budget": _cable_optical_budget(cable, connections),
        "available_boxes": _available_boxes(cable),
    }


def _reverse_geometry(cable):
    if not cable.geometry:
        return
    try:
        lines = []
        for line in reversed(list(cable.geometry)):
            lines.append(LineString(list(line.coords)[::-1], srid=4326))
        cable.geometry = MultiLineString(*lines, srid=4326)
    except Exception:
        # A troca de origem/destino continua válida mesmo se uma geometria
        # importada tiver uma estrutura GEOS inesperada.
        return


@api_view(["GET", "PATCH", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def cable_workspace_v07539(request, cable_id):
    cable = get_object_or_404(
        scope_company_queryset(FiberCable.objects.select_related("origin", "destination", "route", "project"), request.user),
        pk=cable_id,
    )
    if request.method == "GET":
        return JsonResponse(_cable_payload(cable, include_fibers=request.GET.get("fibers") != "0"))
    if not can_edit_company(request.user, cable.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    data = _json_body(request)
    action = str(data.get("action") or "")

    if request.method == "PATCH" and action == "update":
        update_fields = []
        for field in ("name", "code"):
            if field in data:
                value = str(data.get(field) or "").strip()
                if field == "name" and not value:
                    return JsonResponse({"detail": "Informe o nome do cabo."}, status=400)
                setattr(cable, field, value)
                update_fields.append(field)
        if "cable_type" in data:
            value = str(data.get("cable_type") or "")
            if value not in dict(FiberCable.CableType.choices):
                return JsonResponse({"detail": "Tipo de cabo inválido."}, status=400)
            cable.cable_type = value
            update_fields.append("cable_type")
        if "status" in data:
            cable.status = str(data.get("status") or cable.status)
            update_fields.append("status")
        if update_fields:
            cable.save(update_fields=[*dict.fromkeys(update_fields), "updated_at"])
        return JsonResponse(_cable_payload(cable, include_fibers=False))

    if request.method == "POST" and action == "reverse":
        with transaction.atomic():
            cable.origin, cable.destination = cable.destination, cable.origin
            _reverse_geometry(cable)
            cable.save(update_fields=["origin", "destination", "geometry", "updated_at"])
            FiberStrand.objects.filter(cable=cable).update(
                origin_element=cable.origin,
                destination_element=cable.destination,
            )
        return JsonResponse(_cable_payload(cable, include_fibers=False))

    if request.method == "POST" and action == "reserve":
        try:
            point = _point(data)
            length_m = _decimal(data.get("length_m"))
        except ValueError as error:
            return JsonResponse({"detail": str(error)}, status=400)
        if length_m <= 0:
            return JsonResponse({"detail": "A metragem da reserva deve ser maior que zero."}, status=400)
        metadata = {
            "reserve_type": str(data.get("reserve_type") or "technical"),
            "position": str(data.get("position") or "rota"),
            "responsible": str(data.get("responsible") or "")[:120],
            "notes": str(data.get("notes") or ""),
        }
        reserve = CableReserve.objects.create(
            cable=cable,
            point=point,
            length_m=length_m,
            label=str(data.get("label") or "Reserva técnica")[:100],
            notes=RESERVE_PREFIX + json.dumps(metadata, ensure_ascii=False),
        )
        return JsonResponse({"reserve": _reserve_metadata(reserve)}, status=201)

    if request.method == "POST" and action == "create_box":
        subtype = str(data.get("subtype") or "").lower()
        if subtype not in {"cto", "ceo", "cdo"}:
            return JsonResponse({"detail": "Escolha CTO, CEO ou CDO."}, status=400)
        try:
            point = _point(data)
        except ValueError as error:
            return JsonResponse({"detail": str(error)}, status=400)
        name = str(data.get("name") or f"{subtype.upper()} do cabo {cable.name}").strip()
        code = str(data.get("code") or "").strip()
        passage_action = str(data.get("passage_action") or CableElementPassage.Action.PASS)
        if passage_action not in dict(CableElementPassage.Action.choices):
            passage_action = CableElementPassage.Action.PASS
        with transaction.atomic():
            if subtype == "cto":
                element = CTO.objects.create(
                    company=cable.company,
                    project=cable.project,
                    name=name,
                    code=code,
                    point=point,
                    element_type=NetworkElement.ElementType.CTO,
                    route=cable.route,
                    metadata={"subtype": "cto", "created_from_cable_v07539": cable.id},
                )
            else:
                element = NetworkElement.objects.create(
                    company=cable.company,
                    project=cable.project,
                    name=name,
                    code=code,
                    point=point,
                    element_type=NetworkElement.ElementType.SPLICE_BOX,
                    metadata={"subtype": subtype, "created_from_cable_v07539": cable.id},
                )
            CableElementPassage.objects.create(
                cable=cable,
                element=element,
                action=passage_action,
                sequence=(cable.element_passages.count() + 1),
                distance_m=Decimal("0"),
                metadata={"created_from_cable_menu_v07539": True},
            )
            if passage_action == CableElementPassage.Action.CONNECT:
                if cable.origin_id is None:
                    cable.origin = element
                    cable.save(update_fields=["origin", "updated_at"])
                elif cable.destination_id is None:
                    cable.destination = element
                    cable.save(update_fields=["destination", "updated_at"])
        return JsonResponse({"element": _element_payload(element)}, status=201)

    if request.method == "POST" and action == "associate_element":
        element = get_object_or_404(
            NetworkElement.objects,
            pk=data.get("element_id"),
            company=cable.company,
            project=cable.project,
            element_type__in=[NetworkElement.ElementType.CTO, NetworkElement.ElementType.SPLICE_BOX],
        )
        passage_action = str(data.get("passage_action") or CableElementPassage.Action.PASS)
        if passage_action not in dict(CableElementPassage.Action.choices):
            passage_action = CableElementPassage.Action.PASS
        passage, _ = CableElementPassage.objects.update_or_create(
            cable=cable,
            element=element,
            action=passage_action,
            defaults={
                "sequence": cable.element_passages.count() + 1,
                "distance_m": Decimal("0"),
                "metadata": {"associated_from_cable_menu_v07539": True},
            },
        )
        return JsonResponse({"passage": {"id": passage.id, "element": _element_payload(element), "action": passage.action}}, status=201)

    if request.method == "DELETE" and action == "reserve":
        reserve = get_object_or_404(CableReserve, pk=data.get("reserve_id"), cable=cable)
        reserve.delete()
        return HttpResponse(status=204)

    if request.method == "DELETE" and action == "passage":
        passage = get_object_or_404(CableElementPassage, pk=data.get("passage_id"), cable=cable)
        passage.delete()
        return HttpResponse(status=204)

    return JsonResponse({"detail": "Ação inválida no painel do cabo."}, status=400)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def layout_v07539(request, element_id):
    element = get_object_or_404(scope_company_queryset(NetworkElement.objects, request.user), pk=element_id)
    metadata = dict(element.metadata or {})
    if request.method == "GET":
        return JsonResponse({"version": VERSION, "layout": metadata.get("map_v07539_layout") or {}})
    if not can_edit_company(request.user, element.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    data = _json_body(request)
    incoming = data.get("layout")
    if not isinstance(incoming, dict):
        return JsonResponse({"detail": "Envie um objeto layout válido."}, status=400)
    current = dict(metadata.get("map_v07539_layout") or {})
    for key, value in incoming.items():
        if value is None:
            current.pop(str(key), None)
        else:
            current[str(key)] = value
    metadata["map_v07539_layout"] = current
    element.metadata = metadata
    element.save(update_fields=["metadata", "updated_at"])
    return JsonResponse({"version": VERSION, "layout": current})
