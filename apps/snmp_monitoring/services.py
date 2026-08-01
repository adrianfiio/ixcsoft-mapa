import ipaddress
import os
import re
from pathlib import Path

from django.conf import settings

_TEMPLATE_PATH = Path(__file__).resolve().parent / "conf_templates" / "snmp_universal_status.conf"
_COMMUNITY_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]{1,80}$")


class SNMPConfigError(ValueError):
    pass


def validate_ip(value):
    try:
        ipaddress.ip_address(value)
    except ValueError as exc:
        raise SNMPConfigError(f"IP inválido: {value!r}") from exc
    return value


def validate_community(value):
    if not _COMMUNITY_PATTERN.match(value or ""):
        raise SNMPConfigError(
            "Community SNMP inválida — use só letras, números, ponto, hífen e underscore."
        )
    return value


def conf_directory() -> Path:
    """Pasta compartilhada com o container do Telegraf (montada via volume
    Docker — ver `worker` em docker-compose.yml). Fica fora do controle de
    versão: cada arquivo é gerado/apagado por este serviço, nunca editado
    à mão."""
    return Path(getattr(settings, "SNMP_CONF_DIR", settings.BASE_DIR / "equipamentos_ativos_snmp"))


def render_conf(profile, community_plain: str) -> str:
    """Monta o `.conf` do Telegraf pro perfil, validando IP/community/porta/
    intervalo antes de interpolar — evita que um valor malicioso quebre pra
    fora da string TOML e injete diretivas arbitrárias no Telegraf."""
    validate_ip(profile.management_ip)
    validate_community(community_plain)
    if not (1 <= profile.port <= 65535):
        raise SNMPConfigError(f"Porta SNMP inválida: {profile.port}")
    interval = int(profile.polling_interval_seconds)
    if not (5 <= interval <= 3600):
        raise SNMPConfigError(f"Intervalo de coleta inválido: {interval}s")

    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template.replace("{{IP_DO_EQUIPAMENTO}}", profile.management_ip)
        .replace("{{PORTA}}", str(profile.port))
        .replace("{{COMMUNITY_DO_EQUIPAMENTO}}", community_plain)
        .replace("{{INTERVALO}}", str(interval))
        .replace("{{ID_NO_BANCO_DE_DADOS}}", profile.influx_id)
    )


def write_conf(profile) -> Path:
    directory = conf_directory()
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / profile.conf_filename
    content = render_conf(profile, profile.get_community())
    tmp_path = destination.with_suffix(destination.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, destination)
    return destination


def remove_conf_by_influx_id(influx_id: str) -> None:
    """Recebe o `influx_id` (não o objeto) porque também é chamado depois
    que a linha já foi apagada do banco (`post_delete`)."""
    path = conf_directory() / f"element_{influx_id}.conf"
    path.unlink(missing_ok=True)
