from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone as dj_timezone
from django.views.decorators.http import require_GET, require_POST

from agents.deepseek import DeepSeekError
from matches.models import Match, MatchEvent, NewsFeedItem, Player, Team
from matches.search import filter_matches_by_search
from matches.standings import standings_for_group, upcoming_group_matches
from matches.wc_round_order import wc_round_sort_key
from matches.wc2026_data import GROUPS
from predictions.analysis import calibration_rows, snapshot_diff
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
    rounds_raw = list(Match.objects.values("round_name").annotate(match_count=Count("id")))
    rounds_raw.sort(key=lambda r: wc_round_sort_key(r["round_name"]))
    upcoming = list(
        Match.objects.select_related("home_team", "away_team")
        .order_by("kickoff", "id")[:12]
    )
    _attach_latest_predictions(upcoming)
    match_total = Match.objects.count()
    wc_total = Match.objects.filter(is_world_cup=True).count()
    live_total = Match.objects.filter(status=Match.Status.LIVE).count()
    news_feed = list(NewsFeedItem.objects.all()[:14])
    return render(
        request,
        "predictions/home.html",
        {
            "rounds": rounds_raw,
            "upcoming": upcoming,
            "match_total": match_total,
            "wc_total": wc_total,
            "live_total": live_total,
            "news_feed": news_feed,
        },
    )


def fixtures_hub(request: HttpRequest) -> HttpResponse:
    """Goal-style strip for current comps + World Cup rounds (data from your DB, not scraped)."""
    tab = request.GET.get("tab", "current")
    if tab not in ("current", "worldcup"):
        tab = "current"

    search_q = (request.GET.get("q") or "").strip()

    status = (request.GET.get("status") or "").strip()
    valid_status = {"", Match.Status.SCHEDULED, Match.Status.LIVE, Match.Status.FINISHED}
    if status not in valid_status:
        status = ""

    sort = (request.GET.get("sort") or "kickoff").strip()
    if sort not in ("kickoff", "kickoff_desc"):
        sort = "kickoff"
    order = ("-kickoff", "id") if sort == "kickoff_desc" else ("kickoff", "id")

    current_qs = Match.objects.filter(is_world_cup=False).select_related("home_team", "away_team")
    if search_q:
        current_qs = filter_matches_by_search(current_qs, search_q)
    if status:
        current_qs = current_qs.filter(status=status)
    current_matches = list(current_qs.order_by(*order))
    _attach_latest_predictions(current_matches)

    wc_qs = Match.objects.filter(is_world_cup=True).select_related("home_team", "away_team")
    if search_q:
        wc_qs = filter_matches_by_search(wc_qs, search_q)
    if status:
        wc_qs = wc_qs.filter(status=status)
    wc_matches = list(wc_qs.order_by(*order))
    _attach_latest_predictions(wc_matches)

    wc_by_round: dict[str, list[Match]] = {}
    for m in wc_matches:
        wc_by_round.setdefault(m.round_name, []).append(m)
    wc_rounds = sorted(wc_by_round.items(), key=lambda x: wc_round_sort_key(x[0]))

    return render(
        request,
        "predictions/fixtures_hub.html",
        {
            "tab": tab,
            "search_query": search_q,
            "status_filter": status,
            "sort": sort,
            "current_total": len(current_matches),
            "wc_match_total": len(wc_matches),
            "current_matches": current_matches,
            "wc_rounds": wc_rounds,
        },
    )


@require_GET
def matches_today_json(request: HttpRequest) -> JsonResponse:
    """Matches whose kickoff falls on the viewer's local calendar day (tz from IANA name)."""
    raw_tz = (request.GET.get("tz") or "UTC").strip()[:80]
    try:
        tz = ZoneInfo(raw_tz)
        tzname = raw_tz
    except Exception:
        tz = ZoneInfo("UTC")
        tzname = "UTC"
    now_local = dj_timezone.now().astimezone(tz)
    day_start = datetime.combine(now_local.date(), time.min, tzinfo=tz)
    day_end = datetime.combine(now_local.date(), time.max, tzinfo=tz)
    start_utc = day_start.astimezone(ZoneInfo("UTC"))
    end_utc = day_end.astimezone(ZoneInfo("UTC"))
    qs = Match.objects.select_related("home_team", "away_team").filter(
        kickoff__isnull=False,
        kickoff__gte=start_utc,
        kickoff__lte=end_utc,
    )
    matches = list(qs.order_by("kickoff", "id"))
    _attach_latest_predictions(matches)
    rows: list[dict] = []
    for m in matches:
        lp = getattr(m, "latest_prediction", None)
        rows.append(
            {
                "id": m.id,
                "home_code": m.home_team.code,
                "away_code": m.away_team.code,
                "round_name": m.round_name,
                "kickoff": m.kickoff.isoformat() if m.kickoff else None,
                "status": m.status,
                "home_score": m.home_score,
                "away_score": m.away_score,
                "pred_scoreline": lp.scoreline_label if lp else None,
                "pred_confidence": lp.confidence if lp else None,
                "is_world_cup": m.is_world_cup,
                "detail_url": request.build_absolute_uri(reverse("predictions:match_detail", args=[m.id])),
            }
        )
    return JsonResponse(
        {
            "timezone": tzname,
            "date": str(now_local.date()),
            "matches": rows,
        }
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
        Match.objects.select_related("home_team", "away_team").prefetch_related("events"),
        pk=match_id,
    )
    snapshots = list(
        PredictionSnapshot.objects.filter(match=match).select_related("supersedes")
    )
    snapshots.sort(key=lambda s: s.created_at, reverse=True)
    latest = snapshots[0] if snapshots else None
    prev_snap = snapshots[1] if len(snapshots) > 1 else None
    diff = snapshot_diff(prev_snap, latest)
    events = list(match.events.all())
    scenario = None
    wh, wa = request.GET.get("what_home", ""), request.GET.get("what_away", "")
    if wh.isdigit() and wa.isdigit():
        a, b = int(wh), int(wa)
        if 0 <= a <= 20 and 0 <= b <= 20:
            scenario = (a, b)
    return render(
        request,
        "predictions/match_detail.html",
        {
            "match": match,
            "snapshots": snapshots,
            "latest": latest,
            "prev_snapshot": prev_snap,
            "diff": diff,
            "events": events,
            "scenario": scenario,
            "debug": settings.DEBUG,
        },
    )


def global_search(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    teams: list[Team] = []
    players: list[Player] = []
    matches: list[Match] = []
    if q:
        teams = list(Team.objects.filter(Q(name__icontains=q) | Q(code__icontains=q)).order_by("name")[:24])
        players = list(
            Player.objects.select_related("team")
            .filter(
                Q(name__icontains=q)
                | Q(club__icontains=q)
                | Q(team__name__icontains=q)
                | Q(team__code__icontains=q)
            )
            .order_by("team__name", "name")[:24]
        )
        mq = Match.objects.select_related("home_team", "away_team")
        mq = filter_matches_by_search(mq, q)
        matches = list(mq.order_by("-kickoff", "-id")[:30])
    return render(
        request,
        "predictions/search.html",
        {"search_query": q, "teams": teams, "players": players, "matches": matches},
    )


def player_detail(request: HttpRequest, player_id: int) -> HttpResponse:
    player = get_object_or_404(Player.objects.select_related("team"), pk=player_id)
    return render(request, "predictions/player_detail.html", {"player": player})


def team_detail(request: HttpRequest, team_code: str) -> HttpResponse:
    team = get_object_or_404(Team, code__iexact=team_code.strip())
    players = list(team.players.all())
    fixtures = list(
        Match.objects.filter(Q(home_team=team) | Q(away_team=team))
        .select_related("home_team", "away_team")
        .order_by("kickoff", "id")[:36]
    )
    _attach_latest_predictions(fixtures)
    return render(
        request,
        "predictions/team_detail.html",
        {"team": team, "players": players, "fixtures": fixtures},
    )


def wc_groups_index(request: HttpRequest) -> HttpResponse:
    letters = sorted(GROUPS.keys())
    return render(request, "predictions/wc_groups.html", {"letters": letters})


def wc_group_detail(request: HttpRequest, letter: str) -> HttpResponse:
    letter = letter.strip().upper()
    if letter not in GROUPS:
        return HttpResponseBadRequest("Unknown group.")
    standings = standings_for_group(letter)
    fixtures = upcoming_group_matches(letter, limit=48)
    _attach_latest_predictions(fixtures)
    return render(
        request,
        "predictions/wc_group_detail.html",
        {"letter": letter, "standings": standings, "fixtures": fixtures},
    )


def insights_hub(request: HttpRequest) -> HttpResponse:
    cal = calibration_rows(limit=100)
    missing_pred = Match.objects.annotate(pc=Count("prediction_snapshots")).filter(pc=0).count()
    total_matches = Match.objects.count()
    total_snaps = PredictionSnapshot.objects.count()
    finished_with_score = Match.objects.filter(
        status=Match.Status.FINISHED,
        home_score__isnull=False,
        away_score__isnull=False,
    ).count()
    return render(
        request,
        "predictions/insights.html",
        {
            "calibration": cal,
            "missing_pred": missing_pred,
            "total_matches": total_matches,
            "total_snaps": total_snaps,
            "finished_with_score": finished_with_score,
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
