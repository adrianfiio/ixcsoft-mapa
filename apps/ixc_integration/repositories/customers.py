from __future__ import annotations

from typing import Any

from apps.ixc_integration.models import IXCContract, IXCCustomer, IXCLogin


class CustomerRepository:
    ACTIVE_VALUES = {"A", "ATIVO", "S", "SIM", "1", "TRUE"}
    @staticmethod
    def upsert_customer(record: dict[str, Any], company) -> tuple[IXCCustomer, bool]:
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
            company=company,
            ixc_customer_id=external_id,
            defaults=defaults,
        )

    @staticmethod
    def upsert_login(record: dict[str, Any], company) -> tuple[IXCLogin, bool]:
        external_id = str(record.get("id") or "").strip()
        customer_id = str(record.get("id_cliente") or "").strip()
        if not external_id or not customer_id:
            raise ValueError("Login sem id ou id_cliente.")

        customer = IXCCustomer.objects.filter(company=company, ixc_customer_id=customer_id).first()
        if customer is None:
            raise ValueError(f"Cliente IXC {customer_id} ainda não sincronizado.")

        contract_id = str(record.get("id_contrato") or record.get("contrato") or "").strip()
        contract = (
            IXCContract.objects.filter(company=company, ixc_contract_id=contract_id).first()
            if contract_id
            else None
        )
        defaults = {
            "customer": customer,
            "contract": contract,
            "username": record.get("login") or f"login-{external_id}",
            "online": str(record.get("online", "N")).upper() in {"S", "SIM", "1", "TRUE"},
            "last_synced_at": __import__("django.utils.timezone").utils.timezone.now(),
            "raw_data": record,
        }
        return IXCLogin.objects.update_or_create(
            company=company,
            ixc_login_id=external_id,
            defaults=defaults,
        )

    @classmethod
    def upsert_contract(
        cls,
        record: dict[str, Any],
        company,
        active_only: bool = True,
    ) -> tuple[IXCContract | None, bool]:
        external_id = str(record.get("id") or "").strip()
        customer_id = str(record.get("id_cliente") or "").strip()
        if not external_id or not customer_id:
            raise ValueError("Contrato sem id ou id_cliente.")
        customer = IXCCustomer.objects.filter(company=company, ixc_customer_id=customer_id).first()
        if customer is None:
            raise ValueError(f"Cliente IXC {customer_id} ainda não sincronizado.")
        status = str(record.get("status") or record.get("ativo") or "").strip().upper()
        active = status in cls.ACTIVE_VALUES
        if active_only and not active:
            IXCContract.objects.filter(company=company, ixc_contract_id=external_id).delete()
            return None, False
        return IXCContract.objects.update_or_create(
            company=company,
            ixc_contract_id=external_id,
            defaults={
                "customer": customer,
                "status": status,
                "active": active,
                "description": str(
                    record.get("contrato") or record.get("descricao") or record.get("plano") or ""
                )[:255],
                "raw_data": record,
            },
        )
