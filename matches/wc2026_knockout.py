"""
Placeholder 2026 FIFA World Cup knockout bracket rows (32 matches).

Kickoffs are spaced after the last synthetic group-stage slot from ``iter_group_stage_rows``.
Pairings are **not** FIFA-official until you wire ``KnockoutFeed`` rows (admin) or adjust teams
in admin after the draw path is known.

Round names match the public UI: Round of 32 → Final (incl. Third-place play-off).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterator

from matches.wc2026_data import iter_group_stage_rows

# (display round_name, number of fixtures in that round)
KO_ROUND_SPECS: tuple[tuple[str, int], ...] = (
    ("Round of 32", 16),
    ("Round of 16", 8),
    ("Quarter-finals", 4),
    ("Semi-finals", 2),
    ("Third-place play-off", 1),
    ("Final", 1),
)

PLACEHOLDER_TEAM_CODE_PREFIX = "Q"


def bracket_placeholder_code(slot_index: int) -> str:
    """Stable 8-char code: Q + 7 digits (e.g. Q0000001)."""
    if slot_index < 1 or slot_index > 9_999_999:
        raise ValueError("slot_index out of range for placeholder code")
    return f"{PLACEHOLDER_TEAM_CODE_PREFIX}{slot_index:07d}"


def first_knockout_kickoff_utc():
    """First KO kickoff: day after the latest placeholder group kickoff."""
    from datetime import datetime, timezone

    rows = list(iter_group_stage_rows())
    if not rows:
        return datetime(2026, 7, 5, 17, 0, tzinfo=timezone.utc)
    return max(r.kickoff for r in rows) + timedelta(days=1)


@dataclass(frozen=True)
class KnockoutRow:
    round_name: str
    kickoff_index: int  # hours offset from base for ordering
    home_slot: int  # 1-based placeholder slot index
    away_slot: int


def iter_knockout_placeholder_rows() -> Iterator[KnockoutRow]:
    """Yield 32 rows; each uses two distinct placeholder slot indices."""
    slot = 1
    hour = 0
    for round_name, n_matches in KO_ROUND_SPECS:
        for _ in range(n_matches):
            hr, ar = slot, slot + 1
            slot += 2
            yield KnockoutRow(
                round_name=round_name,
                kickoff_index=hour,
                home_slot=hr,
                away_slot=ar,
            )
            hour += 6
