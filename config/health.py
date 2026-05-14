"""Minimal health endpoints (no templates) for load balancers and debugging."""

from __future__ import annotations

from django.db import connection
from django.http import HttpResponse, JsonResponse


def healthz(_request):
    return HttpResponse("ok", content_type="text/plain; charset=utf-8")


def healthz_db(_request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
        ok = row is not None and row[0] == 1
        return JsonResponse({"database": "ok" if ok else "unexpected", "vendor": connection.vendor})
    except Exception as exc:
        return JsonResponse({"database": "error", "detail": str(exc)}, status=503)
