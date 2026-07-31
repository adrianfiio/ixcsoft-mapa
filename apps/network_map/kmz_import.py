from __future__ import annotations

import io
import math
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable
from xml.etree import ElementTree

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_KML_BYTES = 50 * 1024 * 1024
SUPPORTED_FIBER_COUNTS = (1, 2, 4, 6, 8, 12, 16, 24, 36, 48, 72, 96, 144, 288)

NUMERIC_NAME_RE = re.compile(r"^\s*\d+(?:[\s._/-]+\d+)*\s*$")
FIBER_COUNT_RE = re.compile(
    r"(?<!\d)(1|2|4|6|8|12|16|24|36|48|72|96|144|288)\s*(?:fo|f|fibras?)\b",
    re.I,
)
METERS_RE = re.compile(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(?:m|mts?|metros?)\b", re.I)
PREFIX_RE = re.compile(r"^\s*([A-Za-zÀ-ÿ]{2,20})[\s._/-]*", re.UNICODE)
ROUTE_RE = re.compile(r"(?:^|\s|[-_/])rota(?:\s|[-_/]|$)", re.I)

POINT_ALIASES = {
    "cto": "cto",
    "nap": "cto",
    "ceo": "splice_box",
    "cdo": "splice_box",
    "ce": "splice_box",
    "emenda": "splice_box",
    "caixa de emenda": "splice_box",
    "poste": "pole",
    "pop": "pop",
    "cpd": "pop",
    "rack": "rack",
    "torre": "tower",
    "olt": "olt",
    "dio": "dio",
}
RESERVE_ALIASES = ("rt", "reserva", "reserva tecnica", "reserva técnica", "sobra")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFD", value or "")
    return "".join(char for char in value if unicodedata.category(char) != "Mn").casefold().strip()


# Compatibilidade com a v0.2/v0.3.
_normalize = normalize


def child_text(element, name: str) -> str:
    for child in element:
        if local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def parse_coordinates(text: str | None) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for raw in (text or "").replace("\n", " ").split():
        values = raw.split(",")
        if len(values) < 2:
            continue
        try:
            longitude, latitude = float(values[0]), float(values[1])
        except (TypeError, ValueError):
            continue
        if -180 <= longitude <= 180 and -90 <= latitude <= 90:
            result.append((longitude, latitude))
    return result


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 6371008.8 * 2 * math.asin(min(1, math.sqrt(value)))


def line_length_m(coordinates: Iterable[tuple[float, float]]) -> float:
    points = list(coordinates)
    return sum(haversine_m(points[index - 1], points[index]) for index in range(1, len(points)))


def kml_color_to_hex(value: str | None) -> dict:
    """KML usa AABBGGRR; CSS usa #RRGGBB."""
    value = (value or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{8}", value):
        return {"kml": value or None, "hex": None, "opacity": None}
    alpha, blue, green, red = value[0:2], value[2:4], value[4:6], value[6:8]
    return {
        "kml": value,
        "hex": f"#{red}{green}{blue}",
        "opacity": round(int(alpha, 16) / 255, 3),
    }


def read_kml_bytes(upload) -> bytes:
    content = upload.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("O arquivo excede o limite de 20 MB.")
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = [
                item
                for item in archive.infolist()
                if item.filename.lower().endswith(".kml")
                and item.file_size <= MAX_KML_BYTES
            ]
            if not members:
                raise ValueError("O KMZ não contém um arquivo KML válido.")
            # Alguns KMZ possuem mais de um KML; o maior normalmente é o documento principal.
            content = archive.read(max(members, key=lambda item: item.file_size))
    if len(content) > MAX_KML_BYTES:
        raise ValueError("O KML interno excede o limite permitido.")
    return content


@dataclass
class ParsedPlacemark:
    source_id: str
    name: str
    geometry_type: str
    folder_path: list[str]
    coordinates: list[tuple[float, float]]
    style_url: str = ""
    color: dict = field(default_factory=dict)
    width: float | None = None
    description: str = ""

    @property
    def folder_key(self) -> str:
        return " / ".join(self.folder_path)

    @property
    def length_m(self) -> float:
        return line_length_m(self.coordinates) if self.geometry_type == "LineString" else 0.0


class KMZAnalyzer:
    def __init__(self, root):
        self.root = root
        self.parent_map = {child: parent for parent in root.iter() for child in parent}
        self.styles = self._read_styles()
        self.style_maps = self._read_style_maps()

    @classmethod
    def from_upload(cls, upload) -> "KMZAnalyzer":
        content = read_kml_bytes(upload)
        try:
            return cls(ElementTree.fromstring(content))
        except ElementTree.ParseError as exc:
            raise ValueError("KML inválido ou corrompido.") from exc

    def _read_styles(self) -> dict[str, dict]:
        styles: dict[str, dict] = {}
        for element in self.root.iter():
            if local_name(element.tag) != "Style" or not element.attrib.get("id"):
                continue
            record = {"color": None, "width": None}
            for child in element.iter():
                if local_name(child.tag) != "LineStyle":
                    continue
                for item in child:
                    if local_name(item.tag) == "color":
                        record["color"] = (item.text or "").strip()
                    elif local_name(item.tag) == "width":
                        try:
                            record["width"] = float((item.text or "").strip())
                        except ValueError:
                            pass
            styles[element.attrib["id"]] = record
        return styles

    def _read_style_maps(self) -> dict[str, dict[str, str]]:
        result: dict[str, dict[str, str]] = {}
        for element in self.root.iter():
            if local_name(element.tag) != "StyleMap" or not element.attrib.get("id"):
                continue
            pairs: dict[str, str] = {}
            for pair in element:
                if local_name(pair.tag) == "Pair":
                    pairs[child_text(pair, "key")] = child_text(pair, "styleUrl")
            result[element.attrib["id"]] = pairs
        return result

    def _folder_path(self, element) -> list[str]:
        result: list[str] = []
        current = self.parent_map.get(element)
        while current is not None:
            if local_name(current.tag) == "Folder":
                name = child_text(current, "name")
                if name:
                    result.append(name)
            current = self.parent_map.get(current)
        return list(reversed(result))

    def _style(self, style_url: str) -> dict:
        style_id = style_url.lstrip("#")
        if style_id in self.style_maps:
            mapped = self.style_maps[style_id].get("normal") or next(
                iter(self.style_maps[style_id].values()), ""
            )
            style_id = mapped.lstrip("#")
        return self.styles.get(style_id, {})

    def placemarks(self) -> list[ParsedPlacemark]:
        result: list[ParsedPlacemark] = []
        unnamed = 0
        placemarks = [item for item in self.root.iter() if local_name(item.tag) == "Placemark"]
        for index, placemark in enumerate(placemarks, 1):
            name = child_text(placemark, "name")
            if not name:
                unnamed += 1
                name = f"Sem nome {unnamed}"
            point_node = next(
                (item for item in placemark.iter() if local_name(item.tag) == "Point"),
                None,
            )
            line_node = next(
                (item for item in placemark.iter() if local_name(item.tag) == "LineString"),
                None,
            )
            geometry_type = "Unknown"
            coordinate_node = None
            if point_node is not None:
                geometry_type = "Point"
                coordinate_node = next(
                    (item for item in point_node.iter() if local_name(item.tag) == "coordinates"),
                    None,
                )
            elif line_node is not None:
                geometry_type = "LineString"
                coordinate_node = next(
                    (item for item in line_node.iter() if local_name(item.tag) == "coordinates"),
                    None,
                )
            coordinates = parse_coordinates(
                coordinate_node.text if coordinate_node is not None else ""
            )
            style_url = child_text(placemark, "styleUrl")
            style = self._style(style_url)
            result.append(
                ParsedPlacemark(
                    source_id=placemark.attrib.get("id") or f"placemark-{index}",
                    name=name,
                    geometry_type=geometry_type,
                    folder_path=self._folder_path(placemark),
                    coordinates=coordinates,
                    style_url=style_url,
                    color=kml_color_to_hex(style.get("color")),
                    width=style.get("width"),
                    description=child_text(placemark, "description"),
                )
            )
        return result

    @staticmethod
    def classify_point(name: str) -> dict:
        normalized = normalize(name)
        tokens = re.findall(r"[a-z0-9]+", normalized)
        token_set = set(tokens)

        reserve = normalized == "rt" or normalized.startswith("rt ") or any(
            alias in normalized for alias in RESERVE_ALIASES[1:]
        )
        if reserve:
            match = METERS_RE.search(name or "")
            return {
                "suggested_type": "technical_reserve",
                "confidence": 0.97,
                "reason": "alias_rt",
                "length_hint_m": float(match.group(1).replace(",", ".")) if match else None,
            }

        # Ordem é importante: CDO/CEO devem vencer a abreviação genérica CE.
        aliases = sorted(POINT_ALIASES.items(), key=lambda item: len(item[0]), reverse=True)
        for alias, element_type in aliases:
            normalized_alias = normalize(alias)
            if (
                normalized_alias in token_set
                or normalized.startswith(f"{normalized_alias}-")
                or normalized.startswith(f"{normalized_alias} ")
            ):
                confidence = 0.99 if normalized_alias in {"cto", "ceo", "cdo", "pop", "cpd"} else 0.92
                subtype = None
                if normalized_alias in {"ceo", "cdo"}:
                    subtype = normalized_alias
                return {
                    "suggested_type": element_type,
                    "confidence": confidence,
                    "reason": f"alias_{normalized_alias}",
                    "subtype_hint": subtype,
                }

        if NUMERIC_NAME_RE.fullmatch(name or ""):
            return {
                "suggested_type": "cto",
                "confidence": 0.35,
                "reason": "numeric_name",
            }

        prefix_match = PREFIX_RE.match(name or "")
        prefix = normalize(prefix_match.group(1)).upper() if prefix_match else ""
        return {
            "suggested_type": "unknown",
            "confidence": 0.0,
            "reason": "unknown",
            "prefix": prefix,
        }

    @staticmethod
    def classify_line(name: str) -> dict:
        normalized = normalize(name)
        fiber_match = FIBER_COUNT_RE.search(name or "")
        meters_match = METERS_RE.search(name or "")
        is_drop = "drop" in normalized
        is_reserve = any(alias in normalized for alias in ("cabo reserva", "reserva de cabo", "sobra de cabo"))
        fiber_hint = int(fiber_match.group(1)) if fiber_match else (1 if is_drop else None)
        profile = "reserve" if is_reserve else ("drop" if is_drop else "fiber")
        return {
            "suggested_kind": "technical_reserve_line" if is_reserve else "fiber_cable",
            "profile": profile,
            "fiber_count_hint": fiber_hint,
            "cable_type_hint": "drop" if is_drop else "distribution",
            "length_hint_m": float(meters_match.group(1).replace(",", ".")) if meters_match else None,
            "confidence": 0.99 if is_drop else (0.96 if is_reserve or fiber_match else 0.55),
        }

    def analyze(self, filename: str = "") -> dict:
        placemarks = self.placemarks()
        points = [item for item in placemarks if item.geometry_type == "Point" and item.coordinates]
        lines = [
            item
            for item in placemarks
            if item.geometry_type == "LineString" and len(item.coordinates) >= 2
        ]

        point_records: list[dict] = []
        point_groups = defaultdict(lambda: {"count": 0, "samples": [], "source_ids": []})
        for point in points:
            classification = self.classify_point(point.name)
            group_key = classification["reason"]
            if group_key == "unknown":
                group_key = f"prefix:{classification.get('prefix') or 'SEM_PREFIXO'}"
            record = {
                "source_id": point.source_id,
                "name": point.name,
                "folder_path": point.folder_path,
                "folder": point.folder_key,
                "coordinates": point.coordinates[0],
                "group_key": group_key,
                **classification,
            }
            point_records.append(record)
            group = point_groups[group_key]
            group["count"] += 1
            group["source_ids"].append(point.source_id)
            if len(group["samples"]) < 10:
                group["samples"].append(point.name)
            group["suggested_type"] = classification.get("suggested_type")
            group["confidence"] = max(group.get("confidence", 0), classification.get("confidence") or 0)
            if classification.get("subtype_hint"):
                group["subtype_hint"] = classification["subtype_hint"]
            if classification.get("length_hint_m"):
                group["length_hint_m"] = classification["length_hint_m"]

        line_records: list[dict] = []
        line_groups = defaultdict(
            lambda: {
                "count": 0,
                "total_length_m": 0.0,
                "samples": [],
                "folders": set(),
                "source_ids": [],
                "fiber_hints": Counter(),
                "type_hints": Counter(),
                "length_hints": [],
                "hex": None,
                "profile": "fiber",
            }
        )
        for line in lines:
            classification = self.classify_line(line.name)
            color_key = line.color.get("hex") or "SEM_COR"
            group_key = f"{color_key}::{classification['profile']}"
            record = {
                "source_id": line.source_id,
                "name": line.name,
                "folder_path": line.folder_path,
                "folder": line.folder_key,
                "coordinates": line.coordinates,
                "color": line.color,
                "width": line.width,
                "length_m": round(line.length_m, 2),
                "vertex_count": len(line.coordinates),
                "group_key": group_key,
                **classification,
            }
            line_records.append(record)
            group = line_groups[group_key]
            group["count"] += 1
            group["total_length_m"] += line.length_m
            group["folders"].add(line.folder_key)
            group["source_ids"].append(line.source_id)
            group["hex"] = line.color.get("hex")
            group["profile"] = classification["profile"]
            if classification.get("fiber_count_hint"):
                group["fiber_hints"][classification["fiber_count_hint"]] += 1
            if classification.get("cable_type_hint"):
                group["type_hints"][classification["cable_type_hint"]] += 1
            if classification.get("length_hint_m"):
                group["length_hints"].append(classification["length_hint_m"])
            if len(group["samples"]) < 10:
                group["samples"].append(line.name)

        folders = defaultdict(lambda: {"points": 0, "lines": 0, "composition": Counter()})
        for item in placemarks:
            for depth in range(1, len(item.folder_path) + 1):
                path = " / ".join(item.folder_path[:depth])
                record = folders[path]
                if item.geometry_type == "Point":
                    record["points"] += 1
                    record["composition"][self.classify_point(item.name).get("suggested_type") or "unknown"] += 1
                elif item.geometry_type == "LineString":
                    record["lines"] += 1

        folder_records = []
        for path, record in sorted(folders.items()):
            leaf = path.split(" / ")[-1]
            folder_records.append(
                {
                    "path": path,
                    "name": leaf,
                    "points": record["points"],
                    "lines": record["lines"],
                    "composition": dict(record["composition"]),
                    "route_candidate": bool(ROUTE_RE.search(leaf)),
                }
            )

        grouped_lines = []
        for key, record in line_groups.items():
            fiber_hint = record["fiber_hints"].most_common(1)[0][0] if record["fiber_hints"] else None
            cable_type = record["type_hints"].most_common(1)[0][0] if record["type_hints"] else "distribution"
            profile = record["profile"]
            if profile == "drop":
                default_action = "cable"
                fiber_hint = 1
                cable_type = "drop"
            elif profile == "reserve":
                default_action = "reserve_line"
            elif record["hex"] in {None, "#000000"}:
                default_action = "review"
            else:
                default_action = "cable"
            grouped_lines.append(
                {
                    "key": key,
                    "hex": record["hex"],
                    "profile": profile,
                    "count": record["count"],
                    "total_length_m": round(record["total_length_m"], 1),
                    "samples": record["samples"],
                    "folders": sorted(filter(None, record["folders"])),
                    "source_ids": record["source_ids"],
                    "suggested_fibers": fiber_hint,
                    "suggested_cable_type": cable_type,
                    "suggested_reserve_length_m": (
                        round(sum(record["length_hints"]) / len(record["length_hints"]), 1)
                        if record["length_hints"]
                        else None
                    ),
                    "default_action": default_action,
                }
            )

        grouped_points = [
            {"key": key, **record}
            for key, record in sorted(point_groups.items(), key=lambda item: (-item[1]["count"], item[0]))
        ]
        warnings = []
        unknown_count = sum(1 for item in point_records if item["suggested_type"] == "unknown")
        numeric_count = sum(1 for item in point_records if item["reason"] == "numeric_name")
        if unknown_count:
            warnings.append(f"{unknown_count} pontos desconhecidos precisam ser classificados ou ignorados.")
        if numeric_count:
            warnings.append(f"{numeric_count} nomes numéricos sugerem CTO, mas exigem confirmação.")
        if any(item["profile"] == "drop" for item in line_records):
            warnings.append("Linhas com nome DROP/01 FO foram separadas e sugeridas como cabo Drop de 1 fibra.")

        return {
            "schema_version": 4,
            "filename": filename,
            "summary": {
                "folders": len(folder_records),
                "placemarks": len(placemarks),
                "points": len(points),
                "lines": len(lines),
                "unknown_points": unknown_count,
                "numeric_points": numeric_count,
                "total_line_length_m": round(sum(item.length_m for item in lines), 1),
                "distinct_line_groups": len(grouped_lines),
            },
            "folders": folder_records,
            "line_groups": sorted(grouped_lines, key=lambda item: (-item["count"], item["key"])),
            "point_groups": grouped_points,
            "points": point_records,
            "lines": line_records,
            "warnings": warnings,
            "supported_fiber_counts": list(SUPPORTED_FIBER_COUNTS),
        }
