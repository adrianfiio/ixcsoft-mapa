from django.core.mail import EmailMessage, get_connection

from apps.core.crypto import SecretCipher


def send_company_email(configuration, subject, message, to):
    """Envia um e-mail usando o SMTP próprio da empresa (não usa o SMTP da plataforma)."""
    if not configuration or not configuration.enabled:
        raise ValueError("Integração de e-mail desativada ou não configurada.")
    password = (
        SecretCipher().decrypt(configuration.password_encrypted)
        if configuration.password_encrypted
        else ""
    )
    connection = get_connection(
        host=configuration.host,
        port=configuration.port,
        username=configuration.username,
        password=password,
        use_tls=configuration.use_tls,
    )
    email = EmailMessage(subject, message, configuration.from_email, to, connection=connection)
    return email.send()
