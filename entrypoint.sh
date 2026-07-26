#!/bin/sh
set -e
PORT="${PORT:-8080}"
exec python -m gunicorn -w 2 -k gthread --threads 8 -b "0.0.0.0:${PORT}" server:app
