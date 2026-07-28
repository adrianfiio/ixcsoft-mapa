from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.ixc_integration.customer_models import IXCLogin
from apps.ixc_integration.fiber_models import IXCFiberAssignment
from apps.network_map.models import CTO
from apps.olt_integration.models import ONU


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _decimal(value: Any):
    value = _text(value).replace(",", ".")
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _integer(value: Any):
    value = _text(value)
    if not value:
        return None
    try:
        return int(float(value.replace(",", ".")))
    except (TypeError, ValueError):
        return None


def _datetime(value: Any):
    value = _text(value)
    if not value:
        return None
    return parse_datetime(value)


class FiberAssignmentRepository:
    @staticmethod
    def upsert(record: dict[str, Any]) -> tuple[IXCFiberAssignment, bool]:
        external_id = _text(record.get("id"))
        if not external_id:
            raise ValueError("Registro de fibra sem id.")

        login_id = _text(record.get("id_login"))
        cto_id = _text(record.get("id_caixa_ftth"))
        mac = _text(record.get("mac"))
        onu_number = _text(record.get("onu_numero"))

        login = IXCLogin.objects.filter(ixc_login_id=login_id).first() if login_id else None
        cto = CTO.objects.filter(ixc_box_id=cto_id).first() if cto_id else None

        onu_query = ONU.objects.all()
        onu = None
        if mac:
            onu = onu_query.filter(mac_address__iexact=mac).first()
        if onu is None and onu_number:
            try:
                onu = onu_query.filter(onu_id=int(onu_number)).first()
            except ValueError:
                onu = None

        defaults = {
            "login": login,
            "cto": cto,
            "onu": onu,
            "ixc_login_id": login_id,
            "ixc_project_id": _text(record.get("id_projeto")),
            "ixc_cto_id": cto_id,
            "ixc_transmitter_id": _text(record.get("id_transmissor")),
            "ixc_contract_id": _text(record.get("id_contrato")),
            "ixc_hardware_id": _text(record.get("id_hardware")),
            "name": _text(record.get("nome")),
            "mac_address": mac,
            "pon_id": _text(record.get("ponid")),
            "slot_number": _text(record.get("slotno")),
            "pon_number": _text(record.get("ponno")),
            "onu_number": onu_number,
            "onu_type": _text(record.get("onu_tipo")),
            "vlan": _text(record.get("vlan")),
            "vlan_pppoe": _text(record.get("vlan_pppoe")),
            "vlan_dhcp": _text(record.get("vlan_dhcp")),
            "gemport": _text(record.get("gemport")),
            "service_port": _text(record.get("service_port")),
            "cto_port": _text(record.get("porta_ftth")),
            "rx_power": _decimal(record.get("sinal_rx")),
            "tx_power": _decimal(record.get("sinal_tx")),
            "temperature": _decimal(record.get("temperatura")),
            "voltage": _decimal(record.get("voltagem")),
            "distance_meters": _integer(record.get("distancia_onu")),
            "last_signal_at": _datetime(record.get("data_sinal")),
            "last_down_cause": _text(record.get("causa_ultima_queda")),
            "management_ip": _text(record.get("ip_gerencia")) or None,
            "latitude": _decimal(record.get("latitude")),
            "longitude": _decimal(record.get("longitude")),
            "city": _text(record.get("cidade_cliente") or record.get("cidade")),
            "neighborhood": _text(record.get("bairro_cliente") or record.get("bairro")),
            "address": _text(record.get("endereco_cliente") or record.get("endereco")),
            "number": _text(record.get("numero_cliente") or record.get("numero")),
            "complement": _text(record.get("complemento_cliente") or record.get("complemento")),
            "postal_code": _text(record.get("cep_cliente") or record.get("cep")),
            "reference": _text(record.get("referencia_cliente") or record.get("referencia")),
            "raw_data": record,
            "last_synced_at": timezone.now(),
        }

        return IXCFiberAssignment.objects.update_or_create(
            ixc_id=external_id,
            defaults=defaults,
        )
