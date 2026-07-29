# Prefer empty Start Command in Railway so Dockerfile CMD (entrypoint.sh) is used.
# If you set a Start Command, it must go through a shell so $PORT expands:
web: sh -c 'python -c "import yaml" 2>/dev/null || pip install -q "PyYAML>=6.0"; python -m gunicorn -w 2 -k gthread --threads 8 -b 0.0.0.0:${PORT:-8080} --timeout 120 server:app'
worker: python worker.py
