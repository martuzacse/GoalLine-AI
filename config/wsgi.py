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

# On Render, plain `gunicorn ...` often skips migrate/collectstatic from build.
# Run once per worker at import (idempotent). Opt out: AUTO_MIGRATE=0 / AUTO_COLLECTSTATIC=0.
if os.environ.get("RENDER"):
    from django.conf import settings
    from django.core.management import call_command

    if os.environ.get("AUTO_MIGRATE", "1").lower() in ("1", "true", "yes"):
        call_command("migrate", "--noinput")

    if os.environ.get("AUTO_COLLECTSTATIC", "1").lower() in ("1", "true", "yes"):
        marker = settings.STATIC_ROOT / "css" / "app.css"
        if not marker.exists():
            call_command("collectstatic", "--noinput", verbosity=0)
