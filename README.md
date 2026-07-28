# IXCSoft Mapa — v0.4.0

Plataforma de monitoramento de rede óptica com IXCSoft, OLTs, PostGIS, Celery e Redis.

## O que mudou

- modelos IXC consolidados corretamente;
- criptografia Fernet para tokens;
- comando para gerar chave;
- testes do cliente IXC e da criptografia;
- diretórios de migrations preparados;
- versão da API atualizada;
- validação de sintaxe do projeto.

## Primeiro uso

```bash
cp .env.example .env
docker compose build
docker compose run --rm web python manage.py generate_encryption_key
```

Copie a chave exibida para `FIELD_ENCRYPTION_KEY` no `.env`. Depois:

```bash
docker compose up -d db redis
docker compose run --rm web python manage.py makemigrations
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py createsuperuser
docker compose up -d
```

## Testes

```bash
docker compose run --rm web python manage.py test
```

## Segurança

Nunca publique `.env`, token do IXC ou `FIELD_ENCRYPTION_KEY`. O `.env.example` contém somente marcadores.
