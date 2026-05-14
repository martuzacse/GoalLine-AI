"""Import national-team squads from curated JSON (no HTML scraping)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.db import transaction

from matches.models import Player, Team


class SquadImportError(ValueError):
    pass


def _norm_position(raw: Any) -> str:
    if raw is None or raw == "":
        return Player.Position.MF
    v = str(raw).strip().upper()
    valid = {c.value for c in Player.Position}
    if v in valid:
        return v
    alias = {
        "GOALKEEPER": Player.Position.GK,
        "KEEPER": Player.Position.GK,
        "DEFENDER": Player.Position.DF,
        "MIDFIELDER": Player.Position.MF,
        "MIDFIELD": Player.Position.MF,
        "FORWARD": Player.Position.FW,
        "STRIKER": Player.Position.FW,
        "WINGER": Player.Position.FW,
    }
    return alias.get(v, Player.Position.MF)


def _row_to_defaults(row: dict[str, Any]) -> dict[str, Any]:
    sn = row.get("shirt_number")
    shirt = None
    if sn is not None and sn != "":
        try:
            shirt = int(sn)
        except (TypeError, ValueError):
            shirt = None
    stats = row.get("stats_snapshot") or {}
    if not isinstance(stats, dict):
        raise SquadImportError(f"stats_snapshot must be an object for player {row.get('name')!r}")
    return {
        "position": _norm_position(row.get("position")),
        "club": str(row.get("club", "") or "")[:160],
        "shirt_number": shirt,
        "recent_club_scores": str(row.get("recent_club_scores", "") or "")[:120],
        "performance_summary": str(row.get("performance_summary", "") or "").strip(),
        "stats_snapshot": stats if isinstance(stats, dict) else {},
        "form_notes": str(row.get("form_notes", "") or "")[:500],
        "is_injured": bool(row.get("is_injured", False)),
        "injury_notes": str(row.get("injury_notes", "") or "")[:255],
        "cards_suspension_notes": str(row.get("cards_suspension_notes", "") or "")[:255],
    }


def import_squad_dict(data: dict[str, Any], *, dry_run: bool = False) -> tuple[int, int, list[str]]:
    """
    Upsert players keyed by (team code, player name).

    Returns (created_count, updated_count, warnings).
    """
    if not isinstance(data, dict):
        raise SquadImportError("Root JSON must be an object keyed by FIFA-style team codes.")

    created = 0
    updated = 0
    warnings: list[str] = []

    def _run() -> None:
        nonlocal created, updated
        for team_code, rows in data.items():
            if not isinstance(rows, list):
                warnings.append(f"Skipping {team_code}: value is not a list.")
                continue
            try:
                team = Team.objects.get(code=str(team_code).strip().upper())
            except Team.DoesNotExist:
                warnings.append(f"No Team with code {team_code!r}; create teams first (e.g. load_wc2026_fixtures).")
                continue
            for raw in rows:
                if not isinstance(raw, dict):
                    warnings.append(f"Skipping non-object row under {team_code}.")
                    continue
                name = str(raw.get("name", "")).strip()
                if not name:
                    warnings.append(f"Skipping row with empty name under {team_code}.")
                    continue
                defaults = _row_to_defaults(raw)
                if dry_run:
                    continue
                _, was_created = Player.objects.update_or_create(
                    team=team,
                    name=name,
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

    if dry_run:
        _run()
        return 0, 0, warnings

    with transaction.atomic():
        _run()
    return created, updated, warnings


def import_squad_json_file(path: Path, *, dry_run: bool = False) -> tuple[int, int, list[str]]:
    raw_text = path.read_text(encoding="utf-8")
    data = json.loads(raw_text)
    return import_squad_dict(data, dry_run=dry_run)
