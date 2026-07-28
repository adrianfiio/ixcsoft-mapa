#!/bin/sh
set -e

if [ "${WAIT_FOR_POSTGRES:-true}" = "true" ]; then
  echo "Aguardando PostgreSQL em ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
  until nc -z "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}"; do
    sleep 2
  done
fi

python manage.py migrate --noinput

if [ "${COLLECT_STATIC:-true}" = "true" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"
