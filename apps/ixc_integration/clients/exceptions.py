class IXCClientError(Exception):
    """Erro base do cliente IXCSoft."""


class IXCAuthenticationError(IXCClientError):
    """Credenciais inválidas ou não autorizadas."""


class IXCRequestError(IXCClientError):
    """Falha de comunicação ou resposta inválida da API."""
