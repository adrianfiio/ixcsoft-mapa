from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
import logging
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv46_address
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company, scope_company_queryset
from apps.network_map.device_type_yaml_v07551 import (
    CONNECTOR_LABELS,
    EquipmentYAMLV07551Error,
    ParsedEquipmentV07551,
    ParsedPortV07551,
    decimal_payload,
    legacy_port_type,
    parse_equipment_yaml_v07551,
)
from apps.network_map.models import (
    ContainerEquipment,
    ContainerEquipmentPort,
    ContainerPortLink,
    NetworkElement,
)


VERSION = "0.75.51"
PORT_PROFILE_KEY = "v07551_port_profiles"
EXTERNAL_KEY = "v07551_external_key"
MAX_PORTS = 256
SUPPORTED_CONNECTORS = tuple(CONNECTOR_LABELS)
EDITOR_SPEEDS = {Decimal("1"), Decimal("10"), Decimal("25"), Decimal("40"), Decimal("100")}
IMPORT_SPEEDS = EDITOR_SPEEDS | {Decimal("0.1"), Decimal("2.5")}
SPEED_CLASS = {
    Decimal("1"): "speed-1g",
    Decimal("10"): "speed-10g",
    Decimal("25"): "speed-25g",
    Decimal("40"): "speed-40g",
    Decimal("100"): "speed-100g",
}
logger = logging.getLogger(__name__)


LEGACY_PROFILES = {
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


def _switch(container, equipment_id, *, lock=False):
    queryset = ContainerEquipment.objects
    if lock:
        queryset = queryset.select_for_update()
    return get_object_or_404(
        queryset.prefetch_related("ports"),
        pk=equipment_id,
        container=container,
        equipment_type=ContainerEquipment.EquipmentType.SWITCH,
    )


def _can_edit(request, container):
    return can_edit_company(request.user, container.company_id)


def _json_body(request) -> dict[str, Any]:
    return request.data if isinstance(request.data, dict) else dict(request.data or {})


def _decimal_speed(value: Any, *, allowed: set[Decimal]) -> Decimal:
    try:
        speed = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Velocidade inválida.") from exc
    if speed not in allowed:
        values = ", ".join(str(item) for item in sorted(allowed))
        raise ValueError(f"Velocidade inválida. Use {values} Gbps.")
    return speed


def _normalize_connector(value: Any) -> str:
    raw = str(value or "").strip().casefold().replace(" ", "")
    aliases = {
        "rj45": "rj45",
        "sfp": "sfp",
        "sfp+": "sfp_plus",
        "sfpplus": "sfp_plus",
        "sfp_plus": "sfp_plus",
        "xfp": "xfp",
        "qsfp+": "qsfp_plus",
        "qsfpplus": "qsfp_plus",
        "qsfp_plus": "qsfp_plus",
    }
    connector = aliases.get(raw)
    if connector not in SUPPORTED_CONNECTORS:
        raise ValueError("Conector inválido. Use RJ45, SFP, SFP+, XFP ou QSFP+.")
    return connector


def _profile_map(equipment) -> dict[str, dict[str, Any]]:
    raw = (equipment.metadata or {}).get(PORT_PROFILE_KEY)
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for raw_id, profile in raw.items():
        if not isinstance(profile, dict):
            continue
        try:
            port_id = str(int(raw_id))
            connector = _normalize_connector(profile.get("connector_type"))
            speed = _decimal_speed(profile.get("speed_gbps"), allowed=IMPORT_SPEEDS)
        except (TypeError, ValueError):
            continue
        result[port_id] = {
            "connector_type": connector,
            "speed_gbps": decimal_payload(speed),
            "external_key": str(profile.get("external_key") or "").strip(),
            "source_name": str(profile.get("source_name") or "").strip(),
            "source_type": str(profile.get("source_type") or "").strip(),
            "description": str(profile.get("description") or "").strip(),
            "order": int(profile.get("order") or 0),
        }
    return result


def _legacy_profile(port) -> dict[str, Any]:
    connector, speed = LEGACY_PROFILES.get(port.port_type, ("rj45", Decimal("1")))
    return {
        "connector_type": connector,
        "speed_gbps": decimal_payload(speed),
        "external_key": port.label.casefold(),
        "source_name": port.label,
        "source_type": port.port_type,
        "description": "",
        "order": port.port_number or port.number,
    }


def _port_profile(port, profiles=None) -> dict[str, Any]:
    profiles = profiles if profiles is not None else _profile_map(port.equipment)
    return dict(profiles.get(str(port.id)) or _legacy_profile(port))


def _speed_decimal(profile: dict[str, Any]) -> Decimal | None:
    try:
        return Decimal(str(profile.get("speed_gbps")))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _speed_class(speed: Decimal | None) -> str:
    return SPEED_CLASS.get(speed, "")


def _all_profiles_for_equipment_ids(equipment_ids: set[int]) -> dict[int, dict[str, dict[str, Any]]]:
    if not equipment_ids:
        return {}
    rows = ContainerEquipment.objects.filter(id__in=equipment_ids).only("id", "metadata")
    return {item.id: _profile_map(item) for item in rows}


def _link_maps(ports: list[ContainerEquipmentPort]):
    port_ids = [port.id for port in ports]
    links = list(
        ContainerPortLink.objects.filter(
            Q(source_port_id__in=port_ids) | Q(destination_port_id__in=port_ids)
        ).select_related(
            "source_port__equipment",
            "destination_port__equipment",
        ).order_by("id")
    )
    by_port: dict[int, ContainerPortLink] = {}
    remote_equipment_ids: set[int] = set()
    for link in links:
        if link.source_port_id in port_ids:
            by_port.setdefault(link.source_port_id, link)
        if link.destination_port_id in port_ids:
            by_port.setdefault(link.destination_port_id, link)
        if link.source_port_id:
            remote_equipment_ids.add(link.source_port.equipment_id)
        if link.destination_port_id:
            remote_equipment_ids.add(link.destination_port.equipment_id)
    return by_port, _all_profiles_for_equipment_ids(remote_equipment_ids)


def _remote_for(port, link):
    if not link:
        return None
    if link.source_port_id == port.id:
        return link.destination_port
    if link.destination_port_id == port.id:
        return link.source_port
    return None


def _effective_speed(local_speed: Decimal | None, remote_speed: Decimal | None) -> Decimal | None:
    if local_speed is not None and remote_speed is not None:
        return min(local_speed, remote_speed)
    return local_speed if local_speed is not None else remote_speed


def _switch_payload(equipment):
    profiles = _profile_map(equipment)
    ports = list(equipment.ports.select_related("equipment").order_by("number", "id"))
    links, equipment_profiles = _link_maps(ports)
    rows = []
    for index, port in enumerate(ports, 1):
        profile = _port_profile(port, profiles)
        local_speed = _speed_decimal(profile)
        link = links.get(port.id)
        remote = _remote_for(port, link)
        remote_profile = None
        remote_speed = None
        if remote:
            remote_profile = _port_profile(
                remote,
                equipment_profiles.get(remote.equipment_id, {}),
            )
            remote_speed = _speed_decimal(remote_profile)
        effective = _effective_speed(local_speed, remote_speed) if link else None
        rows.append({
            "id": port.id,
            "name": port.label,
            "label": port.label,
            "number": port.number,
            "order": profile.get("order") or port.port_number or index,
            "connector_type": profile["connector_type"],
            "connector_type_label": CONNECTOR_LABELS[profile["connector_type"]],
            "speed_gbps": profile["speed_gbps"],
            "port_type": port.port_type,
            "port_type_label": port.get_port_type_display(),
            "enabled": port.enabled,
            "linked": bool(link),
            "link_id": link.id if link else None,
            "effective_speed_gbps": decimal_payload(effective) if effective is not None else None,
            "speed_class": _speed_class(effective),
            "remote_equipment": remote.equipment.name if remote else "",
            "remote_equipment_id": remote.equipment_id if remote else None,
            "remote_port": remote.label if remote else "",
            "external_key": profile.get("external_key") or "",
        })
    rows.sort(key=lambda item: (int(item["order"] or 0), int(item["number"] or 0), int(item["id"])))
    return {
        "version": VERSION,
        "equipment": {
            "id": equipment.id,
            "name": equipment.name,
            "vendor": equipment.vendor,
            "model": equipment.model,
            "management_ip": str(equipment.management_ip or ""),
            "port_count": len(rows),
        },
        "ports": rows,
        "connector_types": [
            {"value": value, "label": CONNECTOR_LABELS[value]}
            for value in SUPPORTED_CONNECTORS
        ],
        "speed_options": [1, 10, 25, 40, 100],
        "speed_colors": {
            "1": "#22c55e",
            "10": "#0ea5e9",
            "25": "#a855f7",
            "40": "#f97316",
            "100": "#ef4444",
        },
    }


def _save_profile_map(equipment, profiles, *, metadata_patch=None):
    metadata = dict(equipment.metadata or {})
    metadata[PORT_PROFILE_KEY] = profiles
    metadata.update(metadata_patch or {})
    equipment.metadata = metadata
    equipment.save(update_fields=["metadata", "updated_at"])


def _validate_editor_rows(equipment, raw_rows):
    if not isinstance(raw_rows, list) or not raw_rows or len(raw_rows) > MAX_PORTS:
        raise ValueError(f"Informe entre 1 e {MAX_PORTS} portas.")
    existing = {port.id: port for port in equipment.ports.all()}
    parsed = []
    seen_ids: set[int] = set()
    seen_names: set[str] = set()
    seen_orders: set[int] = set()
    for index, row in enumerate(raw_rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Porta #{index} inválida.")
        try:
            port_id = int(row.get("id"))
            order = int(row.get("order") or index)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"ID/order inválido na porta #{index}.") from exc
        if port_id not in existing or port_id in seen_ids:
            raise ValueError(f"Porta #{index} não pertence a este Switch ou está duplicada.")
        if order <= 0 or order > MAX_PORTS or order in seen_orders:
            raise ValueError(f"Ordem inválida ou duplicada na porta #{index}.")
        name = str(row.get("name") or row.get("label") or "").strip()
        if not name or len(name) > 100:
            raise ValueError(f"Informe um nome de até 100 caracteres na porta #{index}.")
        name_key = name.casefold()
        if name_key in seen_names:
            raise ValueError(f"Nome de porta duplicado: {name}.")
        connector = _normalize_connector(row.get("connector_type"))
        speed = _decimal_speed(row.get("speed_gbps"), allowed=EDITOR_SPEEDS)
        parsed.append((existing[port_id], name, connector, speed, order))
        seen_ids.add(port_id)
        seen_names.add(name_key)
        seen_orders.add(order)
    if seen_ids != set(existing):
        raise ValueError("Envie todas as portas do Switch para salvar a edição.")
    return sorted(parsed, key=lambda item: item[4])


@api_view(["GET", "PATCH", "POST"])
@permission_classes([IsAuthenticated])
def switch_hardware_v07551(request, element_id, equipment_id):
    container = _container(request, element_id)
    equipment = _switch(container, equipment_id)
    if request.method == "GET":
        return JsonResponse(_switch_payload(equipment))
    if not _can_edit(request, container):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)

    data = _json_body(request)
    action = str(data.get("action") or "save_ports").strip().lower()
    if action != "save_ports":
        return JsonResponse({"detail": "Ação inválida para o Switch."}, status=400)
    try:
        with transaction.atomic():
            equipment = _switch(container, equipment_id, lock=True)
            rows = _validate_editor_rows(equipment, data.get("ports"))
            profiles = _profile_map(equipment)
            # Libera a restrição unique(equipment, number) antes de reordenar.
            for temporary, (port, *_rest) in enumerate(rows, 30000):
                port.number = temporary
            ContainerEquipmentPort.objects.bulk_update([row[0] for row in rows], ["number"])
            changed_ports = []
            for port, name, connector, speed, order in rows:
                port.label = name
                port.number = order
                port.port_number = order
                port.port_type = legacy_port_type(connector, speed)
                changed_ports.append(port)
                previous = profiles.get(str(port.id), {})
                profiles[str(port.id)] = {
                    **previous,
                    "connector_type": connector,
                    "speed_gbps": decimal_payload(speed),
                    "external_key": str(previous.get("external_key") or name.casefold()),
                    "source_name": str(previous.get("source_name") or name),
                    "source_type": str(previous.get("source_type") or port.port_type),
                    "description": str(previous.get("description") or ""),
                    "order": order,
                }
            ContainerEquipmentPort.objects.bulk_update(
                changed_ports,
                ["label", "number", "port_number", "port_type", "enabled"],
            )
            _save_profile_map(
                equipment,
                profiles,
                metadata_patch={
                    "port_count": len(changed_ports),
                    "height_units": 1 if len(changed_ports) <= 16 else 2 if len(changed_ports) <= 24 else 3,
                    "rack_form_factor": "19-inch",
                },
            )
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    equipment = _switch(container, equipment_id)
    return JsonResponse(_switch_payload(equipment))


def _find_equipment(container, parsed: ParsedEquipmentV07551, name: str):
    if parsed.external_key:
        match = ContainerEquipment.objects.filter(
            container=container,
            metadata__contains={EXTERNAL_KEY: parsed.external_key},
        ).first()
        if match:
            return match
    return ContainerEquipment.objects.filter(container=container, name=name).first()


def _linked_port_ids(port_ids):
    if not port_ids:
        return set()
    pairs = ContainerPortLink.objects.filter(
        Q(source_port_id__in=port_ids) | Q(destination_port_id__in=port_ids)
    ).values_list("source_port_id", "destination_port_id")
    result = set()
    for source_id, destination_id in pairs:
        if source_id in port_ids:
            result.add(source_id)
        if destination_id in port_ids:
            result.add(destination_id)
    return result


def _port_lookup(existing_ports, profiles):
    by_key = {}
    by_name = {}
    for port in existing_ports:
        profile = profiles.get(str(port.id)) or _legacy_profile(port)
        external_key = str(profile.get("external_key") or "").casefold()
        if external_key:
            by_key.setdefault(external_key, port)
        by_name.setdefault(port.label.casefold(), port)
    return by_key, by_name


def _upsert_ports(equipment, parsed: ParsedEquipmentV07551, *, replace_ports: bool):
    existing_ports = list(equipment.ports.select_for_update().order_by("number", "id"))
    profiles = _profile_map(equipment)
    by_key, by_name = _port_lookup(existing_ports, profiles)
    desired: list[tuple[ContainerEquipmentPort, ParsedPortV07551, bool]] = []
    matched_ids: set[int] = set()
    created_count = 0
    updated_count = 0

    next_number = max([port.number for port in existing_ports] or [0]) + 1
    for parsed_port in parsed.ports:
        port = by_key.get(parsed_port.external_key.casefold()) or by_name.get(parsed_port.name.casefold())
        created = False
        if port is None:
            port = ContainerEquipmentPort.objects.create(
                equipment=equipment,
                port_type=parsed_port.port_type,
                number=next_number,
                port_number=next_number,
                label=parsed_port.name,
                enabled=parsed_port.enabled,
            )
            next_number += 1
            existing_ports.append(port)
            created = True
            created_count += 1
        else:
            updated_count += 1
        matched_ids.add(port.id)
        desired.append((port, parsed_port, created))

    absent = [port for port in existing_ports if port.id not in matched_ids]
    conflicts = []
    if replace_ports and absent:
        absent_ids = {port.id for port in absent}
        linked = _linked_port_ids(absent_ids)
        for port in absent:
            if port.id in linked:
                conflicts.append(f"{port.label}: porta ligada, mantida")
        deletable = [port.id for port in absent if port.id not in linked]
        if deletable:
            ContainerEquipmentPort.objects.filter(id__in=deletable).delete()
            for port_id in deletable:
                profiles.pop(str(port_id), None)
        absent = [port for port in absent if port.id in linked]

    ordered_ports = [item[0] for item in desired] + absent
    # Numeração temporária para uma reimportação poder mudar a ordem sem
    # colidir com unique(equipment, number).
    for temporary, port in enumerate(ordered_ports, 30000):
        port.number = temporary
    if ordered_ports:
        ContainerEquipmentPort.objects.bulk_update(ordered_ports, ["number"])

    changed = []
    for order, (port, parsed_port, _created) in enumerate(desired, 1):
        port.label = parsed_port.name
        port.port_type = parsed_port.port_type
        port.number = order
        port.port_number = order
        port.enabled = parsed_port.enabled
        changed.append(port)
        profiles[str(port.id)] = {
            "connector_type": parsed_port.connector_type,
            "speed_gbps": decimal_payload(parsed_port.speed_gbps),
            "external_key": parsed_port.external_key,
            "source_name": parsed_port.name,
            "source_type": parsed_port.source_type,
            "description": parsed_port.description,
            "order": order,
        }
    for offset, port in enumerate(absent, len(desired) + 1):
        port.number = offset
        port.port_number = offset
        changed.append(port)
        profile = profiles.get(str(port.id)) or _legacy_profile(port)
        profile["order"] = offset
        profiles[str(port.id)] = profile
    if changed:
        ContainerEquipmentPort.objects.bulk_update(
            changed,
            ["label", "port_type", "number", "port_number", "enabled"],
        )
    return {
        "created": created_count,
        "updated": updated_count,
        "retained": len(absent),
        "conflicts": conflicts,
        "profiles": profiles,
        "total": len(changed),
    }


def _save_equipment_from_yaml(container, parsed, *, name_override="", type_override="auto", replace_override=None):
    name = str(name_override or parsed.name).strip()
    if not name:
        raise ValueError("Informe o nome do equipamento.")
    selected_type = parsed.equipment_type if type_override in ("", "auto") else type_override
    if selected_type not in {
        ContainerEquipment.EquipmentType.SWITCH,
        ContainerEquipment.EquipmentType.ROUTER,
        ContainerEquipment.EquipmentType.FIREWALL,
    }:
        raise ValueError("O YAML tipado aceita Switch, Roteador ou Firewall.")
    equipment = _find_equipment(container, parsed, name)
    created_equipment = equipment is None
    if equipment and equipment.equipment_type != selected_type:
        raise ValueError(
            f"{name}: já existe como {equipment.get_equipment_type_display()}, não como {selected_type}."
        )
    management_ip = parsed.management_ip or None
    if management_ip:
        try:
            validate_ipv46_address(management_ip)
        except ValidationError as exc:
            raise ValueError(f"{name}: IP de gerência inválido.") from exc

    if equipment is None:
        equipment = ContainerEquipment.objects.create(
            company=container.company,
            container=container,
            name=name,
            description=parsed.comments,
            equipment_type=selected_type,
            management_ip=management_ip,
            provisioning_mode=ContainerEquipment.ProvisioningMode.MANUAL,
            vendor=parsed.manufacturer,
            model=parsed.model,
            metadata={},
        )
    else:
        equipment.name = name
        equipment.description = parsed.comments
        equipment.management_ip = management_ip
        equipment.vendor = parsed.manufacturer
        equipment.model = parsed.model
        equipment.save(update_fields=[
            "name", "description", "management_ip", "vendor", "model", "updated_at"
        ])

    replace_ports = parsed.replace_ports if replace_override is None else bool(replace_override)
    result = _upsert_ports(equipment, parsed, replace_ports=replace_ports)
    metadata = dict(equipment.metadata or {})
    metadata.update({
        EXTERNAL_KEY: parsed.external_key,
        "device_type": parsed.payload(),
        "source_format": parsed.source_format,
        PORT_PROFILE_KEY: result.pop("profiles"),
        "port_count": result["total"],
        "height_units": 1 if result["total"] <= 16 else 2 if result["total"] <= 24 else 3,
        "rack_form_factor": "19-inch",
        "canvas_renderer": "default",
    })
    equipment.metadata = metadata
    equipment.save(update_fields=["metadata", "updated_at"])
    return equipment, created_equipment, result


def _bool_from_request(value, default=None):
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "sim", "on"}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_equipment_yaml_v07551(request, element_id):
    container = _container(request, element_id)
    if not _can_edit(request, container):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"detail": "Selecione um arquivo YAML/YML."}, status=400)
    try:
        parsed_document = parse_equipment_yaml_v07551(upload.read())
    except EquipmentYAMLV07551Error as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    action = str(request.data.get("action") or "preview").strip().casefold()
    type_override = str(request.data.get("equipment_type") or "auto").strip().casefold()
    preview = parsed_document.equipments[0].payload()
    preview["equipment_type"] = (
        preview["equipment_type"] if type_override in ("", "auto") else type_override
    )
    preview["equipment_type_label"] = dict(ContainerEquipment.EquipmentType.choices).get(
        preview["equipment_type"], preview["equipment_type"].upper()
    )
    preview["expanded_interface_count"] = len(preview["interfaces"])
    preview["equipment_count"] = len(parsed_document.equipments)
    preview["equipments"] = [item.payload() for item in parsed_document.equipments]
    if action == "preview":
        return JsonResponse({"version": VERSION, "preview": preview})
    if action != "import":
        return JsonResponse({"detail": "Ação inválida."}, status=400)

    name_override = str(request.data.get("name") or "").strip()
    if name_override and len(parsed_document.equipments) != 1:
        return JsonResponse(
            {"detail": "O campo nome só pode sobrescrever um YAML com um equipamento."},
            status=400,
        )
    replace_override = _bool_from_request(request.data.get("replace_ports"), default=None)
    report = {
        "equipments_created": 0,
        "equipments_updated": 0,
        "ports_created": 0,
        "ports_updated": 0,
        "ports_retained": 0,
        "conflicts": [],
    }
    saved = []
    try:
        with transaction.atomic():
            for parsed in parsed_document.equipments:
                equipment, created, result = _save_equipment_from_yaml(
                    container,
                    parsed,
                    name_override=name_override,
                    type_override=type_override,
                    replace_override=replace_override,
                )
                saved.append(equipment)
                report["equipments_created" if created else "equipments_updated"] += 1
                report["ports_created"] += result["created"]
                report["ports_updated"] += result["updated"]
                report["ports_retained"] += result["retained"]
                report["conflicts"].extend(
                    f"{equipment.name}: {message}" for message in result["conflicts"]
                )
    except (ValueError, ValidationError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    except IntegrityError:
        logger.exception("Conflito ao importar YAML v0.75.51 no container %s", container.id)
        return JsonResponse(
            {"detail": "Conflito de nome, porta ou ordem durante a importação do YAML."},
            status=409,
        )
    except Exception:
        logger.exception("Erro inesperado ao importar YAML v0.75.51 no container %s", container.id)
        return JsonResponse(
            {"detail": "Falha interna ao importar o YAML; consulte os logs do servidor."},
            status=500,
        )

    first = saved[0]
    return JsonResponse(
        {
            "version": VERSION,
            "created": {
                "id": first.id,
                "name": first.name,
                "ports_created": report["ports_created"],
                "equipment_type": first.equipment_type,
                "renderer": (first.metadata or {}).get("canvas_renderer", "default"),
            },
            "preview": preview,
            "report": report,
            "equipments": [
                {"id": item.id, "name": item.name, "equipment_type": item.equipment_type}
                for item in saved
            ],
        },
        status=201,
    )
