# IXCSoft Mapa

Plataforma para monitoramento e correlação de rede óptica, integrando IXCSoft,
OLTs FiberHome, PostgreSQL/PostGIS, Celery, Redis, Zabbix, Grafana e Telegram.

## Versão 0.3.0

Esta versão adiciona:

- arquitetura em camadas;
- cliente HTTP do IXCSoft;
- sincronização de clientes e logins;
- tarefas Celery;
- endpoints para testar conexão e iniciar sincronização;
- base de coletores por fabricante;
- documentação de arquitetura;
- GitHub Actions.

## Executar

```bash
cp .env.example .env
docker compose up --build
```

Depois:

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

## Endpoints principais

- `/api/health/`
- `/api/docs/`
- `/api/v1/olts/`
- `/api/v1/onus/`
- `/api/v1/ctos/`
- `/api/ixc/configurations/`
- `/api/ixc/customers/`
- `/api/ixc/logins/`
- `/api/ixc/executions/`

## Documentação

- `docs/ARCHITECTURE.md`
- `docs/IXC_SETUP.md`

## Próxima etapa

- perfis de OIDs FiberHome;
- coleta SNMP real;
- descoberta de PONs e ONUs;
- histórico óptico;
- correlação ONU ↔ login IXC.
