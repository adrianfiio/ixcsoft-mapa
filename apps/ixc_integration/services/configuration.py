from __future__ import annotations

import os

from apps.ixc_integration.clients.ixc_client import IXCClient
from apps.ixc_integration.models import IXCConfiguration


def decrypt_secret(value: str) -> str:
    # Ponto de extensão para criptografia real. Nesta etapa, o valor é lido
    # diretamente; em produção, use Fernet/KMS ou secret do EasyPanel.
    return value


def build_client(configuration: IXCConfiguration | None = None) -> IXCClient:
    if configuration:
        token = decrypt_secret(configuration.api_token_encrypted)
        return IXCClient(
            base_url=configuration.base_url,
            token=token,
            verify_ssl=configuration.verify_ssl,
        )

    base_url = os.getenv("IXC_BASE_URL", "")
    token = os.getenv("IXC_API_TOKEN", "")
    if not base_url or not token:
        raise ValueError("IXC_BASE_URL e IXC_API_TOKEN não estão configurados.")
    return IXCClient(base_url=base_url, token=token)
