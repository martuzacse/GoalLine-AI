#!/usr/bin/env bash
# Render / CI: install deps then apply DB migrations (needs DATABASE_URL for Neon).
set -euo pipefail
pip install -r requirements.txt
python manage.py migrate --noinput
