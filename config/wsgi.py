"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

# On Render, the Start Command is often plain `gunicorn ...` without migrate.
# Run migrations once per worker at import time (idempotent). Opt out: AUTO_MIGRATE=0.
if os.environ.get("RENDER") and os.environ.get("AUTO_MIGRATE", "1").lower() in (
    "1",
    "true",
    "yes",
):
    from django.core.management import call_command

    call_command("migrate", "--noinput")
