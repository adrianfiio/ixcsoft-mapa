# Deploy no EasyPanel

A versão 0.6.0 foi preparada para implantação a partir do GitHub.

## Serviços necessários

Crie no mesmo projeto do EasyPanel:

1. PostgreSQL com PostGIS
2. Redis
3. Aplicação web Django
4. Worker Celery
5. Celery Beat

O Nginx do arquivo `deploy/nginx/default.conf` é opcional no EasyPanel, pois o
proxy e o HTTPS normalmente são fornecidos pela própria plataforma.

## Repositório

- Repositório: `https://github.com/adrianfiio/ixcsoft-mapa`
- Branch: `main`
- Build method: Dockerfile
- Dockerfile: `Dockerfile`
- Porta interna da aplicação: `8000`

## Comandos dos serviços

### Web

```text
web
```

O serviço web aplica migrations e executa `collectstatic` antes do Gunicorn.

### Worker

```text
worker
```

Defina `RUN_MIGRATIONS=false` e `COLLECT_STATIC=false`.

### Beat

```text
beat
```

Defina `RUN_MIGRATIONS=false` e `COLLECT_STATIC=false`.

## Healthcheck

- Liveness: `/api/health/live/`
- Readiness: `/api/health/ready/`

Use `/api/health/ready/` no EasyPanel para validar PostgreSQL e Redis.

## Volumes

No serviço web, monte volumes persistentes em:

- `/app/media`
- `/app/staticfiles` (opcional quando WhiteNoise estiver servindo estáticos)

## Segurança

- Não coloque tokens do IXCSoft no GitHub.
- Use o painel de variáveis protegidas do EasyPanel.
- Mantenha `DJANGO_DEBUG=false` em produção.
- Use uma senha forte no PostgreSQL.
- Configure `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS` com o domínio real.
