import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def reload_telegraf() -> bool:
    """Recarrega a configuração do Telegraf via SIGHUP (não derruba o
    container, só relê os `.conf` da pasta montada) — em vez de
    `docker restart`, que soltaria a coleta de TODOS os equipamentos por
    alguns segundos a cada equipamento novo cadastrado por qualquer
    empresa.

    Só o container `worker` monta `/var/run/docker.sock` (nunca o `web`,
    que fica exposto a requisições HTTP) — mesmo assim, isso dá ao worker
    controle sobre o Docker do host; é a única forma prática de recarregar
    um container vizinho a partir de outro."""
    import docker
    from docker.errors import DockerException, NotFound

    container_name = getattr(settings, "SNMP_TELEGRAF_CONTAINER", "monitor-telegraf")
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        container.kill(signal="SIGHUP")
        return True
    except NotFound:
        logger.warning("Container %s não encontrado — Telegraf não recarregado.", container_name)
        return False
    except DockerException:
        logger.exception("Falha ao recarregar o container %s.", container_name)
        return False
