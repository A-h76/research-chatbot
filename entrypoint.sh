#!/bin/sh
# Ensure critical runtime deps exist (guards against stale Railway image caches).
if ! python -c "import yaml" 2>/dev/null; then
  echo "entrypoint: PyYAML missing — installing…"
  pip install --no-cache-dir "PyYAML>=6.0"
fi

# Apply SQL migrations before serving. Bound the wait so a stuck DB never
# blocks Gunicorn forever (that looked like a blank Cloudflare 524 page).
if [ -n "${DATABASE_URL:-}" ]; then
  echo "entrypoint: running run_migrations.py…"
  if command -v timeout >/dev/null 2>&1; then
    if ! timeout "${MIGRATION_TIMEOUT_SEC:-60}" python run_migrations.py; then
      echo "entrypoint: WARNING — migrations failed or timed out; starting app anyway."
    fi
  elif ! python run_migrations.py; then
    echo "entrypoint: WARNING — migrations failed; starting app anyway (check logs / DATABASE_URL)."
  fi
fi
PORT="${PORT:-8080}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
echo "entrypoint: starting gunicorn on 0.0.0.0:${PORT} (workers=${WEB_CONCURRENCY})"
exec python -m gunicorn -w "${WEB_CONCURRENCY}" -k gthread --threads 8 \
  -b "0.0.0.0:${PORT}" --timeout 120 --graceful-timeout 30 server:app
