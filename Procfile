# Keep Start Command empty in Railway so this Procfile is used,
# or set Start Command to the same web line below.
web: python -m gunicorn -w 2 -k gthread --threads 8 -b 0.0.0.0:$PORT server:app
worker: python worker.py
