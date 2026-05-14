"""
2026 FIFA World Cup Canada/Mexico/USA — group compositions after the 5 Dec 2025 draw.

Source of truth for *which nations sit in which group* is FIFA / the draw broadcast;
kickoff times here are synthetic spacing (UTC) for ordering in the app until you import
official kickoffs from FIFA’s published schedule
(https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums).

This module expands the full *group stage* (72 matches: 12 groups × 3 matchdays × 2 games).
Knock-out bracket slots depend on which third-placed sides advance; add those fixtures
separately once FIFA’s bracket positions are wired into your workflow.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# (fifa_style_code, english_display_name)
GROUPS: dict[str, list[tuple[str, str]]] = {
    "A": [
        ("MEX", "Mexico"),
        ("RSA", "South Africa"),
        ("KOR", "Korea Republic"),
        ("UPD", "UEFA playoff D"),
    ],
    "B": [
        ("CAN", "Canada"),
        ("UPA", "UEFA playoff A"),
        ("QAT", "Qatar"),
        ("SUI", "Switzerland"),
    ],
    "C": [
        ("BRA", "Brazil"),
        ("MAR", "Morocco"),
        ("HAI", "Haiti"),
        ("SCO", "Scotland"),
    ],
    "D": [
        ("USA", "United States"),
        ("PAR", "Paraguay"),
        ("AUS", "Australia"),
        ("UPC", "UEFA playoff C"),
    ],
    "E": [
        ("GER", "Germany"),
        ("CUW", "Curaçao"),
        ("CIV", "Côte d'Ivoire"),
        ("ECU", "Ecuador"),
    ],
    "F": [
        ("NED", "Netherlands"),
        ("JPN", "Japan"),
        ("TUN", "Tunisia"),
        ("UPB", "UEFA playoff B"),
    ],
    "G": [
        ("BEL", "Belgium"),
        ("IRN", "IR Iran"),
        ("EGY", "Egypt"),
        ("NZL", "New Zealand"),
    ],
    "H": [
        ("ESP", "Spain"),
        ("URU", "Uruguay"),
        ("KSA", "Saudi Arabia"),
        ("CPV", "Cabo Verde"),
    ],
    "I": [
        ("FRA", "France"),
        ("SEN", "Senegal"),
        ("NOR", "Norway"),
        ("FP2", "FIFA playoff 2"),
    ],
    "J": [
        ("ARG", "Argentina"),
        ("AUT", "Austria"),
        ("ALG", "Algeria"),
        ("JOR", "Jordan"),
    ],
    "K": [
        ("POR", "Portugal"),
        ("COL", "Colombia"),
        ("UZB", "Uzbekistan"),
        ("FP1", "FIFA playoff 1"),
    ],
    "L": [
        ("ENG", "England"),
        ("CRO", "Croatia"),
        ("PAN", "Panama"),
        ("GHA", "Ghana"),
    ],
}


@dataclass(frozen=True)
class GroupStageRow:
    round_name: str
    home_code: str
    away_code: str
    kickoff: datetime


def iter_group_stage_rows(
    *,
    base_kickoff: datetime | None = None,
) -> Iterator[GroupStageRow]:
    """
    Yield 72 rows (6 per letter) using a standard double round-robin MD1–MD3 pairing:
    MD1: 1v2, 3v4 — MD2: 1v3, 2v4 — MD3: 1v4, 2v3 (positional slots in draw order).
    """
    base = base_kickoff or datetime(2026, 6, 11, 17, 0, tzinfo=timezone.utc)
    slot = 0
    for letter in sorted(GROUPS.keys()):
        teams = GROUPS[letter]
        if len(teams) != 4:
            raise ValueError(f"Group {letter} must have 4 teams")
        idxs = [(0, 1), (2, 3)], [(0, 2), (1, 3)], [(0, 3), (1, 2)]
        for md, pairs in enumerate(idxs, start=1):
            for hi, ai in pairs:
                hc, _ = teams[hi]
                ac, _ = teams[ai]
                kick = base + timedelta(hours=3 * slot)
                slot += 1
                yield GroupStageRow(
                    round_name=f"Group {letter} · Matchday {md}",
                    home_code=hc,
                    away_code=ac,
                    kickoff=kick,
                )


def all_team_rows() -> list[tuple[str, str, str]]:
    """(code, name, group_letter) for every unique team appearing in GROUPS."""
    out: list[tuple[str, str, str]] = []
    for letter, teams in GROUPS.items():
        for code, name in teams:
            out.append((code, name, letter))
    return out


def all_codes() -> set[str]:
    return {code for teams in GROUPS.values() for code, _ in teams}
