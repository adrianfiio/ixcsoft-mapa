from __future__ import annotations

from dataclasses import dataclass
import base64
from typing import Any, Iterator
from urllib.parse import urlparse
import requests

from .exceptions import IXCAuthenticationError, IXCRequestError


@dataclass(slots=True)
class IXCResponse:
    records: list[dict[str, Any]]
    total: int
    page: int


class IXCClient:
    """Cliente HTTP compatível com o Webservice v1 do IXCSoft.

    Aceita tanto:
      https://dominio
    quanto:
      https://dominio/webservice/v1
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        verify_ssl: bool = True,
        timeout: int = 30,
    ) -> None:
        self.base_url = self._normalize_base_url(base_url)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(
            {
                "Authorization": f"Basic {base64.b64encode(token.encode()).decode()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "ixcsoft": "listar",
            }
        )

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        value = (base_url or "").strip().rstrip("/")
        if not value:
            raise ValueError("A URL do IXCSoft não foi informada.")
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("A URL do IXCSoft é inválida.")
        if value.endswith("/webservice/v1"):
            return value
        return f"{value}/webservice/v1"

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise IXCRequestError(f"Falha ao acessar o IXCSoft: {exc}") from exc

        if response.status_code in {401, 403}:
            raise IXCAuthenticationError(
                "O IXCSoft recusou as credenciais ou o usuário não possui permissão."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise IXCRequestError(
                f"O IXCSoft retornou conteúdo inválido (HTTP {response.status_code})."
            ) from exc

        if not response.ok:
            message = (
                payload.get("message")
                or payload.get("mensagem")
                or payload.get("error")
                or str(payload)
            )
            raise IXCRequestError(f"Erro HTTP {response.status_code}: {message}")

        return payload

    def list_records(
        self,
        table: str,
        *,
        page: int = 1,
        per_page: int = 100,
        field: str | None = None,
        operator: str = ">=",
        value: str | int = 0,
        order_by: str | None = None,
        order_direction: str = "asc",
        grid_param: str = "",
    ) -> IXCResponse:
        field = field or f"{table}.id"
        order_by = order_by or f"{table}.id"
        params = {
            "qtype": field,
            "query": str(value),
            "oper": operator,
            "page": str(page),
            "rp": str(per_page),
            "sortname": order_by,
            "sortorder": order_direction,
        }
        if grid_param:
            params["grid_param"] = grid_param

        # O IXC desta instalação exige POST com filtros em JSON para listagem.
        payload = self._request("POST", table, json=params)
        records = payload.get("registros") or payload.get("records") or []
        total = int(payload.get("total") or len(records))
        return IXCResponse(records=records, total=total, page=page)

    def iter_records(
        self,
        table: str,
        *,
        per_page: int = 100,
        **kwargs: Any,
    ) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            result = self.list_records(
                table,
                page=page,
                per_page=per_page,
                **kwargs,
            )
            yield from result.records
            if page * per_page >= result.total or not result.records:
                break
            page += 1

    def create_record(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", table, json=data)

    def update_record(
        self,
        table: str,
        record_id: str | int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request("PUT", f"{table}/{record_id}", json=data)

    def delete_record(self, table: str, record_id: str | int) -> dict[str, Any]:
        return self._request("DELETE", f"{table}/{record_id}")

    def test_connection(self) -> dict[str, Any]:
        result = self.list_records("cliente", page=1, per_page=1)
        return {"ok": True, "total_clientes": result.total}
