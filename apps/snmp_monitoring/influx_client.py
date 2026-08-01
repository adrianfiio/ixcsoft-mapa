from django.conf import settings


def _client():
    import influxdb_client

    if not settings.INFLUXDB_TOKEN:
        raise RuntimeError("INFLUXDB_TOKEN não configurado.")
    return influxdb_client.InfluxDBClient(
        url=settings.INFLUXDB_URL,
        token=settings.INFLUXDB_TOKEN,
        org=settings.INFLUXDB_ORG,
    )


def fetch_port_status(influx_id: str) -> dict[str, str]:
    """Último status (UP/DOWN/OUTRO) de cada porta do equipamento, lido do
    InfluxDB pela tag `equipamento_id` (== `SNMPMonitoringProfile.influx_id`)."""
    query = f"""
    from(bucket: "{settings.INFLUXDB_BUCKET}")
      |> range(start: -5m)
      |> filter(fn: (r) => r["_measurement"] == "porta_status")
      |> filter(fn: (r) => r["_field"] == "status_operacional")
      |> filter(fn: (r) => r["equipamento_id"] == "{influx_id}")
      |> last()
    """
    client = _client()
    try:
        tables = client.query_api().query(org=settings.INFLUXDB_ORG, query=query)
    finally:
        client.close()

    ports: dict[str, str] = {}
    for table in tables:
        for record in table.records:
            port_name = record.values.get("porta_nome") or "?"
            code = record.get_value()
            ports[port_name] = {1: "UP", 2: "DOWN"}.get(code, "OUTRO")
    return ports
