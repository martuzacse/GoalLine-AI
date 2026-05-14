"""Minimal health endpoints (no templates) for load balancers and debugging."""

from __future__ import annotations

import os
import traceback

from django.db import connection
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.template.loader import render_to_string
from django.utils.crypto import constant_time_compare


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


def healthz_probe(request):
    """
    Run the same DB + template path as / or /fixtures/ and return JSON (including tracebacks).

    Set env PROBE_SECRET to a long random string, then:
      GET /healthz/probe/?key=<PROBE_SECRET>&page=home
      GET /healthz/probe/?key=<PROBE_SECRET>&page=fixtures&tab=worldcup

    Remove PROBE_SECRET when finished. Never commit the secret.
    """
    expected = os.environ.get("PROBE_SECRET", "").strip()
    got = (request.GET.get("key") or "").strip()
    if not expected or not constant_time_compare(got, expected):
        return HttpResponseNotFound()

    page = (request.GET.get("page") or "home").strip().lower()
    payload: dict = {"ok": False, "page": page, "steps": {}}
    try:
        if page == "home":
            from predictions.views import home_context

            ctx = home_context(request)
            payload["steps"]["context"] = "ok"
            html = render_to_string("predictions/home.html", ctx, request=request)
            payload["steps"]["render"] = "ok"
            payload["html_chars"] = len(html)
        elif page == "fixtures":
            from predictions.views import fixtures_hub_context

            ctx = fixtures_hub_context(request)
            payload["steps"]["context"] = "ok"
            html = render_to_string("predictions/fixtures_hub.html", ctx, request=request)
            payload["steps"]["render"] = "ok"
            payload["html_chars"] = len(html)
        else:
            return JsonResponse({"error": "page must be home or fixtures"}, status=400)
        payload["ok"] = True
        return JsonResponse(payload)
    except Exception:
        payload["traceback"] = traceback.format_exc()
        return JsonResponse(payload, status=200)
