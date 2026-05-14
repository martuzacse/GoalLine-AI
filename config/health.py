"""Minimal health endpoints (no templates) for load balancers and debugging."""

from __future__ import annotations

import os

from django.db import connection
from django.http import HttpResponse, JsonResponse


def healthz(_request):
    return HttpResponse("ok", content_type="text/plain; charset=utf-8")


def healthz_version(_request):
    """Which git revision is running (Render sets RENDER_GIT_COMMIT at runtime)."""
    return JsonResponse(
        {
            "git_commit": os.environ.get("RENDER_GIT_COMMIT", ""),
            "git_branch": os.environ.get("RENDER_GIT_BRANCH", ""),
            "repo": os.environ.get("RENDER_GIT_REPO_SLUG", ""),
        }
    )


def healthz_db(_request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
        ok = row is not None and row[0] == 1
        return JsonResponse({"database": "ok" if ok else "unexpected", "vendor": connection.vendor})
    except Exception as exc:
        return JsonResponse({"database": "error", "detail": str(exc)}, status=503)
