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
SUPPORTED_FIBER_COUNTS = (2, 4, 6, 8, 12, 16, 24, 36, 48, 72, 96, 144, 288)

NUMERIC_NAME_RE = re.compile(r"^\s*\d+(?:[\s._/-]+\d+)*\s*$")
FIBER_COUNT_RE = re.compile(r"(?<!\d)(2|4|6|8|12|16|24|36|48|72|96|144|288)\s*(?:fo|f|fibras?)\b", re.I)
METERS_RE = re.compile(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(?:m|mts?|metros?)\b", re.I)
PREFIX_RE = re.compile(r"^\s*([A-Za-zÀ-ÿ]{2,12})[\s._/-]*", re.UNICODE)

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


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFD", value or "")
    return "".join(char for char in value if unicodedata.category(char) != "Mn").casefold().strip()


def _child_text(element, name: str) -> str:
    for child in element:
        if _local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _coordinates(text: str | None) -> list[tuple[float, float]]:
    result = []
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


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371008.8 * 2 * math.asin(min(1, math.sqrt(value)))


def line_length_m(coordinates: Iterable[tuple[float, float]]) -> float:
    points = list(coordinates)
    return sum(_haversine_m(points[index - 1], points[index]) for index in range(1, len(points)))


def kml_color_to_hex(value: str | None) -> dict:
    """KML uses AABBGGRR, not web RRGGBB."""
    value = (value or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{8}", value):
        return {"kml": value or None, "hex": None, "opacity": None}
    alpha, blue, green, red = value[0:2], value[2:4], value[4:6], value[6:8]
    return {"kml": value, "hex": f"#{red}{green}{blue}", "opacity": round(int(alpha, 16) / 255, 3)}


def read_kml_bytes(upload) -> bytes:
    content = upload.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("O arquivo excede o limite de 20 MB.")
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = [
                item for item in archive.infolist()
                if item.filename.lower().endswith(".kml") and item.file_size <= MAX_KML_BYTES
            ]
            if not members:
                raise ValueError("O KMZ não contém um arquivo KML válido.")
            content = archive.read(members[0])
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
        styles = {}
        for element in self.root.iter():
            if _local_name(element.tag) != "Style" or not element.attrib.get("id"):
                continue
            record = {"color": None, "width": None}
            for child in element.iter():
                if _local_name(child.tag) != "LineStyle":
                    continue
                for item in child:
                    if _local_name(item.tag) == "color":
                        record["color"] = (item.text or "").strip()
                    elif _local_name(item.tag) == "width":
                        try:
                            record["width"] = float((item.text or "").strip())
                        except ValueError:
                            pass
            styles[element.attrib["id"]] = record
        return styles

    def _read_style_maps(self) -> dict[str, dict[str, str]]:
        result = {}
        for element in self.root.iter():
            if _local_name(element.tag) != "StyleMap" or not element.attrib.get("id"):
                continue
            pairs = {}
            for pair in element:
                if _local_name(pair.tag) == "Pair":
                    pairs[_child_text(pair, "key")] = _child_text(pair, "styleUrl")
            result[element.attrib["id"]] = pairs
        return result

    def _folder_path(self, element) -> list[str]:
        result = []
        current = self.parent_map.get(element)
        while current is not None:
            if _local_name(current.tag) == "Folder":
                name = _child_text(current, "name")
                if name:
                    result.append(name)
            current = self.parent_map.get(current)
        return list(reversed(result))

    def _style(self, style_url: str) -> dict:
        style_id = style_url.lstrip("#")
        if style_id in self.style_maps:
            mapped = self.style_maps[style_id].get("normal") or next(iter(self.style_maps[style_id].values()), "")
            style_id = mapped.lstrip("#")
        return self.styles.get(style_id, {})

    def placemarks(self) -> list[ParsedPlacemark]:
        result = []
        unnamed = 0
        for index, placemark in enumerate(
            item for item in self.root.iter() if _local_name(item.tag) == "Placemark"
        ):
            name = _child_text(placemark, "name")
            if not name:
                unnamed += 1
                name = f"Sem nome {unnamed}"
            point_node = next(
                (item for item in placemark.iter() if _local_name(item.tag) == "Point"), None
            )
            line_node = next(
                (item for item in placemark.iter() if _local_name(item.tag) == "LineString"), None
            )
            geometry_type = "Unknown"
            coordinate_node = None
            if point_node is not None:
                geometry_type = "Point"
                coordinate_node = next(
                    (item for item in point_node.iter() if _local_name(item.tag) == "coordinates"), None
                )
            elif line_node is not None:
                geometry_type = "LineString"
                coordinate_node = next(
                    (item for item in line_node.iter() if _local_name(item.tag) == "coordinates"), None
                )
            coordinates = _coordinates(coordinate_node.text if coordinate_node is not None else "")
            style_url = _child_text(placemark, "styleUrl")
            style = self._style(style_url)
            result.append(
                ParsedPlacemark(
                    source_id=placemark.attrib.get("id") or f"placemark-{index + 1}",
                    name=name,
                    geometry_type=geometry_type,
                    folder_path=self._folder_path(placemark),
                    coordinates=coordinates,
                    style_url=style_url,
                    color=kml_color_to_hex(style.get("color")),
                    width=style.get("width"),
                    description=_child_text(placemark, "description"),
                )
            )
        return result

    @staticmethod
    def classify_point(name: str) -> dict:
        normalized = _normalize(name)
        tokens = re.findall(r"[a-z0-9]+", normalized)
        token_set = set(tokens)

        reserve = normalized == "rt" or normalized.startswith("rt ") or any(
            alias in normalized for alias in RESERVE_ALIASES[1:]
        )
        if reserve:
            return {"suggested_type": "technical_reserve", "confidence": 0.96, "reason": "alias_rt"}

        for alias, element_type in POINT_ALIASES.items():
            normalized_alias = _normalize(alias)
            if normalized_alias in token_set or normalized.startswith(f"{normalized_alias}-") or normalized.startswith(f"{normalized_alias} "):
                confidence = 0.99 if normalized_alias in {"cto", "ceo", "cdo", "pop", "cpd"} else 0.92
                return {"suggested_type": element_type, "confidence": confidence, "reason": f"alias_{normalized_alias}"}

        if NUMERIC_NAME_RE.fullmatch(name or ""):
            return {"suggested_type": "cto", "confidence": 0.35, "reason": "numeric_name"}

        prefix_match = PREFIX_RE.match(name or "")
        return {
            "suggested_type": "unknown",
            "confidence": 0.0,
            "reason": "unknown",
            "prefix": _normalize(prefix_match.group(1)).upper() if prefix_match else "",
        }

    @staticmethod
    def classify_line(name: str) -> dict:
        normalized = _normalize(name)
        reserve = normalized == "rt" or normalized.startswith("rt ") or any(
            alias in normalized for alias in RESERVE_ALIASES[1:]
        )
        fiber_match = FIBER_COUNT_RE.search(name or "")
        meters_match = METERS_RE.search(name or "")
        return {
            "suggested_kind": "technical_reserve" if reserve else "fiber_cable",
            "fiber_count_hint": int(fiber_match.group(1)) if fiber_match else None,
            "length_hint_m": float(meters_match.group(1).replace(",", ".")) if meters_match else None,
            "confidence": 0.95 if reserve or fiber_match else 0.55,
        }

    def analyze(self, filename: str = "") -> dict:
        placemarks = self.placemarks()
        points = [item for item in placemarks if item.geometry_type == "Point" and item.coordinates]
        lines = [item for item in placemarks if item.geometry_type == "LineString" and len(item.coordinates) >= 2]

        folders = defaultdict(lambda: {"points": 0, "lines": 0, "children": set(), "sample_names": []})
        point_groups = defaultdict(lambda: {"count": 0, "samples": []})
        color_groups = defaultdict(lambda: {"count": 0, "total_length_m": 0.0, "samples": [], "folders": set(), "fiber_hints": Counter()})

        point_records = []
        for point in points:
            classification = self.classify_point(point.name)
            record = {
                "source_id": point.source_id,
                "name": point.name,
                "folder_path": point.folder_path,
                "coordinates": point.coordinates[0],
                **classification,
            }
            point_records.append(record)
            group_key = classification["reason"] if classification["reason"] != "unknown" else f"prefix:{classification.get('prefix') or 'SEM_PREFIXO'}"
            point_groups[group_key]["count"] += 1
            if len(point_groups[group_key]["samples"]) < 8:
                point_groups[group_key]["samples"].append(point.name)

        line_records = []
        for line in lines:
            classification = self.classify_line(line.name)
            record = {
                "source_id": line.source_id,
                "name": line.name,
                "folder_path": line.folder_path,
                "color": line.color,
                "width": line.width,
                "length_m": round(line.length_m, 2),
                "vertex_count": len(line.coordinates),
                **classification,
            }
            line_records.append(record)
            key = line.color.get("hex") or "SEM_COR"
            group = color_groups[key]
            group["count"] += 1
            group["total_length_m"] += line.length_m
            group["folders"].add(line.folder_key)
            if classification["fiber_count_hint"]:
                group["fiber_hints"][classification["fiber_count_hint"]] += 1
            if len(group["samples"]) < 8:
                group["samples"].append(line.name)

        for item in placemarks:
            path = item.folder_path
            for depth, folder_name in enumerate(path):
                key = " / ".join(path[: depth + 1])
                record = folders[key]
                if depth + 1 < len(path):
                    record["children"].add(path[depth + 1])
                if item.geometry_type == "Point":
                    record["points"] += 1
                elif item.geometry_type == "LineString":
                    record["lines"] += 1
                if len(record["sample_names"]) < 5:
                    record["sample_names"].append(item.name)

        folder_records = []
        for path, record in sorted(folders.items()):
            leaf = path.split(" / ")[-1]
            normalized = _normalize(leaf)
            route_candidate = bool(re.search(r"\brota\b", normalized)) or (
                record["lines"] > 0 and record["points"] > 0
            )
            folder_records.append({
                "path": path,
                "name": leaf,
                "points": record["points"],
                "lines": record["lines"],
                "children": sorted(record["children"]),
                "samples": record["sample_names"],
                "route_candidate": route_candidate,
                "route_confidence": 0.98 if re.search(r"\brota\b", normalized) else (0.7 if route_candidate else 0.1),
            })

        colors = []
        for hex_color, record in sorted(color_groups.items(), key=lambda item: (-item[1]["count"], item[0])):
            colors.append({
                "hex": None if hex_color == "SEM_COR" else hex_color,
                "count": record["count"],
                "total_length_m": round(record["total_length_m"], 2),
                "folders": sorted(record["folders"]),
                "samples": record["samples"],
                "fiber_count_hints": dict(record["fiber_hints"]),
            })

        warnings = []
        invalid_geometries = len(placemarks) - len(points) - len(lines)
        if invalid_geometries:
            warnings.append(f"{invalid_geometries} objetos não possuem geometria Point/LineString utilizável.")
        unknown_points = sum(1 for item in point_records if item["suggested_type"] == "unknown")
        numeric_points = sum(1 for item in point_records if item["reason"] == "numeric_name")
        if unknown_points:
            warnings.append(f"{unknown_points} pontos precisam de classificação.")
        if numeric_points:
            warnings.append(f"{numeric_points} pontos possuem nome numérico e exigem confirmação em lote.")

        return {
            "schema_version": 1,
            "filename": filename,
            "summary": {
                "folders": len(folder_records),
                "placemarks": len(placemarks),
                "points": len(points),
                "lines": len(lines),
                "unknown_points": unknown_points,
                "numeric_points": numeric_points,
                "total_line_length_m": round(sum(item.length_m for item in lines), 2),
                "distinct_line_colors": len(colors),
            },
            "folders": folder_records,
            "line_color_groups": colors,
            "point_groups": [
                {"key": key, **value}
                for key, value in sorted(point_groups.items(), key=lambda item: (-item[1]["count"], item[0]))
            ],
            "points": point_records,
            "lines": line_records,
            "warnings": warnings,
            "supported_fiber_counts": SUPPORTED_FIBER_COUNTS,
        }
