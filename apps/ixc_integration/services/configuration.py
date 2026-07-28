from __future__ import annotations
import os
from apps.core.crypto import SecretCipher
from apps.ixc_integration.clients.ixc_client import IXCClient
from apps.ixc_integration.models import IXCConfiguration

def encrypt_secret(value: str) -> str:
    return SecretCipher().encrypt(value)

def decrypt_secret(value: str) -> str:
    return SecretCipher().decrypt(value)

def build_client(configuration: IXCConfiguration | None = None) -> IXCClient:
    if configuration:
        return IXCClient(configuration.base_url, decrypt_secret(configuration.api_token_encrypted), verify_ssl=configuration.verify_ssl)
    base_url=os.getenv("IXC_BASE_URL",""); token=os.getenv("IXC_API_TOKEN","")
    if not base_url or not token:
        raise ValueError("IXC_BASE_URL e IXC_API_TOKEN não estão configurados.")
    return IXCClient(base_url, token)
