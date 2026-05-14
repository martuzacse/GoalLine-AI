"""Build context and persist DeepSeek-powered match predictions."""

from __future__ import annotations

import json
from typing import Any

from django.db import transaction

from agents.deepseek import DeepSeekError, chat_json
from matches.models import Match, Player
from predictions.models import PredictionSnapshot
from predictions.source_catalog import AGENT_SOURCE_POLICY


def _normalize_predicted_scorers(raw: Any) -> dict[str, Any]:
    """Coerce model JSON into {home: [...], away: [...], summary?: str}."""
    if not isinstance(raw, dict):
        return {"home": [], "away": []}

    def _parse_side(arr: Any) -> list[dict[str, Any]]:
        if not isinstance(arr, list):
            return []
        out: list[dict[str, Any]] = []
        for item in arr:
            if isinstance(item, str):
                out.append({"player": item.strip() or "Unknown", "rationale": ""})
                continue
            if not isinstance(item, dict):
                continue
            name = item.get("player") or item.get("name") or "Unknown"
            rationale = str(item.get("rationale", item.get("reason", ""))).strip()
            rec: dict[str, Any] = {"player": str(name).strip() or "Unknown", "rationale": rationale}
            conf = item.get("confidence")
            if conf is not None and conf != "":
                try:
                    rec["confidence"] = max(0, min(100, int(conf)))
                except (TypeError, ValueError):
                    pass
            out.append(rec)
        return out

    home = raw.get("home")
    if home is None and raw.get("home_scorers") is not None:
        home = raw.get("home_scorers")
    away = raw.get("away")
    if away is None and raw.get("away_scorers") is not None:
        away = raw.get("away_scorers")

    result: dict[str, Any] = {"home": _parse_side(home), "away": _parse_side(away)}
    summary = raw.get("summary") or raw.get("scorers_summary")
    if isinstance(summary, str) and summary.strip():
        result["summary"] = summary.strip()
    return result


def _squads_block(match: Match) -> str:
    lines: list[str] = []
    for label, team in (("Home", match.home_team), ("Away", match.away_team)):
        lines.append(f"## {label}: {team.name} ({team.code}) group {team.group_label or '—'}")
        qs = Player.objects.filter(team=team).select_related("team")
        if not qs.exists():
            lines.append("  (no players on file — infer cautiously)")
        for p in qs:
            inj = " INJURED" if p.is_injured else ""
            shirt = f"#{p.shirt_number} " if p.shirt_number else ""
            stats_blob = ""
            if p.stats_snapshot:
                try:
                    stats_blob = json.dumps(p.stats_snapshot, ensure_ascii=False)[:360]
                except TypeError:
                    stats_blob = ""
            perf = (p.performance_summary[:240] + "…") if len(p.performance_summary) > 240 else (p.performance_summary or "—")
            lines.append(
                f"  - {shirt}{p.name} ({p.get_position_display()}){inj} "
                f"club={p.club or 'n/a'} "
                f"last5_club={p.recent_club_scores or '—'} "
                f"perf={perf} "
                f"stats={stats_blob or '—'} "
                f"injury_notes={p.injury_notes or '—'} "
                f"cards/susp={p.cards_suspension_notes or '—'} "
                f"form_notes={p.form_notes or '—'}"
            )
        tact = match.tactical_notes_home if label == "Home" else match.tactical_notes_away
        if tact:
            lines.append(f"  Tactical notes: {tact}")
    return "\n".join(lines)


def _match_state_block(match: Match) -> str:
    parts = [
        f"Round: {match.round_name}",
        f"Status: {match.get_status_display()}",
    ]
    if match.kickoff:
        parts.append(f"Kickoff (stored as UTC): {match.kickoff.isoformat()}")
    if match.status != Match.Status.SCHEDULED and match.home_score is not None:
        parts.append(f"Current / final score: {match.home_score}–{match.away_score}")
    if match.external_news_digest.strip():
        parts.append("News / external digest:\n" + match.external_news_digest.strip())
    return "\n".join(parts)


def build_agent_context(match: Match, previous: PredictionSnapshot | None) -> str:
    blocks = [_match_state_block(match), _squads_block(match)]
    if previous:
        blocks.append(
            "Previous prediction (to refine or supersede):\n"
            f"  Scoreline: {previous.pred_home_goals}–{previous.pred_away_goals}\n"
            f"  Confidence: {previous.confidence}\n"
            f"  Summary: {previous.reasoning[:1200]}"
        )
        if previous.predicted_scorers:
            blocks.append(
                "Previous predicted scorers (JSON):\n"
                + json.dumps(previous.predicted_scorers, ensure_ascii=False)[:2000]
            )
    return "\n\n".join(blocks)


def _snapshot_from_parsed(
    match: Match,
    parsed: dict[str, Any],
    raw: str,
    source_digest: str,
    previous: PredictionSnapshot | None,
) -> PredictionSnapshot:
    try:
        ph = int(parsed["pred_home_goals"])
        pa = int(parsed["pred_away_goals"])
        conf = int(parsed["confidence"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DeepSeekError(f"Missing or invalid numeric fields in model JSON: {parsed}") from exc

    reasoning = str(parsed.get("reasoning", "")).strip() or "No reasoning provided."
    factors = parsed.get("factors") if isinstance(parsed.get("factors"), dict) else {}
    change = str(parsed.get("change_explanation", "")).strip()
    if previous and not change:
        change = "Model did not supply an explicit delta; review reasoning vs prior snapshot."

    raw_ps = parsed.get("predicted_scorers")
    if not isinstance(raw_ps, dict):
        raw_ps = {}
    extra_summary = parsed.get("scorers_summary")
    if isinstance(extra_summary, str) and extra_summary.strip() and not raw_ps.get("summary"):
        raw_ps = {**raw_ps, "summary": extra_summary.strip()}
    scorers = _normalize_predicted_scorers(raw_ps)

    return PredictionSnapshot(
        match=match,
        pred_home_goals=max(0, min(ph, 20)),
        pred_away_goals=max(0, min(pa, 20)),
        confidence=max(0, min(conf, 100)),
        reasoning=reasoning,
        factors=factors,
        predicted_scorers=scorers,
        source_digest=source_digest,
        supersedes=previous,
        change_explanation=change,
        raw_model_response=raw[:50000],
    )


SYSTEM_PROMPT = """You are a senior football analyst agent for FIFA World Cup fixtures.
You receive squad lists, injury/card notes, tactical notes, optional live scores, and media digests.
You must output strict JSON only (no markdown fences) with keys:
- pred_home_goals (integer, non-negative)
- pred_away_goals (integer, non-negative)
- confidence (integer 0-100): your confidence in the predicted result direction and approximate scoreline
- predicted_scorers (object): must include string keys "home" and "away" mapping to arrays. For each predicted goal for that side, add one object with:
  - player (string): use full names from the provided squad lists when possible
  - rationale (string): 1–2 sentences on why they are a likely scorer in this fixture (role, form, matchup, set pieces)
  - confidence (integer 0-100, optional): your confidence that this player scores at least one goal in this match
  If a side's predicted goal count is 0, use an empty array. If you predict a brace for one player, include two separate objects (you may reuse the same player with different rationales or minutes context).
  Optional sibling string field "summary" inside predicted_scorers: one short paragraph on how/why goals are scored (patterns, transitions, dead-ball threats).
- reasoning (string): clear narrative citing squad strengths, injuries, suspensions, tactics, form signals, news, and per-player last5_club / perf / stats_snapshot fields when present, mapping them to scoreline and scorers
- factors (object): include optional keys injuries, suspensions, tactics, form, news, scorers — each short string or list of strings
- change_explanation (string): if a previous prediction is provided, explain precisely why numbers, scorers, or confidence moved; otherwise empty string

Be calibrated: widen uncertainty when data is thin. Never invent real-time scores not given in context.

""" + AGENT_SOURCE_POLICY


def run_match_prediction(match: Match) -> PredictionSnapshot:
    previous = (
        PredictionSnapshot.objects.filter(match=match).order_by("-created_at").first()
    )
    digest = build_agent_context(match, previous)
    user = (
        "Analyze the fixture and predict the most likely full-time scoreline, "
        "named goal scorers drawn from the squads (with per-scorer rationale), "
        "and confidence.\n\n"
        + digest
        + "\n\nReturn JSON as specified."
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
    parsed, raw = chat_json(messages)
    snap = _snapshot_from_parsed(match, parsed, raw, digest, previous)
    with transaction.atomic():
        snap.save()
    return snap


def _stub_predicted_scorers(match: Match, ph: int, pa: int) -> dict[str, Any]:
    home_names = list(
        Player.objects.filter(team=match.home_team, is_injured=False).values_list("name", flat=True)
    )
    away_names = list(
        Player.objects.filter(team=match.away_team, is_injured=False).values_list("name", flat=True)
    )

    def pick(names: list[str], n: int, side: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for i in range(n):
            label = names[i] if i < len(names) else f"{side.title()} scorer {i + 1}"
            rows.append(
                {
                    "player": label,
                    "rationale": "Stub: picked from available (non-injured) squad order in the database.",
                    "confidence": max(20, 55 - 10 * i),
                }
            )
        return rows

    return {
        "home": pick(home_names, ph, "home"),
        "away": pick(away_names, pa, "away"),
        "summary": "Stub output: align counts with the predicted scoreline; replace with a real agent run.",
    }


def dry_run_stub_prediction(match: Match) -> PredictionSnapshot:
    """Deterministic placeholder when API is unavailable (local demos only)."""
    previous = (
        PredictionSnapshot.objects.filter(match=match).order_by("-created_at").first()
    )
    digest = build_agent_context(match, previous)
    home_n = Player.objects.filter(team=match.home_team, is_injured=True).count()
    away_n = Player.objects.filter(team=match.away_team, is_injured=True).count()
    ph, pa = 1, 1
    if home_n > away_n:
        ph, pa = 1, 2
    elif away_n > home_n:
        ph, pa = 2, 1
    conf = max(35, 72 - 6 * (home_n + away_n))
    reasoning = (
        "Stub agent (no DeepSeek call): scoreline tilts slightly against the side carrying "
        f"more flagged injuries in the database (home injured={home_n}, away injured={away_n}). "
        "Replace with a real agent run when DEEPSEEK_API_KEY is configured."
    )
    factors = {
        "injuries": [f"home_injured_players={home_n}", f"away_injured_players={away_n}"],
        "note": ["This snapshot is a local stub, not model output."],
    }
    change = ""
    if previous:
        change = (
            "Stub refresh: prediction moved because the stub logic re-counted injury flags vs the prior run."
        )
    scorers = _stub_predicted_scorers(match, ph, pa)
    snap = PredictionSnapshot(
        match=match,
        pred_home_goals=ph,
        pred_away_goals=pa,
        confidence=conf,
        reasoning=reasoning,
        factors=factors,
        predicted_scorers=scorers,
        source_digest=digest,
        supersedes=previous,
        change_explanation=change,
        raw_model_response=json.dumps({"stub": True}),
    )
    with transaction.atomic():
        snap.save()
    return snap
