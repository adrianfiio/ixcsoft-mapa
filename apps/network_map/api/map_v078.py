from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company, scope_company_queryset
from apps.network_map.device_type_yaml_v07551 import CONNECTOR_LABELS, decimal_payload, legacy_port_type
from apps.network_map.models import (
    ContainerEquipment,
    ContainerEquipmentPort,
    ContainerPortLink,
    FiberCable,
    FiberSplice,
    FiberStrand,
    NetworkElement,
    SpliceTraySplitterPort,
)


VERSION = "0.78.0"
PORT_PROFILE_KEY = "v07551_port_profiles"
PORT_POWER_KEY = "v07548_port_tx_power_dbm"
DIO_PORT_LOSS_DB = 0.50
FUSION_LOSS_DB = 0.10
FIBER_ATTENUATION_DB_PER_KM = 0.35
BALANCED_SPLITTER_LOSS_DB = {
    "1:2": 3.7,
    "1:4": 7.0,
    "1:8": 10.5,
    "1:16": 13.5,
    "1:32": 16.7,
    "1:64": 20.4,
}
UNBALANCED_SPLITTER_LOSS_DB = {
    "10:90": (11.2, 0.8),
    "15:85": (9.2, 1.0),
    "20:80": (7.8, 1.3),
    "30:70": (6.0, 2.0),
    "40:60": (4.7, 2.7),
    "45:55": (4.1, 3.2),
}

ALLOWED_EDIT_TYPES = {
    ContainerEquipment.EquipmentType.SWITCH,
    ContainerEquipment.EquipmentType.ROUTER,
    ContainerEquipment.EquipmentType.ACCESS_POINT,
    ContainerEquipment.EquipmentType.PTP,
}
RADIO_TYPES = {
    ContainerEquipment.EquipmentType.ACCESS_POINT,
    ContainerEquipment.EquipmentType.PTP,
}
GENERIC_PORT_TYPES = {
    ContainerEquipmentPort.PortType.RJ45_100M,
    ContainerEquipmentPort.PortType.RJ45_1G,
    ContainerEquipmentPort.PortType.RJ45_2G5,
    ContainerEquipmentPort.PortType.SFP_1G,
    ContainerEquipmentPort.PortType.SFP_PLUS_10G,
    ContainerEquipmentPort.PortType.SFP28_25G,
    ContainerEquipmentPort.PortType.QSFP_PLUS_40G,
    ContainerEquipmentPort.PortType.QSFP28_100G,
    ContainerEquipmentPort.PortType.WIRELESS,
}
CONNECTOR_SPEED_TO_PORT = {
    ("rj45", Decimal("0.1")): ContainerEquipmentPort.PortType.RJ45_100M,
    ("rj45", Decimal("1")): ContainerEquipmentPort.PortType.RJ45_1G,
    ("rj45", Decimal("2.5")): ContainerEquipmentPort.PortType.RJ45_2G5,
    ("sfp", Decimal("1")): ContainerEquipmentPort.PortType.SFP_1G,
    ("sfp_plus", Decimal("10")): ContainerEquipmentPort.PortType.SFP_PLUS_10G,
    ("sfp_plus", Decimal("25")): ContainerEquipmentPort.PortType.SFP28_25G,
    ("qsfp_plus", Decimal("40")): ContainerEquipmentPort.PortType.QSFP_PLUS_40G,
    ("qsfp_plus", Decimal("100")): ContainerEquipmentPort.PortType.QSFP28_100G,
}
LEGACY_PROFILE = {
    ContainerEquipmentPort.PortType.RJ45_100M: ("rj45", Decimal("0.1")),
    ContainerEquipmentPort.PortType.RJ45_1G: ("rj45", Decimal("1")),
    ContainerEquipmentPort.PortType.RJ45_2G5: ("rj45", Decimal("2.5")),
    ContainerEquipmentPort.PortType.SFP_1G: ("sfp", Decimal("1")),
    ContainerEquipmentPort.PortType.SFP_PLUS_10G: ("sfp_plus", Decimal("10")),
    ContainerEquipmentPort.PortType.SFP28_25G: ("sfp_plus", Decimal("25")),
    ContainerEquipmentPort.PortType.QSFP_PLUS_40G: ("qsfp_plus", Decimal("40")),
    ContainerEquipmentPort.PortType.QSFP28_100G: ("qsfp_plus", Decimal("100")),
}


def _container(request, element_id):
    return get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type__in=[NetworkElement.ElementType.RACK, NetworkElement.ElementType.TOWER],
    )


def _equipment(container, equipment_id, lock=False):
    queryset = ContainerEquipment.objects
    if lock:
        queryset = queryset.select_for_update()
    return get_object_or_404(
        queryset.prefetch_related("ports"),
        pk=equipment_id,
        container=container,
        equipment_type__in=ALLOWED_EDIT_TYPES,
    )


def _is_port_linked(port_id: int) -> bool:
    return ContainerPortLink.objects.filter(
        Q(source_port_id=port_id) | Q(destination_port_id=port_id)
    ).exists()


def _profile_map(equipment):
    raw = (equipment.metadata or {}).get(PORT_PROFILE_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def _port_profile(port, profiles):
    current = profiles.get(str(port.id)) if isinstance(profiles, dict) else None
    if isinstance(current, dict):
        return current
    connector, speed = LEGACY_PROFILE.get(port.port_type, ("rj45", Decimal("1")))
    return {
        "connector_type": connector,
        "speed_gbps": decimal_payload(speed),
        "order": port.port_number or port.number,
    }


def _port_payload(port, profiles):
    profile = _port_profile(port, profiles)
    connector = str(profile.get("connector_type") or "")
    speed = profile.get("speed_gbps")
    return {
        "id": port.id,
        "label": port.label,
        "number": port.number,
        "order": int(profile.get("order") or port.port_number or port.number),
        "port_type": port.port_type,
        "port_type_label": port.get_port_type_display(),
        "connector_type": connector,
        "connector_type_label": CONNECTOR_LABELS.get(connector, port.get_port_type_display()),
        "speed_gbps": speed,
        "linked": _is_port_linked(port.id),
        "enabled": port.enabled,
    }


def _ports_payload(equipment):
    profiles = _profile_map(equipment)
    ports = list(equipment.ports.order_by("number", "id"))
    return {
        "version": VERSION,
        "equipment": {
            "id": equipment.id,
            "name": equipment.name,
            "type": equipment.equipment_type,
            "type_label": equipment.get_equipment_type_display(),
            "management_ip": str(equipment.management_ip or ""),
        },
        "ports": [_port_payload(port, profiles) for port in ports],
        "limits": {
            "minimum": 1,
            "maximum": 48 if equipment.equipment_type in {
                ContainerEquipment.EquipmentType.SWITCH,
                ContainerEquipment.EquipmentType.ROUTER,
            } else 32,
        },
        "connector_types": [
            {"value": "rj45", "label": "RJ45"},
            {"value": "sfp", "label": "SFP"},
            {"value": "sfp_plus", "label": "SFP+ / SFP28"},
            {"value": "qsfp_plus", "label": "QSFP+ / QSFP28"},
        ],
        "speed_options": [0.1, 1, 2.5, 10, 25, 40, 100],
        "radio_port_types": [
            {"value": value, "label": label}
            for value, label in ContainerEquipmentPort.PortType.choices
            if value in GENERIC_PORT_TYPES
        ],
    }


def _parse_speed(value):
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Velocidade inválida.") from exc


def _parse_rows(equipment, rows):
    if not isinstance(rows, list):
        raise ValueError("Envie a lista de portas.")
    maximum = 48 if equipment.equipment_type in {
        ContainerEquipment.EquipmentType.SWITCH,
        ContainerEquipment.EquipmentType.ROUTER,
    } else 32
    if not 1 <= len(rows) <= maximum:
        raise ValueError(f"Este equipamento deve possuir entre 1 e {maximum} portas.")
    existing = {port.id: port for port in equipment.ports.all()}
    parsed = []
    seen_existing = set()
    names = set()
    for order, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Porta {order}: formato inválido.")
        label = str(row.get("label") or row.get("name") or f"Porta {order}").strip()[:100]
        if not label:
            raise ValueError(f"Porta {order}: informe o nome.")
        key = label.casefold()
        if key in names:
            raise ValueError(f"Nome de porta duplicado: {label}.")
        names.add(key)
        raw_id = row.get("id")
        port = None
        if raw_id not in (None, "", 0, "0"):
            try:
                port_id = int(raw_id)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Porta {order}: ID inválido.") from exc
            port = existing.get(port_id)
            if not port or port_id in seen_existing:
                raise ValueError(f"Porta {order}: ID não pertence ao equipamento ou está repetido.")
            seen_existing.add(port_id)
        if equipment.equipment_type in RADIO_TYPES:
            port_type = str(row.get("port_type") or ContainerEquipmentPort.PortType.RJ45_1G)
            if port_type not in GENERIC_PORT_TYPES:
                raise ValueError(f"Porta {order}: tipo inválido para rádio/AP.")
            connector = ""
            speed = None
        else:
            connector = str(row.get("connector_type") or "rj45")
            if connector not in CONNECTOR_LABELS:
                raise ValueError(f"Porta {order}: conector inválido.")
            speed = _parse_speed(row.get("speed_gbps") or 1)
            try:
                port_type = CONNECTOR_SPEED_TO_PORT[(connector, speed)]
            except KeyError:
                # Mantém as mesmas conversões compatíveis já usadas pelo importador tipado.
                port_type = legacy_port_type(connector, speed)
        parsed.append({
            "port": port,
            "label": label,
            "order": order,
            "port_type": port_type,
            "connector": connector,
            "speed": speed,
        })
    return parsed, existing, seen_existing


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def equipment_ports_v078(request, element_id, equipment_id):
    container = _container(request, element_id)
    equipment = _equipment(container, equipment_id)
    if request.method == "GET":
        return JsonResponse(_ports_payload(equipment))
    if not can_edit_company(request.user, container.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    data = request.data if isinstance(request.data, dict) else {}
    try:
        with transaction.atomic():
            equipment = _equipment(container, equipment_id, lock=True)
            parsed, existing, seen_existing = _parse_rows(equipment, data.get("ports"))
            removed = [port for port_id, port in existing.items() if port_id not in seen_existing]
            linked_removed = [port.label for port in removed if _is_port_linked(port.id)]
            if linked_removed:
                return JsonResponse(
                    {"detail": "Desligue estas portas antes de removê-las: " + ", ".join(linked_removed)},
                    status=409,
                )
            if removed:
                ContainerEquipmentPort.objects.filter(id__in=[port.id for port in removed]).delete()

            profiles = _profile_map(equipment)
            for port in removed:
                profiles.pop(str(port.id), None)

            changed = []
            # Libera a restrição unique(equipment, number) antes da nova ordem.
            for temporary, item in enumerate([item for item in parsed if item["port"]], 30000):
                item["port"].number = temporary
                changed.append(item["port"])
            if changed:
                ContainerEquipmentPort.objects.bulk_update(changed, ["number"])

            for item in parsed:
                port = item["port"]
                if port is None:
                    port = ContainerEquipmentPort.objects.create(
                        equipment=equipment,
                        port_type=item["port_type"],
                        number=item["order"],
                        port_number=item["order"],
                        label=item["label"],
                        enabled=True,
                    )
                    item["port"] = port
                else:
                    port.label = item["label"]
                    port.port_type = item["port_type"]
                    port.number = item["order"]
                    port.port_number = item["order"]
                    port.enabled = True
                    port.save(update_fields=["label", "port_type", "number", "port_number", "enabled", "updated_at"])
                if equipment.equipment_type not in RADIO_TYPES:
                    previous = profiles.get(str(port.id), {}) if isinstance(profiles.get(str(port.id)), dict) else {}
                    profiles[str(port.id)] = {
                        **previous,
                        "connector_type": item["connector"],
                        "speed_gbps": decimal_payload(item["speed"]),
                        "order": item["order"],
                        "source_name": item["label"],
                    }

            metadata = dict(equipment.metadata or {})
            metadata["port_count"] = len(parsed)
            metadata["height_units"] = 1 if len(parsed) <= 16 else 2
            metadata["rack_form_factor"] = "19-inch"
            if equipment.equipment_type not in RADIO_TYPES:
                metadata[PORT_PROFILE_KEY] = profiles
            equipment.metadata = metadata
            equipment.save(update_fields=["metadata", "updated_at"])
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    return JsonResponse(_ports_payload(_equipment(container, equipment_id)))


def _cable_length_km(cable):
    if not cable or not cable.geometry:
        return 0.0
    try:
        return cable.geometry.transform(3857, clone=True).length / 1000.0
    except Exception:
        return 0.0


def _port_tx_power(port):
    equipment = port.equipment
    raw = dict((equipment.metadata or {}).get(PORT_POWER_KEY) or {})
    value = raw.get(str(port.id))
    if value not in (None, ""):
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    return float(equipment.tx_power_dbm) if equipment.tx_power_dbm is not None else None


def _splitter_loss(port):
    ratio = port.splitter.ratio
    if ratio in BALANCED_SPLITTER_LOSS_DB:
        return BALANCED_SPLITTER_LOSS_DB[ratio]
    if ratio in UNBALANCED_SPLITTER_LOSS_DB:
        try:
            return UNBALANCED_SPLITTER_LOSS_DB[ratio][int(port.number) - 1]
        except (IndexError, TypeError, ValueError):
            return 0.0
    return 0.0


def _trace_splitter_port(port, visited):
    key = ("splitter_port", port.id)
    if key in visited or len(visited) > 80:
        return [], 0.0, None
    visited.add(key)
    splitter = port.splitter
    if splitter.input_fiber_id:
        path, loss, tx = _trace_fiber(splitter.input_fiber, visited)
        # A atenuação do cabo de entrada só é somada se ainda não foi somada
        # pela etapa anterior. _trace_fiber retorna a potência no início do
        # segmento atual, como o cálculo legado.
        cable_loss = _cable_length_km(splitter.input_fiber.cable) * FIBER_ATTENUATION_DB_PER_KM
    elif splitter.input_splitter_port_id:
        path, loss, tx = _trace_splitter_port(splitter.input_splitter_port, visited)
        cable_loss = 0.0
    else:
        return [], 0.0, None
    return [*path, {
        "type": "splitter",
        "name": f"Splitter {splitter.ratio} · {splitter.tray.splice_box.name}",
    }], loss + cable_loss + _splitter_loss(port), tx


def _trace_fiber(fiber, visited=None):
    visited = set() if visited is None else visited
    key = ("fiber", fiber.id)
    if key in visited or len(visited) > 80:
        return [], 0.0, None
    visited.add(key)

    # Traseira do DIO -> frente do mesmo DIO -> PON da OLT.
    rear = ContainerPortLink.objects.filter(
        cable_fiber=fiber,
        destination_port__equipment__equipment_type=ContainerEquipment.EquipmentType.DIO,
    ).select_related(
        "destination_port__equipment",
        "source_port__equipment",
    ).first()
    if rear:
        front = ContainerPortLink.objects.filter(
            destination_port=rear.destination_port,
            source_port__equipment__equipment_type=ContainerEquipment.EquipmentType.OLT,
        ).select_related("source_port__equipment").first()
        if front:
            tx = _port_tx_power(front.source_port)
            return [
                {"type": "olt", "name": f"{front.source_port.equipment.name} · {front.source_port.label}"},
                {"type": "dio", "name": f"{rear.destination_port.equipment.name} · {rear.destination_port.label}"},
            ], DIO_PORT_LOSS_DB + FUSION_LOSS_DB, tx
        return [{"type": "dio", "name": rear.destination_port.equipment.name}], FUSION_LOSS_DB, None

    # Emenda é fisicamente bidirecional. O código anterior só aceitava
    # output_fiber=fiber, então uma fusão criada no sentido contrário quebrava
    # o orçamento mesmo com OLT/DIO perfeitamente ligados.
    splices = FiberSplice.objects.filter(
        Q(input_fiber=fiber) | Q(output_fiber=fiber)
    ).select_related(
        "input_fiber__cable", "output_fiber__cable", "splice_box"
    ).order_by("id")
    fallback = None
    for splice in splices:
        other = splice.output_fiber if splice.input_fiber_id == fiber.id else splice.input_fiber
        branch_visited = set(visited)
        path, loss, tx = _trace_fiber(other, branch_visited)
        branch_loss = loss + FUSION_LOSS_DB + _cable_length_km(other.cable) * FIBER_ATTENUATION_DB_PER_KM
        branch = ([*path, {"type": "splice_box", "name": splice.splice_box.name}], branch_loss, tx)
        if tx is not None:
            return branch
        if fallback is None:
            fallback = branch
    if fallback is not None:
        return fallback

    splitter_port = SpliceTraySplitterPort.objects.filter(output_fiber=fiber).select_related(
        "splitter__input_fiber__cable",
        "splitter__input_splitter_port__splitter",
        "splitter__tray__splice_box",
    ).first()
    if splitter_port:
        return _trace_splitter_port(splitter_port, visited)

    return [], 0.0, None


def _budget_payload(fiber, element=None):
    path, loss, tx = _trace_fiber(fiber)
    if element is not None and fiber.cable.destination_id == element.id:
        loss += _cable_length_km(fiber.cable) * FIBER_ATTENUATION_DB_PER_KM
        path = [*path, {"type": "cable", "name": fiber.cable.name}]
    return {
        "version": VERSION,
        "fiber_id": fiber.id,
        "path": path,
        "loss_db": round(loss, 2),
        "tx_dbm": round(tx, 2) if tx is not None else None,
        "budget_dbm": round(tx - loss, 2) if tx is not None else None,
        "estimated": True,
        "complete": tx is not None,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fiber_budget_v078(request, fiber_id):
    fiber = get_object_or_404(
        FiberStrand.objects.select_related("cable", "color"),
        pk=fiber_id,
        cable__in=scope_company_queryset(FiberCable.objects, request.user),
    )
    element = None
    raw_element = request.GET.get("element_id")
    if raw_element:
        element = scope_company_queryset(NetworkElement.objects, request.user).filter(
            pk=raw_element,
            project=fiber.cable.project,
        ).first()
    return JsonResponse(_budget_payload(fiber, element))
