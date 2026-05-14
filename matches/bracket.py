"""Resolve knockout slots from finished results or latest prediction snapshots."""

from __future__ import annotations

from matches.models import KnockoutFeed, Match
from predictions.models import PredictionSnapshot


def _winner_team_id_if_finished(match: Match) -> int | None:
    if match.status != Match.Status.FINISHED:
        return None
    if match.home_score is None or match.away_score is None:
        return None
    if match.home_score > match.away_score:
        return match.home_team_id
    if match.away_score > match.home_score:
        return match.away_team_id
    return None


def _predicted_winner_team_id(match: Match) -> int | None:
    snap = (
        PredictionSnapshot.objects.filter(match=match)
        .order_by("-created_at", "-id")
        .values("pred_home_goals", "pred_away_goals")
        .first()
    )
    if not snap:
        return None
    ph, pa = int(snap["pred_home_goals"]), int(snap["pred_away_goals"])
    if ph > pa:
        return match.home_team_id
    if pa > ph:
        return match.away_team_id
    return None


def resolve_slot_team_id(source: Match) -> int | None:
    """Prefer actual result; if the source is not finished, use latest snapshot winner if decisive."""
    w = _winner_team_id_if_finished(source)
    if w is not None:
        return w
    return _predicted_winner_team_id(source)


def apply_knockout_feeds(*, dry_run: bool = False) -> tuple[int, int]:
    """
    For each KnockoutFeed, set target_match home/away FK to the winner of source_match
    (or predicted winner if not finished). Returns (updated_count, skipped_count).
    """
    updated = 0
    skipped = 0
    qs = KnockoutFeed.objects.select_related("target_match", "source_match")
    for feed in qs.iterator():
        tid = resolve_slot_team_id(feed.source_match)
        if not tid:
            skipped += 1
            continue
        tm = feed.target_match
        if feed.target_side == KnockoutFeed.Side.HOME:
            if tm.home_team_id == tid:
                skipped += 1
                continue
            if dry_run:
                updated += 1
                continue
            tm.home_team_id = tid
            tm.save(update_fields=["home_team_id"])
            updated += 1
        else:
            if tm.away_team_id == tid:
                skipped += 1
                continue
            if dry_run:
                updated += 1
                continue
            tm.away_team_id = tid
            tm.save(update_fields=["away_team_id"])
            updated += 1
    return updated, skipped
