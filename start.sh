#!/usr/bin/env bash
# Run migrations on every start so tables exist (Neon if DATABASE_URL is set, else SQLite).
set -euo pipefail
python manage.py migrate --noinput
# Use python -m so Gunicorn runs even when the venv's bin/ is not on PATH (Render).
exec python -m gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
