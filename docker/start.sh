#!/usr/bin/env sh
set -e

PORT="${APP_PORT:-8000}"
WORKERS="${APP_WORKERS:-2}"
TIMEOUT="${GUNICORN_TIMEOUT:-60}"
KEEPALIVE="${GUNICORN_KEEPALIVE:-5}"
LOG_LEVEL="${LOG_LEVEL:-info}"

exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WORKERS}" \
  --timeout "${TIMEOUT}" \
  --keep-alive "${KEEPALIVE}" \
  --access-logfile - \
  --access-logformat '[%(t)s] %(h)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"' \
  --error-logfile - \
  --log-level "${LOG_LEVEL}"
