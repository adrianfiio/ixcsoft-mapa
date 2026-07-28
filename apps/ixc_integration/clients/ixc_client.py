from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import requests

from .exceptions import IXCAuthenticationError, IXCRequestError


@dataclass(slots=True)
class IXCResponse:
    records: list[dict[str, Any]]
    total: int
    page: int


class IXCClient:
    """Cliente HTTP para a API do IXCSoft.

    O IXC usa endpoints do tipo `/webservice/v1/<tabela>` e normalmente recebe
    filtros em JSON no corpo da requisição.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        verify_ssl: bool = True,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(
            {
                "Authorization": f"Basic {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "ixcsoft": "listar",
            }
        )

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.base_url}/webservice/v1/{endpoint.lstrip('/')}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise IXCRequestError(f"Falha ao acessar {url}: {exc}") from exc

        if response.status_code in {401, 403}:
            raise IXCAuthenticationError("A API do IXC recusou as credenciais.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise IXCRequestError(
                f"A API retornou conteúdo inválido (HTTP {response.status_code})."
            ) from exc

        if not response.ok:
            message = payload.get("message") or payload.get("error") or str(payload)
            raise IXCRequestError(f"Erro HTTP {response.status_code}: {message}")

        return payload

    def list_records(
        self,
        table: str,
        *,
        page: int = 1,
        per_page: int = 100,
        field: str = "id",
        operator: str = ">=",
        value: str | int = 0,
        order_by: str = "id",
        order_direction: str = "asc",
        grid_param: str = "",
    ) -> IXCResponse:
        body = {
            "qtype": field,
            "query": str(value),
            "oper": operator,
            "page": str(page),
            "rp": str(per_page),
            "sortname": order_by,
            "sortorder": order_direction,
            "grid_param": grid_param,
        }
        payload = self._request("POST", table, json=body)
        records = payload.get("registros") or payload.get("records") or []
        total = int(payload.get("total") or len(records))
        return IXCResponse(records=records, total=total, page=page)

    def iter_records(
        self,
        table: str,
        *,
        per_page: int = 100,
        **kwargs: Any,
    ):
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

    def test_connection(self) -> dict[str, Any]:
        result = self.list_records("cliente", page=1, per_page=1)
        return {"ok": True, "total_clientes": result.total}
