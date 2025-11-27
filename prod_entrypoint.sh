#!/bin/sh
set -e
 
# Ejecutá las migraciones y collectstatic
uv run manage.py makemigrations
uv run manage.py migrate
uv run manage.py collectstatic --noinput

 
# Ejecutá el CMD final
GUNICORN_WORKERS="${GUNICORN_WORKERS:-4}"
GUNICORN_WORKER_CLASS="${GUNICORN_WORKER_CLASS:-gevent}"
GUNICORN_BIND="${GUNICORN_BIND:-0.0.0.0:8000}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-360}"
GUNICORN_ACCESS_LOGFILE="${GUNICORN_ACCESS_LOGFILE:-/app/access.log}"
GUNICORN_ERROR_LOGFILE="${GUNICORN_ERROR_LOGFILE:-/app/error.log}"
 
exec uv run gunicorn "vsm_frigo.wsgi:application" \
  --bind "$GUNICORN_BIND" \
  --worker-class "$GUNICORN_WORKER_CLASS" \
  --workers "$GUNICORN_WORKERS" \
  --access-logfile "$GUNICORN_ACCESS_LOGFILE" \
  --error-logfile "$GUNICORN_ERROR_LOGFILE" \
  --timeout "$GUNICORN_TIMEOUT"
 