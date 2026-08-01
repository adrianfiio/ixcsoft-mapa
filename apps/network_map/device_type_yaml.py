from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import yaml

from apps.network_map.models import ContainerEquipment, ContainerEquipmentPort

MAX_DEVICE_TYPE_YAML_BYTES = 1024 * 1024


class DeviceTypeYAMLError(ValueError):
    """Raised when a device-type YAML cannot be safely imported."""


@dataclass(frozen=True)
class ParsedInterface:
    name: str
    source_type: str
    port_type: str | None
    enabled: bool = True
    management_only: bool = False
    description: str = ""
    warning: str = ""


@dataclass(frozen=True)
class ParsedDeviceType:
    manufacturer: str
    model: str
    slug: str
    suggested_equipment_type: str
    interfaces: tuple[ParsedInterface, ...]
    skipped_interfaces: tuple[ParsedInterface, ...]
    source: dict[str, Any]

    def payload(self) -> dict[str, Any]:
        return {
            "manufacturer": self.manufacturer,
            "model": self.model,
            "slug": self.slug,
            "suggested_equipment_type": self.suggested_equipment_type,
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
    "virtual",
    "bridge",
    "lag",
    "l2vlan",
    "l3ipvlan",
    "tunnel",
    "other",
}


def _text(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("name") or value.get("model") or value.get("slug") or ""
    return str(value or "").strip()


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


def _suggest_equipment_type(manufacturer: str, model: str, slug: str, interfaces: list[ParsedInterface]) -> str:
    searchable = f"{manufacturer} {model} {slug}".lower()
    port_types = [item.port_type for item in interfaces]
    if any(token in searchable for token in (" onu", "ont", "optical network unit")):
        return ContainerEquipment.EquipmentType.OTHER
    if ContainerEquipmentPort.PortType.WIRELESS in port_types:
        wired = sum(
            item in {
                ContainerEquipmentPort.PortType.RJ45_100M,
                ContainerEquipmentPort.PortType.RJ45_1G,
                ContainerEquipmentPort.PortType.SFP_1G,
                ContainerEquipmentPort.PortType.SFP_PLUS_10G,
            }
            for item in port_types
        )
        return (
            ContainerEquipment.EquipmentType.PTP
            if wired <= 2
            else ContainerEquipment.EquipmentType.ACCESS_POINT
        )
    ethernet_count = sum(
        item in {
            ContainerEquipmentPort.PortType.RJ45_100M,
            ContainerEquipmentPort.PortType.RJ45_1G,
            ContainerEquipmentPort.PortType.SFP_1G,
            ContainerEquipmentPort.PortType.SFP_PLUS_10G,
        }
        for item in port_types
    )
    if ethernet_count >= 4:
        return ContainerEquipment.EquipmentType.SWITCH
    return ContainerEquipment.EquipmentType.OTHER


def parse_device_type_yaml(content: bytes | str) -> ParsedDeviceType:
    if isinstance(content, str):
        raw = content.encode("utf-8")
    else:
        raw = bytes(content)
    if len(raw) > MAX_DEVICE_TYPE_YAML_BYTES:
        raise DeviceTypeYAMLError("O YAML excede o limite de 1 MB.")
    try:
        document = yaml.safe_load(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise DeviceTypeYAMLError("YAML inválido ou não codificado em UTF-8.") from exc
    if not isinstance(document, dict):
        raise DeviceTypeYAMLError("O YAML deve conter um único objeto de device type.")

    manufacturer = _text(document.get("manufacturer"))
    model = _text(document.get("model"))
    slug = _text(document.get("slug"))
    if not model:
        raise DeviceTypeYAMLError("O campo model é obrigatório.")
    if not manufacturer:
        manufacturer = "Não informado"
    if not slug:
        slug = "-".join(model.lower().split())

    raw_interfaces = document.get("interfaces") or []
    if not isinstance(raw_interfaces, list):
        raise DeviceTypeYAMLError("O campo interfaces precisa ser uma lista.")

    interfaces: list[ParsedInterface] = []
    skipped: list[ParsedInterface] = []
    seen_names: set[str] = set()
    for index, raw_interface in enumerate(raw_interfaces, 1):
        if not isinstance(raw_interface, dict):
            raise DeviceTypeYAMLError(f"Interface #{index} precisa ser um objeto.")
        name = _text(raw_interface.get("name")) or f"Interface {index}"
        if name.casefold() in seen_names:
            raise DeviceTypeYAMLError(f"Nome de interface duplicado: {name}.")
        seen_names.add(name.casefold())
        source_type = _text(raw_interface.get("type"))
        port_type, warning = _map_interface_type(source_type)
        parsed = ParsedInterface(
            name=name,
            source_type=source_type,
            port_type=port_type,
            enabled=bool(raw_interface.get("enabled", True)),
            management_only=bool(raw_interface.get("mgmt_only", False)),
            description=_text(raw_interface.get("description")),
            warning=warning,
        )
        (interfaces if port_type else skipped).append(parsed)

    if not interfaces:
        raise DeviceTypeYAMLError(
            "Nenhuma interface física compatível foi encontrada. "
            "Verifique os tipos das interfaces no YAML."
        )

    suggested = _suggest_equipment_type(manufacturer, model, slug, interfaces)
    return ParsedDeviceType(
        manufacturer=manufacturer,
        model=model,
        slug=slug,
        suggested_equipment_type=suggested,
        interfaces=tuple(interfaces),
        skipped_interfaces=tuple(skipped),
        source=document,
    )
