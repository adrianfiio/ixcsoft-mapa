"""Criptografia de segredos da integração IXCSoft.

A chave deve ser fornecida em FIELD_ENCRYPTION_KEY no formato Fernet
(base64 URL-safe com 32 bytes decodificados).
"""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken
from django.core.exceptions import ImproperlyConfigured


def _get_fernet() -> Fernet:
    key = os.getenv("FIELD_ENCRYPTION_KEY", "").strip()
    if not key:
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEY não foi configurada. "
            "Defina uma chave Fernet válida no ambiente."
        )

    try:
        return Fernet(key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEY é inválida. Use uma chave Fernet válida."
        ) from exc


def encrypt_secret(value: str) -> str:
    """Criptografa um texto e retorna o token como string UTF-8."""
    if value is None:
        raise ValueError("O segredo não pode ser None.")

    return _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    """Descriptografa um token previamente criado por ``encrypt_secret``."""
    if not token:
        return ""

    try:
        return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError(
            "Não foi possível descriptografar o segredo. "
            "Verifique FIELD_ENCRYPTION_KEY."
        ) from exc
