from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Iterable

import yaml


MAX_YAML_BYTES = 1024 * 1024
MAX_EQUIPMENTS = 32
MAX_PORTS_PER_EQUIPMENT = 256
_RANGE_PATTERN = re.compile(r"\[(\d+)-(\d+)\]")

# Valores persistidos nos metadados da porta. O PortType legado continua
# existindo para compatibilidade com as APIs e ligações já criadas.
CONNECTOR_LABELS = {
    "rj45": "RJ45",
    "sfp": "SFP",
    "sfp_plus": "SFP+",
    "xfp": "XFP",
    "qsfp_plus": "QSFP+",
}
DEFAULT_SPEEDS = {
    "rj45": Decimal("1"),
    "sfp": Decimal("1"),
    "sfp_plus": Decimal("10"),
    "xfp": Decimal("10"),
    "qsfp_plus": Decimal("40"),
}
SUPPORTED_SPEEDS = {
    Decimal("0.1"),  # compatibilidade com 100BASE-TX do importador anterior
    Decimal("1"),
    Decimal("2.5"),  # compatibilidade com portas multi-gig já existentes
    Decimal("10"),
    Decimal("25"),
    Decimal("40"),
    Decimal("100"),
}


class EquipmentYAMLV07551Error(ValueError):
    """Erro de validação de YAML seguro da MAP v0.75.51."""


@dataclass(frozen=True)
class ParsedPortV07551:
    name: str
    connector_type: str
    speed_gbps: Decimal
    order: int
    external_key: str
    source_type: str = ""
    description: str = ""
    enabled: bool = True

    @property
    def port_type(self) -> str:
        """PortType legado usado pelo modelo atual."""
        return legacy_port_type(self.connector_type, self.speed_gbps)

    def payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "connector_type": self.connector_type,
            "connector_type_label": CONNECTOR_LABELS[self.connector_type],
            "speed_gbps": decimal_payload(self.speed_gbps),
            "order": self.order,
            "external_key": self.external_key,
            "source_type": self.source_type,
            "description": self.description,
            "enabled": self.enabled,
            "port_type": self.port_type,
            "group_name": "Interfaces",
            "group_kind": "ethernet",
            "group_order": self.order,
            "warning": "",
        }


@dataclass(frozen=True)
class ParsedEquipmentV07551:
    name: str
    external_key: str
    equipment_type: str
    manufacturer: str
    model: str
    slug: str
    management_ip: str
    comments: str
    u_height: int | None
    is_full_depth: bool
    replace_ports: bool
    ports: tuple[ParsedPortV07551, ...]
    source_format: str
    source: dict[str, Any]

    def payload(self) -> dict[str, Any]:
        interfaces = [port.payload() for port in self.ports]
        return {
            "name": self.name,
            "external_key": self.external_key,
            "equipment_type": self.equipment_type,
            "suggested_equipment_type": self.equipment_type,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "slug": self.slug,
            "management_ip": self.management_ip,
            "comments": self.comments,
            "u_height": self.u_height,
            "is_full_depth": self.is_full_depth,
            "replace_ports": self.replace_ports,
            "source_format": self.source_format,
            "interfaces": interfaces,
            "ports": interfaces,
            "skipped_interfaces": [],
            "module_bays": [],
            "power_ports": [],
            "expanded_interface_count": len(interfaces),
        }


@dataclass(frozen=True)
class ParsedEquipmentDocumentV07551:
    equipments: tuple[ParsedEquipmentV07551, ...]

    def payload(self) -> dict[str, Any]:
        return {
            "equipment_count": len(self.equipments),
            "equipments": [equipment.payload() for equipment in self.equipments],
        }


def decimal_payload(value: Decimal) -> int | float:
    integral = value.to_integral_value()
    return int(integral) if value == integral else float(value)


def _text(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("name") or value.get("model") or value.get("slug") or ""
    return str(value or "").strip()


def _bounded_positive_int(value: Any, field_name: str, *, maximum: int) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise EquipmentYAMLV07551Error(f"{field_name} precisa ser um número inteiro.") from exc
    if parsed <= 0 or parsed > maximum:
        raise EquipmentYAMLV07551Error(f"{field_name} precisa estar entre 1 e {maximum}.")
    return parsed


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized or "equipamento"


def _normalize_connector(value: Any, *, source_type: str = "") -> str:
    raw = _text(value or source_type)
    normalized = re.sub(r"[^a-z0-9+]+", "", raw.casefold())
    aliases = {
        "rj45": "rj45",
        "copper": "rj45",
        "ethernet": "rj45",
        "100basetx": "rj45",
        "100basetxpoe": "rj45",
        "1000baset": "rj45",
        "1000basetfixed": "rj45",
        "2.5gbaset": "rj45",
        "2g5baset": "rj45",
        "sfp": "sfp",
        "1000basex": "sfp",
        "1000basexsfp": "sfp",
        "1000basexgbic": "sfp",
        "sfp+": "sfp_plus",
        "sfpplus": "sfp_plus",
        "sfpp": "sfp_plus",
        "10gbasexsfpp": "sfp_plus",
        "10gbasexsfp+": "sfp_plus",
        "sfp28": "sfp_plus",
        "25gbasexsfp28": "sfp_plus",
        "xfp": "xfp",
        "10gbasexxfp": "xfp",
        "qsfp+": "qsfp_plus",
        "qsfpplus": "qsfp_plus",
        "qsfpp": "qsfp_plus",
        "40gbasexqsfpp": "qsfp_plus",
        "qsfp28": "qsfp_plus",
        "100gbasexqsfp28": "qsfp_plus",
    }
    if normalized in aliases:
        return aliases[normalized]
    # Nomes NetBox variam bastante entre fabricantes. A ordem importa:
    # QSFP antes de SFP e XFP antes do fallback genérico de 10G.
    if "qsfp" in normalized or normalized.startswith("40gbase") or normalized.startswith("100gbase"):
        return "qsfp_plus"
    if "xfp" in normalized:
        return "xfp"
    if "sfp28" in normalized or "sfp+" in raw.casefold() or "sfpp" in normalized:
        return "sfp_plus"
    if "sfp" in normalized or "gbic" in normalized or "1000basex" in normalized:
        return "sfp"
    if any(token in normalized for token in ("baset", "rj45", "copper", "ethernet", "gigabitethernet", "fastethernet")):
        return "rj45"
    raise EquipmentYAMLV07551Error(
        f"Conector não suportado: {raw or 'vazio'}. Use RJ45, SFP, SFP+, XFP ou QSFP+."
    )


def _speed_from_source_type(source_type: str, connector: str) -> Decimal:
    normalized = source_type.casefold().replace(" ", "")
    if any(token in normalized for token in ("100g", "qsfp28")):
        return Decimal("100")
    if any(token in normalized for token in ("40g", "qsfpp", "qsfp+")):
        return Decimal("40")
    if any(token in normalized for token in ("25g", "sfp28")):
        return Decimal("25")
    if any(token in normalized for token in ("10g", "xfp", "sfpp", "sfp+")):
        return Decimal("10")
    if any(token in normalized for token in ("2.5g", "2g5")):
        return Decimal("2.5")
    if "100base" in normalized or "fastethernet" in normalized:
        return Decimal("0.1")
    if any(token in normalized for token in ("1000", "1g", "gigabit", "sfp", "rj45")):
        return Decimal("1")
    return DEFAULT_SPEEDS[connector]


def _normalize_speed(value: Any, connector: str, *, source_type: str = "") -> Decimal:
    if value in (None, ""):
        return _speed_from_source_type(source_type, connector)
    raw = str(value).strip().casefold().replace(",", ".")
    raw = re.sub(r"\s*(g|gb|gbps|gbit/s)$", "", raw)
    try:
        speed = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise EquipmentYAMLV07551Error(f"Velocidade inválida: {value}.") from exc
    if speed not in SUPPORTED_SPEEDS:
        accepted = ", ".join(str(item) for item in sorted(SUPPORTED_SPEEDS))
        raise EquipmentYAMLV07551Error(
            f"Velocidade {speed} Gbps não suportada. Valores aceitos: {accepted}."
        )
    return speed


def legacy_port_type(connector: str, speed: Decimal) -> str:
    """Converte o perfil rico para o enum legado sem perder o perfil nos metadados."""
    if connector == "rj45":
        if speed == Decimal("0.1"):
            return "rj45_100m"
        if speed == Decimal("2.5"):
            return "rj45_2g5"
        return "rj45_1g"
    if speed >= Decimal("100"):
        return "qsfp28_100g"
    if speed >= Decimal("40"):
        return "qsfp_plus_40g"
    if speed >= Decimal("25"):
        return "sfp28_25g"
    if connector == "sfp" and speed <= Decimal("1"):
        return "sfp_1g"
    return "sfp_plus_10g"


def _expand_name(name: str) -> list[str]:
    match = _RANGE_PATTERN.search(name)
    if not match:
        return [name]
    start, end = int(match.group(1)), int(match.group(2))
    if start <= 0 or end < start:
        raise EquipmentYAMLV07551Error(f"Intervalo inválido na porta {name}.")
    if end - start + 1 > MAX_PORTS_PER_EQUIPMENT:
        raise EquipmentYAMLV07551Error(f"Intervalo muito grande na porta {name}.")
    return [name[: match.start()] + str(number) + name[match.end() :] for number in range(start, end + 1)]


def _port_external_key(row: dict[str, Any], name: str) -> str:
    explicit = _text(
        row.get("external_key")
        or row.get("key")
        or row.get("id")
        or row.get("interface_id")
    )
    return explicit or name.casefold()


def _port_rows(raw_rows: Any, *, source_format: str) -> tuple[ParsedPortV07551, ...]:
    if not isinstance(raw_rows, list):
        raise EquipmentYAMLV07551Error("O campo ports/interfaces precisa ser uma lista.")
    parsed: list[ParsedPortV07551] = []
    seen_names: set[str] = set()
    seen_keys: set[str] = set()
    for row_index, raw_row in enumerate(raw_rows, 1):
        if not isinstance(raw_row, dict):
            raise EquipmentYAMLV07551Error(f"Porta #{row_index} precisa ser um objeto.")
        source_name = _text(raw_row.get("name") or raw_row.get("label") or raw_row.get("port_name"))
        if not source_name:
            raise EquipmentYAMLV07551Error(f"Porta #{row_index} precisa ter name, label ou port_name.")
        source_type = _text(
            raw_row.get("source_type")
            or raw_row.get("connector_type")
            or raw_row.get("port_type")
            or raw_row.get("type")
        )
        connector = _normalize_connector(
            raw_row.get("connector_type")
            or raw_row.get("port_type")
            or raw_row.get("type"),
            source_type=source_type,
        )
        speed = _normalize_speed(
            raw_row.get("speed_gbps")
            or raw_row.get("speed")
            or raw_row.get("bandwidth")
            or raw_row.get("capacity_gbps"),
            connector,
            source_type=source_type,
        )
        description = _text(raw_row.get("description"))
        expanded_names = _expand_name(source_name)
        for offset, name in enumerate(expanded_names):
            name_key = name.casefold()
            external_key = _port_external_key(raw_row, name)
            if len(expanded_names) > 1 and external_key != name_key:
                external_key = f"{external_key}:{offset + 1}"
            stable_key = external_key.casefold()
            if name_key in seen_names:
                raise EquipmentYAMLV07551Error(f"Nome de porta duplicado após expansão: {name}.")
            if stable_key in seen_keys:
                raise EquipmentYAMLV07551Error(f"Chave de porta duplicada após expansão: {external_key}.")
            seen_names.add(name_key)
            seen_keys.add(stable_key)
            explicit_order = raw_row.get("order")
            try:
                order = int(explicit_order) + offset if explicit_order not in (None, "") else len(parsed) + 1
            except (TypeError, ValueError) as exc:
                raise EquipmentYAMLV07551Error(f"order inválido na porta {source_name}.") from exc
            if order <= 0:
                raise EquipmentYAMLV07551Error(f"order precisa ser positivo na porta {source_name}.")
            parsed.append(
                ParsedPortV07551(
                    name=name,
                    connector_type=connector,
                    speed_gbps=speed,
                    order=order,
                    external_key=external_key,
                    source_type=source_type,
                    description=description,
                    enabled=bool(raw_row.get("enabled", True)),
                )
            )
            if len(parsed) > MAX_PORTS_PER_EQUIPMENT:
                raise EquipmentYAMLV07551Error(
                    f"O equipamento excede {MAX_PORTS_PER_EQUIPMENT} portas após expandir intervalos."
                )
    if not parsed:
        raise EquipmentYAMLV07551Error("Nenhuma porta física compatível foi encontrada no YAML.")
    return tuple(sorted(parsed, key=lambda item: (item.order, item.name.casefold())))


def _generic_equipment_rows(document: dict[str, Any]) -> list[dict[str, Any]] | None:
    if "equipments" in document:
        rows = document.get("equipments")
    elif "equipment" in document:
        rows = document.get("equipment")
    else:
        return None
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        raise EquipmentYAMLV07551Error("equipment/equipments precisa ser um objeto ou uma lista.")
    return rows


def _parse_generic_equipment(row: dict[str, Any], index: int) -> ParsedEquipmentV07551:
    if not isinstance(row, dict):
        raise EquipmentYAMLV07551Error(f"equipment #{index} precisa ser um objeto.")
    equipment_type = _text(row.get("equipment_type") or row.get("type") or "switch").casefold()
    if equipment_type not in {"switch", "router", "firewall", "access_point", "ptp"}:
        raise EquipmentYAMLV07551Error(
            f"equipment #{index}: somente switch, router, firewall, access_point ou ptp são aceitos neste importador tipado."
        )
    name = _text(row.get("name") or row.get("model") or row.get("external_key"))
    if not name:
        raise EquipmentYAMLV07551Error(f"equipment #{index} precisa ter name.")
    external_key = _text(row.get("external_key") or row.get("key") or row.get("slug"))
    manufacturer = _text(row.get("vendor") or row.get("manufacturer")) or "Não informado"
    model = _text(row.get("model"))
    slug = _text(row.get("slug")) or _slug(external_key or name)
    ports = _port_rows(row.get("ports") if "ports" in row else row.get("interfaces"), source_format="equipment-v07551")
    return ParsedEquipmentV07551(
        name=name,
        external_key=external_key,
        equipment_type=equipment_type,
        manufacturer=manufacturer,
        model=model,
        slug=slug,
        management_ip=_text(row.get("management_ip") or row.get("ip")),
        comments=_text(row.get("comments") or row.get("description")),
        u_height=_bounded_positive_int(row.get("u_height"), f"equipment #{index}.u_height", maximum=64),
        is_full_depth=bool(row.get("is_full_depth", False)),
        replace_ports=bool(row.get("replace_ports", False)),
        ports=ports,
        source_format="equipment-v07551",
        source=row,
    )


def _parse_netbox_device_type(document: dict[str, Any]) -> ParsedEquipmentV07551:
    model = _text(document.get("model"))
    if not model:
        raise EquipmentYAMLV07551Error("O campo model é obrigatório no device type YAML.")
    manufacturer = _text(document.get("manufacturer")) or "Não informado"
    slug = _text(document.get("slug")) or _slug(model)
    interfaces = document.get("interfaces") or []
    # Interfaces virtuais continuam ignoradas, como no importador anterior.
    physical_rows = []
    virtual_tokens = {"virtual", "bridge", "lag", "l2vlan", "l3ipvlan", "tunnel", "other"}
    for row in interfaces if isinstance(interfaces, list) else []:
        if not isinstance(row, dict):
            physical_rows.append(row)
            continue
        source_type = _text(row.get("type")).casefold()
        if source_type in virtual_tokens:
            continue
        physical_rows.append(row)
    ports = _port_rows(physical_rows, source_format="netbox-device-type-yaml")
    return ParsedEquipmentV07551(
        name=model,
        external_key=slug,
        equipment_type="switch",
        manufacturer=manufacturer,
        model=model,
        slug=slug,
        management_ip="",
        comments=_text(document.get("comments")),
        u_height=_bounded_positive_int(document.get("u_height"), "u_height", maximum=64),
        is_full_depth=bool(document.get("is_full_depth", False)),
        replace_ports=bool(document.get("replace_ports", False)),
        ports=ports,
        source_format="netbox-device-type-yaml",
        source=document,
    )


def parse_equipment_yaml_v07551(content: bytes | str) -> ParsedEquipmentDocumentV07551:
    raw = content.encode("utf-8") if isinstance(content, str) else bytes(content)
    if len(raw) > MAX_YAML_BYTES:
        raise EquipmentYAMLV07551Error("O YAML excede o limite de 1 MB.")
    try:
        document = yaml.safe_load(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise EquipmentYAMLV07551Error("YAML inválido ou não codificado em UTF-8.") from exc
    if not isinstance(document, dict):
        raise EquipmentYAMLV07551Error("O YAML deve conter um objeto na raiz.")

    generic_rows = _generic_equipment_rows(document)
    if generic_rows is not None:
        if not generic_rows:
            raise EquipmentYAMLV07551Error("A lista de equipamentos está vazia.")
        if len(generic_rows) > MAX_EQUIPMENTS:
            raise EquipmentYAMLV07551Error(
                f"O YAML excede o limite de {MAX_EQUIPMENTS} equipamentos por importação."
            )
        equipments = tuple(
            _parse_generic_equipment(row, index)
            for index, row in enumerate(generic_rows, 1)
        )
    else:
        equipments = (_parse_netbox_device_type(document),)
    return ParsedEquipmentDocumentV07551(equipments=equipments)
