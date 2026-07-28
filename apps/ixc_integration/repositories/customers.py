from __future__ import annotations

from typing import Any

from apps.ixc_integration.customer_models import IXCCustomer, IXCLogin


class CustomerRepository:
    @staticmethod
    def upsert_customer(record: dict[str, Any]) -> tuple[IXCCustomer, bool]:
        external_id = str(record.get("id") or "").strip()
        if not external_id:
            raise ValueError("Registro de cliente sem id.")

        defaults = {
            "name": record.get("razao") or record.get("nome") or f"Cliente {external_id}",
            "document": record.get("cnpj_cpf") or "",
            "phone": record.get("fone") or record.get("telefone") or "",
            "email": record.get("email") or "",
            "active": str(record.get("ativo", "S")).upper() in {"S", "SIM", "1", "TRUE"},
            "raw_data": record,
        }
        return IXCCustomer.objects.update_or_create(
            ixc_customer_id=external_id,
            defaults=defaults,
        )

    @staticmethod
    def upsert_login(record: dict[str, Any]) -> tuple[IXCLogin, bool]:
        external_id = str(record.get("id") or "").strip()
        customer_id = str(record.get("id_cliente") or "").strip()
        if not external_id or not customer_id:
            raise ValueError("Login sem id ou id_cliente.")

        customer = IXCCustomer.objects.filter(ixc_customer_id=customer_id).first()
        if customer is None:
            raise ValueError(f"Cliente IXC {customer_id} ainda não sincronizado.")

        status_value = str(record.get("ativo", "S")).upper()
        defaults = {
            "customer": customer,
            "username": record.get("login") or f"login-{external_id}",
            "online": str(record.get("online", "N")).upper() in {"S", "SIM", "1", "TRUE"},
            "last_synced_at": __import__("django.utils.timezone").utils.timezone.now(),
            "raw_data": record,
        }
        return IXCLogin.objects.update_or_create(
            ixc_login_id=external_id,
            defaults=defaults,
        )
