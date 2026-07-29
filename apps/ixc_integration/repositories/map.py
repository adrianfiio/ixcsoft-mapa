from __future__ import annotations

from typing import Any

from django.contrib.gis.geos import Point

from apps.core.enums import OperationalStatus
from apps.network_map.models import CTO, NetworkElement, NetworkProject


def _point(record: dict[str, Any]):
    try:
        latitude = float(str(record.get("latitude") or "").replace(",", "."))
        longitude = float(str(record.get("longitude") or "").replace(",", "."))
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return Point(longitude, latitude, srid=4326)
    except (TypeError, ValueError):
        pass
    return None


class IXCMapRepository:
    @staticmethod
    def upsert_element(record: dict[str, Any], company):
        external_id = str(record.get("id") or "").strip()
        if not external_id:
            raise ValueError("Elemento IXC sem id.")
        project_id = str(record.get("id_projeto") or "").strip()
        project = NetworkProject.objects.filter(
            company=company,
            ixc_project_id=project_id,
        ).first()
        description = str(
            record.get("descricao") or record.get("tipo") or record.get("nome") or ""
        )
        normalized = description.upper()
        element_type = NetworkElement.ElementType.OTHER
        for key, value in (
            ("POSTE", NetworkElement.ElementType.POLE),
            ("CEO", NetworkElement.ElementType.SPLICE_BOX),
            ("EMENDA", NetworkElement.ElementType.SPLICE_BOX),
            ("OLT", NetworkElement.ElementType.OLT),
            ("DIO", NetworkElement.ElementType.DIO),
            ("ARMARIO", NetworkElement.ElementType.CABINET),
            ("ARMÁRIO", NetworkElement.ElementType.CABINET),
        ):
            if key in normalized:
                element_type = value
                break
        active = str(record.get("status") or "A").upper() not in {"I", "INATIVO", "N", "0"}
        return NetworkElement.objects.update_or_create(
            company=company,
            code=f"IXC-ELEM-{external_id}",
            defaults={
                "project": project,
                "name": description or f"Elemento IXC {external_id}",
                "description": "Importado automaticamente do projeto IXCSoft.",
                "element_type": element_type,
                "point": _point(record),
                "status": OperationalStatus.NORMAL if active else OperationalStatus.OFFLINE,
                "enabled": active,
                "metadata": {"ixc": record, "ixc_element_id": external_id},
            },
        )

    @staticmethod
    def upsert_project(record: dict[str, Any], company):
        external_id = str(record.get("id") or "").strip()
        if not external_id:
            raise ValueError("Projeto IXC sem id.")
        active = str(record.get("status") or "A").upper() in {"A", "ATIVO", "S", "1"}
        color = str(record.get("cor_mapa") or "#2dd4bf")
        if not color.startswith("#") or len(color) != 7:
            color = "#2dd4bf"
        return NetworkProject.objects.update_or_create(
            company=company,
            ixc_project_id=external_id,
            defaults={
                "name": record.get("nome") or f"Projeto IXC {external_id}",
                "code": f"IXC-{company_id(company)}-{external_id}",
                "description": "Importado automaticamente do IXCSoft.",
                "status": NetworkProject.Status.ACTIVE if active else NetworkProject.Status.PAUSED,
                "color": color,
                "enabled": active,
            },
        )

    @staticmethod
    def upsert_cto(record: dict[str, Any], company):
        external_id = str(record.get("id") or "").strip()
        if not external_id:
            raise ValueError("CTO IXC sem id.")
        project_id = str(record.get("id_projeto") or "").strip()
        project = NetworkProject.objects.filter(
            company=company,
            ixc_project_id=project_id,
        ).first()
        capacity_raw = record.get("capacidade") or 16
        try:
            capacity = max(1, min(int(float(capacity_raw)), 65535))
        except (TypeError, ValueError):
            capacity = 16
        active = str(record.get("status") or "A").upper() not in {"I", "INATIVO", "N", "0"}
        return CTO.objects.update_or_create(
            company=company,
            ixc_box_id=external_id,
            defaults={
                "project": project,
                "name": record.get("descricao") or f"CTO IXC {external_id}",
                "code": f"IXC-CTO-{external_id}",
                "description": "Importada automaticamente do IXCSoft.",
                "element_type": NetworkElement.ElementType.CTO,
                "point": _point(record),
                "capacity": capacity,
                "status": OperationalStatus.NORMAL if active else OperationalStatus.OFFLINE,
                "enabled": active,
                "metadata": {
                    "ixc": record,
                    "address": record.get("endereco") or "",
                    "number": record.get("numero") or "",
                    "neighborhood": record.get("bairro") or "",
                    "city_id": record.get("id_cidade") or "",
                },
            },
        )


def company_id(company) -> int:
    return int(getattr(company, "pk", company))
