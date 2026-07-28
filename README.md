# IXCSoft Mapa

Sistema para monitoramento de rede óptica com integração IXCSoft, OLTs FiberHome, Zabbix, Grafana, Telegram e mapa geoespacial.

## Versão atual: 0.2.0

Incluído:

- Django 5
- Django REST Framework
- PostgreSQL/PostGIS
- Redis
- Celery e Celery Beat
- Swagger/OpenAPI
- Health check
- Modelos de OLT, PON, ONU e histórico óptico
- Modelos de CTO, rotas, elementos e cabos
- Clientes e logins sincronizados do IXCSoft
- Alertas, regras e notificações
- API REST inicial
- Administração Django

## Instalação

```bash
cp .env.example .env
docker compose up --build
```

Em outro terminal:

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

## Endereços

- API Health: `http://localhost:8000/api/health/`
- Swagger: `http://localhost:8000/api/docs/`
- Administração: `http://localhost:8000/admin/`
- API v1: `http://localhost:8000/api/v1/`

## Recursos atuais da API

```text
/api/v1/olts/
/api/v1/pon-ports/
/api/v1/onus/
/api/v1/ctos/
/api/v1/routes/
/api/v1/network-elements/
/api/v1/fiber-cables/
/api/v1/alerts/
```

## Próxima etapa

- Cliente da API IXCSoft
- Sincronização de caixas, clientes e logins
- Rotinas Celery
- Logs e reconciliação entre IXC e OLT
