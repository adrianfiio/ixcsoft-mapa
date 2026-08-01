from __future__ import annotations

import re
from typing import Any, Mapping

_ROUTE_TOKEN = re.compile(r"\bROTA\s*[A-Z0-9][A-Z0-9 /._-]*", re.IGNORECASE)


def route_name_from_metadata(metadata: Mapping[str, Any] | None) -> str:
    """Extrai a rota preservada por importações KML/KMZ antigas e novas."""
    metadata = metadata or {}
    direct = str(metadata.get("route_name") or "").strip()
    if direct:
        return direct
    for key in ("route_path", "kmz_folder", "source_folder"):
        raw = str(metadata.get(key) or "").strip()
        if not raw:
            continue
        parts = [part.strip() for part in raw.split(" / ") if part.strip()]
        for part in reversed(parts):
            if part.upper().startswith("ROTA"):
                return part
        match = _ROUTE_TOKEN.search(raw)
        if match:
            return match.group(0).strip(" ._-/")
    return ""


def _append_route(target: list[Any], route: Any) -> None:
    if route is None or not getattr(route, "name", None):
        return
    if not any(getattr(item, "pk", None) == route.pk for item in target):
        target.append(route)


def element_route_payload(element) -> dict[str, Any]:
    """Retorna todas as rotas relacionadas ao elemento.

    CTO possui relação direta. CEO/CDO e CPD podem obter a rota dos metadados
    do KMZ, dos cabos conectados e das passagens registradas. Isso permite que
    o filtro de rota mantenha um CPD visível em mais de uma rota.
    """
    routes: list[Any] = []
    try:
        cto = element.cto
    except Exception:
        cto = None
    if cto is not None:
        _append_route(routes, getattr(cto, "route", None))

    metadata_name = route_name_from_metadata(getattr(element, "metadata", None))

    # O ponto pode ser origem/destino de diversas rotas (ex.: CPD/POP).
    for manager_name in ("outgoing_cables", "incoming_cables"):
        manager = getattr(element, manager_name, None)
        if manager is None:
            continue
        for cable in manager.select_related("route").exclude(route__isnull=True).all():
            _append_route(routes, cable.route)

    # CEO/CDO pode apenas registrar passagem, sem ser origem/destino.
    passages = getattr(element, "cable_passages", None)
    if passages is not None:
        for passage in passages.select_related("cable__route").exclude(cable__route__isnull=True):
            _append_route(routes, passage.cable.route)

    names = [route.name for route in routes]
    codes = [route.code for route in routes]
    ids = [route.pk for route in routes]
    if metadata_name and metadata_name not in names:
        names.append(metadata_name)

    return {
        "route_id": ids[0] if ids else None,
        "route_name": names[0] if names else "",
        "route_code": codes[0] if codes else "",
        "route_ids": ids,
        "route_names": names,
        "route_codes": codes,
    }
