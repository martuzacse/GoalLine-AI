from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.db.models import Count
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from agents.deepseek import DeepSeekError
from matches.models import Match
from matches.search import filter_matches_by_search
from predictions.models import PredictionSnapshot
from predictions.services import dry_run_stub_prediction, run_match_prediction
from predictions.source_catalog import SOURCE_CATEGORIES


def _scorer_one_line(prediction: PredictionSnapshot | None, max_names: int = 5) -> str:
    if not prediction or not prediction.predicted_scorers:
        return ""
    ps = prediction.predicted_scorers
    names: list[str] = []
    for side in ("home", "away"):
        for row in ps.get(side) or []:
            if isinstance(row, dict):
                n = row.get("player")
                if n:
                    names.append(str(n))
    if not names:
        return ""
    head = names[:max_names]
    out = ", ".join(head)
    if len(names) > max_names:
        out += "…"
    return out


def _attach_latest_predictions(matches: list[Match]) -> None:
    latest_map = PredictionSnapshot.latest_by_match_id([m.id for m in matches])
    for m in matches:
        lp = latest_map.get(m.id)
        m.latest_prediction = lp  # type: ignore[attr-defined]
        m.pred_scorers_one_line = _scorer_one_line(lp)  # type: ignore[attr-defined]


def home(request: HttpRequest) -> HttpResponse:
    rounds = (
        Match.objects.values("round_name")
        .annotate(match_count=Count("id"))
        .order_by("round_name")
    )
    upcoming = list(
        Match.objects.select_related("home_team", "away_team")
        .order_by("kickoff", "id")[:12]
    )
    _attach_latest_predictions(upcoming)
    return render(
        request,
        "predictions/home.html",
        {"rounds": rounds, "upcoming": upcoming},
    )


def fixtures_hub(request: HttpRequest) -> HttpResponse:
    """Goal-style strip for current comps + World Cup rounds (data from your DB, not scraped)."""
    tab = request.GET.get("tab", "current")
    if tab not in ("current", "worldcup"):
        tab = "current"

    search_q = (request.GET.get("q") or "").strip()

    current_qs = Match.objects.filter(is_world_cup=False).select_related("home_team", "away_team")
    if search_q:
        current_qs = filter_matches_by_search(current_qs, search_q)
    current_matches = list(current_qs.order_by("kickoff", "id"))
    _attach_latest_predictions(current_matches)

    wc_qs = Match.objects.filter(is_world_cup=True).select_related("home_team", "away_team")
    if search_q:
        wc_qs = filter_matches_by_search(wc_qs, search_q)
    wc_matches = list(wc_qs.order_by("kickoff", "id"))
    _attach_latest_predictions(wc_matches)

    wc_by_round: dict[str, list[Match]] = {}
    for m in wc_matches:
        wc_by_round.setdefault(m.round_name, []).append(m)
    wc_rounds = sorted(wc_by_round.items(), key=lambda x: x[0])

    return render(
        request,
        "predictions/fixtures_hub.html",
        {
            "tab": tab,
            "search_query": search_q,
            "current_total": len(current_matches),
            "wc_match_total": len(wc_matches),
            "current_matches": current_matches,
            "wc_rounds": wc_rounds,
        },
    )


def sources(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "predictions/sources.html",
        {"categories": SOURCE_CATEGORIES},
    )


def round_detail(request: HttpRequest, round_name: str) -> HttpResponse:
    search_q = (request.GET.get("q") or "").strip()
    qs = Match.objects.filter(round_name=round_name).select_related("home_team", "away_team")
    if search_q:
        qs = filter_matches_by_search(qs, search_q)
    matches = list(qs.order_by("kickoff", "id"))
    _attach_latest_predictions(matches)
    return render(
        request,
        "predictions/round.html",
        {"round_name": round_name, "matches": matches, "search_query": search_q},
    )


def match_detail(request: HttpRequest, match_id: int) -> HttpResponse:
    match = get_object_or_404(
        Match.objects.select_related("home_team", "away_team"),
        pk=match_id,
    )
    snapshots = list(
        PredictionSnapshot.objects.filter(match=match).select_related("supersedes")
    )
    snapshots.sort(key=lambda s: s.created_at, reverse=True)
    latest = snapshots[0] if snapshots else None
    return render(
        request,
        "predictions/match_detail.html",
        {
            "match": match,
            "snapshots": snapshots,
            "latest": latest,
            "debug": settings.DEBUG,
        },
    )


@require_POST
def run_agent(request: HttpRequest, match_id: int) -> HttpResponse:
    match = get_object_or_404(Match, pk=match_id)
    try:
        run_match_prediction(match)
        messages.success(request, "DeepSeek agent finished; new snapshot saved.")
    except DeepSeekError as exc:
        messages.error(request, str(exc))
    return redirect("predictions:match_detail", match_id=match.id)


@require_POST
def run_stub(request: HttpRequest, match_id: int) -> HttpResponse:
    if not settings.DEBUG:
        return HttpResponseBadRequest("Stub predictions are only available when DEBUG is True.")
    match = get_object_or_404(Match, pk=match_id)
    dry_run_stub_prediction(match)
    messages.info(request, "Demo stub snapshot saved (no API call).")
    return redirect("predictions:match_detail", match_id=match.id)
