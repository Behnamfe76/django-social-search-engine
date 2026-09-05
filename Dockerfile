# syntax=docker/dockerfile:1

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    GUNICORN_WORKERS=3 \
    GUNICORN_TIMEOUT=120 \
    GUNICORN_RELOAD=false \
    CELERY_CONCURRENCY=4 \
    CELERY_LOGLEVEL=INFO \
    CELERY_RELOAD=false

# supervisor runs the two processes; curl backs the container healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends supervisor curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first, so this layer is only rebuilt when requirements change.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Non-root. The UID is a build arg because on Linux the container writes into a
# bind-mounted working tree, and matching the host user is what keeps those files
# owned by you; on Docker Desktop the default is fine.
ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd --gid "$APP_GID" app 2>/dev/null || groupmod --new-name app "$(getent group "$APP_GID" | cut -d: -f1)" \
    && useradd --uid "$APP_UID" --gid "$APP_GID" --create-home app

COPY docker/supervisord.conf /etc/supervisor/supervisord.conf
COPY . .

# A named volume inherits ownership from the image path it covers, so media and
# staticfiles have to be chowned here for the app user to write to them.
RUN mkdir -p /app/media /app/staticfiles \
    && chown -R app:app /app/media /app/staticfiles \
    && chmod +x /app/docker/web.sh /app/docker/worker.sh

USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=6 \
    CMD curl -fsS http://localhost:8000/api/v1/health/ || exit 1

CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
