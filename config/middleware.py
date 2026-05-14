"""Production-friendly handling for common deploy mistakes."""

from __future__ import annotations

from django.db import DatabaseError
from django.http import HttpResponse


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
