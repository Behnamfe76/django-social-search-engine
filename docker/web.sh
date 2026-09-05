#!/bin/sh
# The web process, started by supervisor.
#
# Options are read from the environment here rather than expanded inside
# supervisord.conf: supervisor treats a missing %(ENV_...)s as fatal, and a
# config that dies because a variable was not set is a poor trade for the
# little it saves.
set -eu

. /app/docker/lib.sh

reload=""
if is_true "${GUNICORN_RELOAD:-}"; then
    echo "web: --reload is on, code changes restart the workers automatically" >&2
    reload="--reload"
fi

# $reload is deliberately unquoted: empty must expand to no argument at all.
exec gunicorn social_search_engine.wsgi:application \
    --bind "0.0.0.0:8000" \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile - \
    $reload
