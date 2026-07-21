#!/bin/sh
# Production entrypoint: apply pending Alembic migrations before the app
# starts serving traffic, then hand off to the real CMD (uvicorn).
set -e

echo "Running database migrations..."
alembic upgrade head

exec "$@"
