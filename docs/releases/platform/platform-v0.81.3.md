# Plataforma v0.81.3

Corrige o GID cravado do socket do Docker no `worker`, que fazia o
recarregamento do Telegraf falhar silenciosamente sempre que um
monitoramento SNMP era criado, editado ou removido.

## Contexto

Investigando um relato de monitoramento SNMP "fantasma" (equipamento
antigo removido no mapa continuava aparecendo com dado fresco no
InfluxDB, e o equipamento novo criado no lugar não trazia dado
nenhum), confirmamos duas coisas:

1. A exclusão de equipamento **já funciona certinho**: o `.conf` do
   equipamento removido é apagado do disco de verdade (`CASCADE` +
   sinal `post_delete` em `SNMPMonitoringProfile`, ver
   `apps/snmp_monitoring/signals.py`).
2. O problema real é o `reload_telegraf()` (`apps/snmp_monitoring/docker_control.py`):
   `docker-compose.yml` colocava o `worker` no grupo `999` (`group_add`)
   assumindo que esse fosse o GID do dono de `/var/run/docker.sock`. No
   servidor de produção, o GID real é `989` (confirmado com
   `stat -c '%g' /var/run/docker.sock`). Com o GID errado, toda
   tentativa de mandar SIGHUP pro Telegraf falha com `PermissionError`
   — silenciosamente, só visível no log do `worker`, nunca no site. O
   Telegraf só pegava configuração nova/removida quando crashava e
   reiniciava sozinho por outro motivo (comportamento observado por
   sorte numa investigação anterior, não por um reload funcionando).

## Entrega

- `docker-compose.yml`: `group_add` do `worker` passa de `"999"`
  cravado pra `"${DOCKER_SOCK_GID:-999}"` — configurável por servidor,
  com `999` como valor padrão (mesmo comportamento de antes pra quem
  não setar a variável).

## Aplicação no servidor (necessário além do deploy do código)

O `.env` de produção precisa da variável nova, já que o GID real
(`989`) é diferente do padrão:

```bash
echo 'DOCKER_SOCK_GID=989' >> /opt/ixcsoft-mapa/.env
docker compose up -d --force-recreate worker
docker exec -it ixcsoft-mapa-worker-1 id   # confirma "989" nos groups
```

## Dados e segurança

- Só infraestrutura (`docker-compose.yml`) — nenhuma mudança de
  código Python, nenhuma migration.
- Sem isso configurado, o comportamento é o mesmo de antes desta
  versão (grupo `999`, mesma falha silenciosa) — mudança
  retrocompatível, só passa a funcionar quando `DOCKER_SOCK_GID` for
  definido corretamente no `.env`.

## Validação executada neste sandbox (sem GDAL/Postgres/Docker)

- Revisão manual do YAML (sintaxe `${VAR:-default}` já usada em todo o
  resto do arquivo, mesmo padrão).
- Nenhum arquivo da trilha do mapa tocado, `MAP_VERSION` inalterada.
- Confirmação real (reload do Telegraf funcionando após a mudança,
  sem esperar um crash acontecer por acaso) depende do `.env` do
  servidor e de recriar o `worker` — ver comandos acima.
