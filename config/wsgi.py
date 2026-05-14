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

from django.conf import settings
from django.core.management import call_command

# Migrate on boot only when Render is detected (avoid side effects for local WSGI with DEBUG=False).
if os.environ.get("RENDER") and os.environ.get("AUTO_MIGRATE", "1").lower() in ("1", "true", "yes"):
    call_command("migrate", "--noinput")

# Collect static when missing: production (DEBUG off) even if RENDER is unset, or any Render deploy.
if os.environ.get("AUTO_COLLECTSTATIC", "1").lower() in ("1", "true", "yes"):
    if os.environ.get("RENDER") or not settings.DEBUG:
        marker = settings.STATIC_ROOT / "css" / "app.css"
        if not marker.exists():
            call_command("collectstatic", "--noinput", verbosity=0)
