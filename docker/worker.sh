#!/bin/sh
# The Celery worker, started by supervisor.
set -eu

. /app/docker/lib.sh

set -- celery -A social_search_engine worker \
    --loglevel "${CELERY_LOGLEVEL:-INFO}" \
    --concurrency "${CELERY_CONCURRENCY:-4}"

if is_true "${CELERY_RELOAD:-}"; then
    echo "worker: auto-restart is on, watching the project for .py changes" >&2
    # Only the source trees. /app also carries the host's .venv through the bind
    # mount, and watching that would be enormous and pointless.
    #
    # SIGTERM gives Celery a warm shutdown, so a chunk in flight finishes rather
    # than being cut off -- and were it cut off, the task claim makes redelivery
    # safe anyway.
    exec watchmedo auto-restart \
        --directory /app/social_api \
        --directory /app/social_search_engine \
        --pattern '*.py' \
        --recursive \
        --signal SIGTERM \
        --debounce-interval 1 \
        -- "$@"
fi

exec "$@"
