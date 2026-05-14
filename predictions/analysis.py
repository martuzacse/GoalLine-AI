"""Lightweight calibration and snapshot helpers for the insights UI."""

from __future__ import annotations

from dataclasses import dataclass

from matches.models import Match
from predictions.models import PredictionSnapshot


@dataclass(frozen=True)
class CalibrationRow:
    match_id: int
    label: str
    actual_home: int
    actual_away: int
    pred_home: int
    pred_away: int
    confidence: int
    goal_error: int
    snapshot_id: int


def calibration_rows(*, limit: int = 80) -> list[CalibrationRow]:
    """Finished matches with a latest prediction vs actual score (sum of absolute goal errors)."""
    qs = (
        Match.objects.filter(
            status=Match.Status.FINISHED,
            home_score__isnull=False,
            away_score__isnull=False,
        )
        .select_related("home_team", "away_team")
        .order_by("-kickoff")[:200]
    )
    out: list[CalibrationRow] = []
    for m in qs:
        snap = (
            PredictionSnapshot.objects.filter(match=m).order_by("-created_at", "-id").values(
                "id",
                "pred_home_goals",
                "pred_away_goals",
                "confidence",
            ).first()
        )
        if not snap:
            continue
        ph, pa = int(snap["pred_home_goals"]), int(snap["pred_away_goals"])
        ah, aa = int(m.home_score), int(m.away_score)
        err = abs(ph - ah) + abs(pa - aa)
        out.append(
            CalibrationRow(
                match_id=m.id,
                label=f"{m.home_team.code} vs {m.away_team.code}",
                actual_home=ah,
                actual_away=aa,
                pred_home=ph,
                pred_away=pa,
                confidence=int(snap["confidence"]),
                goal_error=err,
                snapshot_id=int(snap["id"]),
            )
        )
        if len(out) >= limit:
            break
    out.sort(key=lambda r: r.goal_error, reverse=True)
    return out


def snapshot_diff(prev: PredictionSnapshot | None, cur: PredictionSnapshot | None) -> dict:
    """Structured deltas for template rendering."""
    if not cur:
        return {}
    out: dict[str, object] = {
        "scoreline_prev": None,
        "scoreline_cur": cur.scoreline_label,
        "confidence_prev": None,
        "confidence_cur": cur.confidence,
        "factors_new_keys": [],
        "factors_changed": [],
    }
    if prev:
        out["scoreline_prev"] = prev.scoreline_label
        out["confidence_prev"] = prev.confidence
        pk = set((prev.factors or {}).keys()) if isinstance(prev.factors, dict) else set()
        ck = set((cur.factors or {}).keys()) if isinstance(cur.factors, dict) else set()
        out["factors_new_keys"] = sorted(ck - pk)
        for k in sorted(ck & pk):
            if (prev.factors or {}).get(k) != (cur.factors or {}).get(k):
                out["factors_changed"].append(k)
    return out
