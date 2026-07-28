from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.access.models import AccessPoint
from apps.access.repositories.ixc import load_ixc_customers


ACTIVE_VALUES = {
    "S",
    "SS",
    "SIM",
    "1",
    "TRUE",
    "ATIVO",
    "ACTIVE",
    "ONLINE",
    "ON",
}


def is_active(value):
    """
    Verifica os valores que o IXC utiliza para ativo ou online.
    """
    return str(value or "").strip().upper() in ACTIVE_VALUES


def convert_ixc_coordinate(value):
    """
    Converte coordenadas vindas do IXC.
    """
    if value in (None, ""):
        return None

    try:
        text = str(value).strip().replace(",", ".")

        if "." not in text:
            return round(float(text) / 1_000_000, 7)

        return round(float(text), 7)

    except (ValueError, TypeError):
        return None


def map_online(value):
    """
    Converte o campo online retornado pelo IXC.

    Aceita S, SS, SIM, 1, TRUE, ONLINE e ON.
    """
    return is_active(value)


def parse_ixc_datetime(value):
    """
    Converte datas do IXC para datetime com timezone.
    """
    if not value:
        return None

    text = str(value).strip()

    for date_format in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            parsed = datetime.strptime(text, date_format)

            if timezone.is_naive(parsed):
                return timezone.make_aware(parsed)

            return parsed

        except (ValueError, TypeError):
            continue

    return None


def sync_radusuarios(client, company):
    """
    Sincroniza somente acessos ativos do IXC.

    Regras:
    - mantém somente registros com ativo=S ou equivalente;
    - remove registros retornados explicitamente como inativos;
    - corrige a leitura do campo online;
    - atualiza os dados do acesso no mapa.
    """
    created = 0
    updated = 0
    deleted = 0
    ignored = 0

    customers = load_ixc_customers(client)
    inactive_external_ids = set()

    with transaction.atomic():
        for item in client.iter_records(
            "radusuarios",
            per_page=200,
        ):
            external_id = str(item.get("id") or "").strip()

            if not external_id:
                ignored += 1
                continue

            if not is_active(item.get("ativo")):
                inactive_external_ids.add(external_id)
                ignored += 1
                continue

            online = map_online(item.get("online"))

            customer_id = str(
                item.get("id_cliente") or ""
            ).strip()

            customer_name = customers.get(
                customer_id,
                "",
            )

            _, was_created = AccessPoint.objects.update_or_create(
                company=company,
                source="ixc",
                external_id=external_id,
                defaults={
                    "ixc_customer_id": customer_id,
                    "ixc_contract_id": str(
                        item.get("id_contrato") or ""
                    ).strip(),
                    "username": str(
                        item.get("login") or ""
                    ).strip(),
                    "customer_name": customer_name,

                    "online": online,
                    "status": (
                        AccessPoint.Status.ONLINE
                        if online
                        else AccessPoint.Status.OFFLINE
                    ),

                    "latitude": convert_ixc_coordinate(
                        item.get("latitude")
                    ),
                    "longitude": convert_ixc_coordinate(
                        item.get("longitude")
                    ),

                    "onu_mac": str(
                        item.get("onu_mac") or ""
                    ).strip(),
                    "cto_ixc_id": str(
                        item.get("id_caixa_ftth") or ""
                    ).strip(),
                    "ftth_port": str(
                        item.get("ftth_porta") or ""
                    ).strip(),

                    "concentrator_id": str(
                        item.get("id_concentrador") or ""
                    ).strip(),
                    "concentrator": str(
                        item.get("concentrador") or ""
                    ).strip(),
                    "interface_transmission": str(
                        item.get("interface_transmissao")
                        or item.get("interface_transmission")
                        or ""
                    ).strip(),
                    "connection_type": str(
                        item.get("tipo_conexao") or ""
                    ).strip(),

                    "last_connection_start": parse_ixc_datetime(
                        item.get("ultima_conexao_inicial")
                    ),
                    "last_connection_end": parse_ixc_datetime(
                        item.get("ultima_conexao_final")
                    ),
                    "disconnect_reason": str(
                        item.get("motivo_desconexao") or ""
                    ).strip(),

                    "last_seen_at": timezone.now(),
                    "raw_data": item,
                },
            )

            if was_created:
                created += 1
            else:
                updated += 1

        if inactive_external_ids:
            removed, _ = AccessPoint.objects.filter(
                company=company,
                source="ixc",
                external_id__in=inactive_external_ids,
            ).delete()

            deleted += removed

        existing_inactive = AccessPoint.objects.filter(
            company=company,
            source="ixc",
        ).exclude(
            raw_data__ativo__in=[
                "S",
                "SS",
                "SIM",
                "1",
                "TRUE",
                "s",
                "ss",
                "sim",
                "true",
            ]
        )

        removed, _ = existing_inactive.delete()
        deleted += removed

    return {
        "created": created,
        "updated": updated,
        "deleted": deleted,
        "ignored": ignored,
    }
