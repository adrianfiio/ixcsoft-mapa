# Deploy no EasyPanel — v0.6.2

## Serviços externos

Crie no mesmo projeto:

- PostgreSQL/PostGIS com nome interno `postgres`;
- Redis com nome interno `redis`.

O PostgreSQL deve usar uma imagem PostGIS, por exemplo `postgis/postgis:16-3.4`.

## Serviço Compose

Conecte o repositório `adrianfiio/ixcsoft-mapa`, branch `main`, usando o arquivo da raiz:

```text
docker-compose.yml
```

Esse Compose cria apenas:

- `web`;
- `worker`;
- `beat`.

Ele não publica portas do host e não cria outro banco, outro Redis ou Nginx.

## Domínio

Configure o domínio com:

```text
Serviço Compose: web
Protocolo: HTTP
Porta: 8000
Caminho: /
HTTPS: ligado
```

## Ambiente

Copie `.env.example` para o editor de ambiente e substitua os segredos.

Não use `$` em `DJANGO_SECRET_KEY` ou `POSTGRES_PASSWORD` no editor Compose sem escapar como `$$`, pois o Docker Compose interpreta `$VAR` como interpolação.

## Desenvolvimento local

Use o stack completo local:

```bash
docker compose -f docker-compose.local.yml up --build
```
