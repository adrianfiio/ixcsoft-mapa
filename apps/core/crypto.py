from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

class SecretCipher:
    def __init__(self, key: str | bytes | None = None):
        raw = key or settings.FIELD_ENCRYPTION_KEY
        if not raw:
            raise RuntimeError("FIELD_ENCRYPTION_KEY não configurada.")
        self.fernet = Fernet(raw.encode() if isinstance(raw, str) else raw)

    def encrypt(self, value: str) -> str:
        if not value:
            return ""
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        if not value:
            return ""
        try:
            return self.fernet.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Não foi possível descriptografar o segredo.") from exc
