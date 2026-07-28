# Arquitetura

## Fluxo principal

```text
IXCSoft API ──> Cliente HTTP ──> Serviço de sincronização ──> Repositórios
                                                       └──> PostgreSQL/PostGIS

FiberHome OLT ──> Coletores SNMP ──> Normalização ──> Estado atual + histórico

Estado da rede ──> Motor de correlação ──> Alertas ──> Telegram / Zabbix / Grafana
```

## Camadas por domínio

- `api/`: serializers, views e rotas HTTP.
- `clients/`: comunicação com serviços externos.
- `repositories/`: persistência e atualização de entidades.
- `services/`: regras de negócio e orquestração.
- `tasks.py`: execução assíncrona via Celery.
- `collectors/`: coleta específica por fabricante/modelo.
- `models.py`: entidades persistidas.

## Regra de dependência

A API chama serviços. Serviços chamam clientes e repositórios. Clientes não
conhecem modelos Django. Repositórios não fazem chamadas externas.
