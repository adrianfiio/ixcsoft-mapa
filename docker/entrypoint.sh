#!/bin/sh
set -eu

wait_for_postgres() {
  if [ "${WAIT_FOR_POSTGRES:-true}" != "true" ]; then
    return
  fi

  echo "Aguardando PostgreSQL em ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
  until nc -z "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}"; do
    sleep 2
  done
}

run_web() {
  wait_for_postgres

  if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Aplicando migrations..."
    python manage.py migrate --noinput
  fi

  if [ "${COLLECT_STATIC:-true}" = "true" ]; then
    echo "Coletando arquivos estáticos..."
    python manage.py collectstatic --noinput
  fi

  exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-3}" \
    --threads "${GUNICORN_THREADS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile -
}

case "${1:-web}" in
  web)
    run_web
    ;;
  worker)
    wait_for_postgres
    exec celery -A config worker \
      --loglevel="${CELERY_LOG_LEVEL:-INFO}" \
      --concurrency="${CELERY_WORKER_CONCURRENCY:-2}"
    ;;
  beat)
    wait_for_postgres
    exec celery -A config beat \
      --loglevel="${CELERY_LOG_LEVEL:-INFO}" \
      --scheduler django_celery_beat.schedulers:DatabaseScheduler
    ;;
  migrate)
    wait_for_postgres
    exec python manage.py migrate --noinput
    ;;
  collectstatic)
    exec python manage.py collectstatic --noinput
    ;;
  *)
    exec "$@"
    ;;
esac
