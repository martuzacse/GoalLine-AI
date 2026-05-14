"""Production-friendly handling for common deploy mistakes."""

from __future__ import annotations

import logging
import os
import traceback

from django.db.utils import DatabaseError
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class RequestExceptionLoggingMiddleware:
    """
    Log full tracebacks for uncaught exceptions (visible in Render / gunicorn logs).
    Placed outermost so failures from any inner middleware or view are recorded.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception:
            logger.exception("%s %s", request.method, request.path)
            if os.environ.get("SHOW_SERVER_ERRORS", "").lower() in ("1", "true", "yes"):
                body = traceback.format_exc()
                return HttpResponse(body, status=500, content_type="text/plain; charset=utf-8")
            raise


class DatabaseErrorResponseMiddleware:
    """
    When migrations were never applied (empty Neon DB), many requests raise
    DatabaseError before DEBUG pages would help. Return a plain HTML 503 with
    fix steps instead of a generic 500.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except DatabaseError:
            body = (
                "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Database setup</title></head>"
                "<body style='font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;line-height:1.5'>"
                "<h1>Database is not ready</h1>"
                "<p>Tables are missing or the database cannot be queried. Apply migrations, then reload.</p>"
                "<ol>"
                "<li><strong>Render Shell:</strong> <code>python manage.py migrate --noinput</code></li>"
                "<li><strong>Or</strong> set <strong>Build</strong> to <code>./build.sh</code> and "
                "<strong>Start</strong> to <code>./start.sh</code>, then redeploy.</li>"
                "</ol>"
                "<p>Check <strong>Render → Logs</strong> for the underlying SQL error while fixing this.</p>"
                "</body></html>"
            )
            return HttpResponse(body, status=503, content_type="text/html; charset=utf-8")
