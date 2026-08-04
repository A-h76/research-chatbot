# Build frontend (Vite) then run Flask via Gunicorn.
# Railway detects this Dockerfile and uses it instead of Python-only Railpack.

FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Docs catalog imports living contracts/ADRs via @repo-docs → ../docs
COPY docs/ /docs/
RUN npm run build

# Match CI-ish LTS runtime; avoid 3.13 builder OOM/edge wheels on Railway.
FROM python:3.12-slim-bookworm
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Prod-only deps (tests/lint live in requirements-dev.txt). Cache-bust 2026-08-03.
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY . .
COPY --from=frontend /frontend/dist ./frontend/dist

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["/entrypoint.sh"]
