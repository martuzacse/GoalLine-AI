#!/usr/bin/env bash
# Run migrations on every start so tables exist (Neon if DATABASE_URL is set, else SQLite).
set -euo pipefail
python manage.py migrate --noinput
# Ensure /static/ assets exist when the build step skipped collectstatic (common on Render).
if [ -n "${RENDER:-}" ] || [ -n "${DATABASE_URL:-}" ] || [ "${DJANGO_COLLECTSTATIC_ON_START:-0}" = "1" ]; then
  python manage.py collectstatic --noinput
fi
# Use python -m so Gunicorn runs even when the venv's bin/ is not on PATH (Render).
exec python -m gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
