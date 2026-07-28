#!/bin/sh
# Apply SQL migrations before serving. Do not abort boot if they fail —
# a dead container surfaces as Railway "upstream error" with no HTTP.
if [ -n "${DATABASE_URL:-}" ]; then
  echo "entrypoint: running run_migrations.py…"
  if ! python run_migrations.py; then
    echo "entrypoint: WARNING — migrations failed; starting app anyway (check logs / DATABASE_URL)."
  fi
fi
PORT="${PORT:-8080}"
echo "entrypoint: starting gunicorn on 0.0.0.0:${PORT}"
exec python -m gunicorn -w 2 -k gthread --threads 8 -b "0.0.0.0:${PORT}" --timeout 120 server:app
