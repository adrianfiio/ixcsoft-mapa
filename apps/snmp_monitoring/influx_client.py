from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime

from django.conf import settings


_SAFE_ID = re.compile(r"^[a-f0-9]{32}$")


IF_OPER_STATUS = {
    1: "up",
    2: "down",
    3: "testing",
    4: "unknown",
    5: "dormant",
    6: "not_present",
    7: "lower_layer_down",
}


def _client():
    import influxdb_client

    if not settings.INFLUXDB_TOKEN:
        raise RuntimeError("INFLUXDB_TOKEN não configurado.")
    return influxdb_client.InfluxDBClient(
        url=settings.INFLUXDB_URL,
        token=settings.INFLUXDB_TOKEN,
        org=settings.INFLUXDB_ORG,
    )


def _safe_ids(values) -> list[str]:
    result = []
    for value in values:
        clean = str(value or "").strip().lower()
        if _SAFE_ID.fullmatch(clean):
            result.append(clean)
    return sorted(set(result))


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def fetch_port_observations_many(
    influx_ids,
    *,
    lookback_minutes: int = 10,
    chunk_size: int = 100,
) -> dict[str, list[dict]]:
    """Busca o último ``ifOperStatus`` de todas as portas em poucos queries.

    A versão anterior fazia um query por equipamento. Aqui os identificadores
    são consultados em lotes, reduzindo a carga no InfluxDB quando houver
    dezenas ou centenas de switches/APs/roteadores cadastrados.
    """
    ids = _safe_ids(influx_ids)
    if not ids:
        return {}
    lookback = max(2, min(int(lookback_minutes), 1440))
    grouped: dict[str, list[dict]] = defaultdict(list)
    client = _client()
    try:
        query_api = client.query_api()
        for offset in range(0, len(ids), max(1, int(chunk_size))):
            chunk = ids[offset:offset + chunk_size]
            flux_set = ", ".join(f'"{item}"' for item in chunk)
            query = f'''
            from(bucket: "{settings.INFLUXDB_BUCKET}")
              |> range(start: -{lookback}m)
              |> filter(fn: (r) => r["_measurement"] == "porta_status")
              |> filter(fn: (r) => r["_field"] == "status_operacional")
              |> filter(fn: (r) => contains(value: r["equipamento_id"], set: [{flux_set}]))
              |> last()
            '''
            tables = query_api.query(org=settings.INFLUXDB_ORG, query=query)
            for table in tables:
                for record in table.records:
                    values = record.values
                    influx_id = str(values.get("equipamento_id") or "").lower()
                    if influx_id not in chunk:
                        continue
                    code = _to_int(record.get_value())
                    observed_at = record.get_time()
                    if observed_at and not isinstance(observed_at, datetime):
                        observed_at = None
                    grouped[influx_id].append({
                        "if_name": str(values.get("porta_nome") or "?").strip() or "?",
                        "if_index": _to_int(values.get("porta_indice")),
                        "if_alias": str(values.get("porta_alias") or "").strip(),
                        "raw_status": code,
                        "status": IF_OPER_STATUS.get(code, "other"),
                        "observed_at": observed_at,
                        "hostname": str(values.get("hostname") or "").strip(),
                    })
    finally:
        client.close()
    return dict(grouped)


def fetch_port_observations(influx_id: str, *, lookback_minutes: int = 10) -> list[dict]:
    return fetch_port_observations_many(
        [influx_id],
        lookback_minutes=lookback_minutes,
    ).get(str(influx_id).lower(), [])


def fetch_port_status(influx_id: str) -> dict[str, str]:
    """Compatibilidade com a API v0.68.0."""
    result = {}
    for row in fetch_port_observations(influx_id):
        label = row["if_name"]
        result[label] = {
            "up": "UP",
            "down": "DOWN",
        }.get(row["status"], "OUTRO")
    return result
