from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

import yaml

from apps.network_map.models import ContainerEquipment, ContainerEquipmentPort

MAX_DEVICE_TYPE_YAML_BYTES = 1024 * 1024
MAX_EXPANDED_INTERFACES = 256
_RANGE_PATTERN = re.compile(r"\[(\d+)-(\d+)\]")
_SLOT_PATTERN = re.compile(r"\bslot\s*(\d+)\b", re.IGNORECASE)
_PORT_SLOT_PATTERN = re.compile(r"\b(?:PON|ETH|GE|XGE|SFP\+?)\s*(\d+)\s*/", re.IGNORECASE)


class DeviceTypeYAMLError(ValueError):
    """Raised when a device-type YAML cannot be safely imported."""


@dataclass(frozen=True)
class ParsedPowerPort:
    name: str
    source_type: str
    description: str = ""


@dataclass(frozen=True)
class ParsedModuleBay:
    name: str
    position: int | None = None
    description: str = ""


@dataclass(frozen=True)
class ParsedInterface:
    name: str
    source_name: str
    source_type: str
    port_type: str | None
    enabled: bool = True
    management_only: bool = False
    description: str = ""
    group_name: str = "Interfaces"
    group_kind: str = "interface"
    group_order: int = 9999
    warning: str = ""


@dataclass(frozen=True)
class ParsedDeviceType:
    manufacturer: str
    model: str
    slug: str
    suggested_equipment_type: str
    u_height: int | None
    is_full_depth: bool
    comments: str
    power_ports: tuple[ParsedPowerPort, ...]
    module_bays: tuple[ParsedModuleBay, ...]
    interfaces: tuple[ParsedInterface, ...]
    skipped_interfaces: tuple[ParsedInterface, ...]
    source: dict[str, Any]

    def payload(self) -> dict[str, Any]:
        return {
            "manufacturer": self.manufacturer,
            "model": self.model,
            "slug": self.slug,
            "suggested_equipment_type": self.suggested_equipment_type,
            "u_height": self.u_height,
            "is_full_depth": self.is_full_depth,
            "comments": self.comments,
            "power_ports": [asdict(item) for item in self.power_ports],
            "module_bays": [asdict(item) for item in self.module_bays],
            "interfaces": [asdict(item) for item in self.interfaces],
            "skipped_interfaces": [asdict(item) for item in self.skipped_interfaces],
        }


EXACT_INTERFACE_TYPE_MAP = {
    "100base-tx": ContainerEquipmentPort.PortType.RJ45_100M,
    "100base-tx-poe": ContainerEquipmentPort.PortType.RJ45_100M,
    "1000base-t": ContainerEquipmentPort.PortType.RJ45_1G,
    "1000base-t-fixed": ContainerEquipmentPort.PortType.RJ45_1G,
    "1000base-x-gbic": ContainerEquipmentPort.PortType.SFP_1G,
    "1000base-x-sfp": ContainerEquipmentPort.PortType.SFP_1G,
    "10gbase-x-sfpp": ContainerEquipmentPort.PortType.SFP_PLUS_10G,
    "10gbase-x-xfp": ContainerEquipmentPort.PortType.SFP_PLUS_10G,
    "10gbase-x-x2": ContainerEquipmentPort.PortType.SFP_PLUS_10G,
    "10gbase-x-xenpak": ContainerEquipmentPort.PortType.SFP_PLUS_10G,
    "ieee802.11a": ContainerEquipmentPort.PortType.WIRELESS,
    "ieee802.11b": ContainerEquipmentPort.PortType.WIRELESS,
    "ieee802.11g": ContainerEquipmentPort.PortType.WIRELESS,
    "ieee802.11n": ContainerEquipmentPort.PortType.WIRELESS,
    "ieee802.11ac": ContainerEquipmentPort.PortType.WIRELESS,
    "ieee802.11ax": ContainerEquipmentPort.PortType.WIRELESS,
    "wireless": ContainerEquipmentPort.PortType.WIRELESS,
    "gpon": ContainerEquipmentPort.PortType.PON,
    "xg-pon": ContainerEquipmentPort.PortType.PON,
    "xgs-pon": ContainerEquipmentPort.PortType.PON,
    "pon": ContainerEquipmentPort.PortType.PON,
}

VIRTUAL_INTERFACE_TYPES = {
    "virtual", "bridge", "lag", "l2vlan", "l3ipvlan", "tunnel", "other",
}


def _text(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("name") or value.get("model") or value.get("slug") or ""
    return str(value or "").strip()


def _optional_positive_int(value: Any, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise DeviceTypeYAMLError(f"O campo {field_name} precisa ser um número inteiro.") from exc
    if parsed <= 0:
        raise DeviceTypeYAMLError(f"O campo {field_name} precisa ser maior que zero.")
    return parsed


def _map_interface_type(source_type: str) -> tuple[str | None, str]:
    normalized = source_type.strip().lower()
    if normalized in EXACT_INTERFACE_TYPE_MAP:
        return EXACT_INTERFACE_TYPE_MAP[normalized], ""
    if normalized in VIRTUAL_INTERFACE_TYPES:
        return None, "Interface virtual ignorada; preservada nos metadados."
    if "wireless" in normalized or "802.11" in normalized or normalized.startswith("wifi"):
        return ContainerEquipmentPort.PortType.WIRELESS, ""
    if "sfp+" in normalized or "sfpp" in normalized or normalized.startswith("10gbase-x"):
        return ContainerEquipmentPort.PortType.SFP_PLUS_10G, ""
    if "sfp" in normalized or "1000base-x" in normalized:
        return ContainerEquipmentPort.PortType.SFP_1G, ""
    if "1000" in normalized or "gigabit" in normalized:
        return ContainerEquipmentPort.PortType.RJ45_1G, ""
    if "100base" in normalized or "fastethernet" in normalized:
        return ContainerEquipmentPort.PortType.RJ45_100M, ""
    return None, f"Tipo de interface não suportado: {source_type or 'vazio'}."


def _expand_interface_name(name: str) -> list[str]:
    match = _RANGE_PATTERN.search(name)
    if not match:
        return [name]
    start, end = int(match.group(1)), int(match.group(2))
    if start <= 0 or end < start:
        raise DeviceTypeYAMLError(f"Intervalo inválido na interface: {name}.")
    count = end - start + 1
    if count > MAX_EXPANDED_INTERFACES:
        raise DeviceTypeYAMLError(f"Intervalo muito grande na interface: {name}.")
    return [name[:match.start()] + str(number) + name[match.end():] for number in range(start, end + 1)]


def _slot_number(name: str, description: str) -> int | None:
    for value, pattern in ((description, _SLOT_PATTERN), (name, _PORT_SLOT_PATTERN), (name, _SLOT_PATTERN)):
        match = pattern.search(value or "")
        if match:
            return int(match.group(1))
    return None


def _group_data(name: str, description: str, port_type: str | None) -> tuple[str, str, int]:
    slot = _slot_number(name, description)
    description = description.strip()
    if description:
        label = description
    elif slot is not None:
        label = f"Slot {slot}"
    elif port_type == ContainerEquipmentPort.PortType.PON:
        label = "PON"
    elif port_type in {ContainerEquipmentPort.PortType.SFP_1G, ContainerEquipmentPort.PortType.SFP_PLUS_10G}:
        label = "Uplinks"
    else:
        label = "Interfaces"
    kind = (
        "pon" if port_type == ContainerEquipmentPort.PortType.PON
        else "uplink" if port_type in {ContainerEquipmentPort.PortType.SFP_1G, ContainerEquipmentPort.PortType.SFP_PLUS_10G}
        else "ethernet"
    )
    return label, kind, slot if slot is not None else 9999


def _parse_named_rows(document: dict[str, Any], key: str, row_class):
    raw_rows = document.get(key) or []
    if not isinstance(raw_rows, list):
        raise DeviceTypeYAMLError(f"O campo {key} precisa ser uma lista.")
    result = []
    for index, row in enumerate(raw_rows, 1):
        if not isinstance(row, dict):
            raise DeviceTypeYAMLError(f"{key} #{index} precisa ser um objeto.")
        name = _text(row.get("name"))
        if not name:
            raise DeviceTypeYAMLError(f"{key} #{index} precisa ter name.")
        if row_class is ParsedPowerPort:
            result.append(row_class(name=name, source_type=_text(row.get("type")), description=_text(row.get("description"))))
        else:
            result.append(row_class(name=name, position=_slot_number(name, _text(row.get("description"))), description=_text(row.get("description"))))
    return tuple(result)


def _suggest_equipment_type(manufacturer: str, model: str, slug: str, interfaces: list[ParsedInterface]) -> str:
    searchable = f" {manufacturer} {model} {slug} ".lower()
    port_types = [item.port_type for item in interfaces]
    pon_count = sum(item == ContainerEquipmentPort.PortType.PON for item in port_types)
    if any(token in searchable for token in (" onu", " ont", "optical network unit")):
        return ContainerEquipment.EquipmentType.OTHER
    if " olt" in searchable or pon_count >= 4:
        return ContainerEquipment.EquipmentType.OLT
    if ContainerEquipmentPort.PortType.WIRELESS in port_types:
        wired = sum(item in {
            ContainerEquipmentPort.PortType.RJ45_100M,
            ContainerEquipmentPort.PortType.RJ45_1G,
            ContainerEquipmentPort.PortType.SFP_1G,
            ContainerEquipmentPort.PortType.SFP_PLUS_10G,
        } for item in port_types)
        return ContainerEquipment.EquipmentType.PTP if wired <= 2 else ContainerEquipment.EquipmentType.ACCESS_POINT
    ethernet_count = sum(item in {
        ContainerEquipmentPort.PortType.RJ45_100M,
        ContainerEquipmentPort.PortType.RJ45_1G,
        ContainerEquipmentPort.PortType.SFP_1G,
        ContainerEquipmentPort.PortType.SFP_PLUS_10G,
    } for item in port_types)
    if ethernet_count >= 4:
        return ContainerEquipment.EquipmentType.SWITCH
    return ContainerEquipment.EquipmentType.OTHER


def parse_device_type_yaml(content: bytes | str) -> ParsedDeviceType:
    raw = content.encode("utf-8") if isinstance(content, str) else bytes(content)
    if len(raw) > MAX_DEVICE_TYPE_YAML_BYTES:
        raise DeviceTypeYAMLError("O YAML excede o limite de 1 MB.")
    try:
        document = yaml.safe_load(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise DeviceTypeYAMLError("YAML inválido ou não codificado em UTF-8.") from exc
    if not isinstance(document, dict):
        raise DeviceTypeYAMLError("O YAML deve conter um único objeto de device type.")

    manufacturer = _text(document.get("manufacturer")) or "Não informado"
    model = _text(document.get("model"))
    slug = _text(document.get("slug"))
    if not model:
        raise DeviceTypeYAMLError("O campo model é obrigatório.")
    if not slug:
        slug = "-".join(model.lower().split())

    u_height = _optional_positive_int(document.get("u_height"), "u_height")
    is_full_depth = bool(document.get("is_full_depth", False))
    comments = _text(document.get("comments"))
    power_ports = _parse_named_rows(document, "power-ports", ParsedPowerPort)
    module_bays = _parse_named_rows(document, "module-bays", ParsedModuleBay)

    raw_interfaces = document.get("interfaces") or []
    if not isinstance(raw_interfaces, list):
        raise DeviceTypeYAMLError("O campo interfaces precisa ser uma lista.")

    interfaces: list[ParsedInterface] = []
    skipped: list[ParsedInterface] = []
    seen_names: set[str] = set()
    for index, raw_interface in enumerate(raw_interfaces, 1):
        if not isinstance(raw_interface, dict):
            raise DeviceTypeYAMLError(f"Interface #{index} precisa ser um objeto.")
        source_name = _text(raw_interface.get("name")) or f"Interface {index}"
        source_type = _text(raw_interface.get("type"))
        description = _text(raw_interface.get("description"))
        port_type, warning = _map_interface_type(source_type)
        expanded_names = _expand_interface_name(source_name)
        for expanded_name in expanded_names:
            key = expanded_name.casefold()
            if key in seen_names:
                raise DeviceTypeYAMLError(f"Nome de interface duplicado após expansão: {expanded_name}.")
            seen_names.add(key)
            group_name, group_kind, group_order = _group_data(expanded_name, description, port_type)
            parsed = ParsedInterface(
                name=expanded_name,
                source_name=source_name,
                source_type=source_type,
                port_type=port_type,
                enabled=bool(raw_interface.get("enabled", True)),
                management_only=bool(raw_interface.get("mgmt_only", False)),
                description=description,
                group_name=group_name,
                group_kind=group_kind,
                group_order=group_order,
                warning=warning,
            )
            (interfaces if port_type else skipped).append(parsed)
            if len(interfaces) + len(skipped) > MAX_EXPANDED_INTERFACES:
                raise DeviceTypeYAMLError(f"O YAML expandiu para mais de {MAX_EXPANDED_INTERFACES} interfaces.")

    if not interfaces:
        raise DeviceTypeYAMLError(
            "Nenhuma interface física compatível foi encontrada. Verifique os tipos das interfaces no YAML."
        )

    suggested = _suggest_equipment_type(manufacturer, model, slug, interfaces)
    return ParsedDeviceType(
        manufacturer=manufacturer,
        model=model,
        slug=slug,
        suggested_equipment_type=suggested,
        u_height=u_height,
        is_full_depth=is_full_depth,
        comments=comments,
        power_ports=power_ports,
        module_bays=module_bays,
        interfaces=tuple(interfaces),
        skipped_interfaces=tuple(skipped),
        source=document,
    )
