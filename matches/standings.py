"""World Cup group standings derived from finished matches in the database."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from matches.models import Match, Team


@dataclass(frozen=True)
class GroupStandingRow:
    code: str
    name: str
    team: Team | None
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int


def group_finished_matches(letter: str) -> Iterable[Match]:
    letter = letter.upper()
    return Match.objects.filter(
        is_world_cup=True,
        status=Match.Status.FINISHED,
        home_score__isnull=False,
        away_score__isnull=False,
        round_name__startswith=f"Group {letter}",
    ).select_related("home_team", "away_team")


def standings_for_group(letter: str) -> list[GroupStandingRow]:
    from matches.wc2026_data import GROUPS

    letter = letter.upper()
    if letter not in GROUPS:
        return []

    roster = [(code.upper(), name) for code, name in GROUPS[letter]]
    team_by_code: dict[str, Team | None] = {}
    for code, _name in roster:
        team_by_code[code] = Team.objects.filter(code__iexact=code).first()

    stats: dict[str, dict[str, int]] = {}
    for code, _ in roster:
        stats[code] = {"p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}

    for m in group_finished_matches(letter):
        hc = m.home_team.code.upper()
        ac = m.away_team.code.upper()
        if hc not in stats or ac not in stats:
            continue
        hs, gs = int(m.home_score), int(m.away_score)
        stats[hc]["p"] += 1
        stats[ac]["p"] += 1
        stats[hc]["gf"] += hs
        stats[hc]["ga"] += gs
        stats[ac]["gf"] += gs
        stats[ac]["ga"] += hs
        if hs > gs:
            stats[hc]["w"] += 1
            stats[hc]["pts"] += 3
            stats[ac]["l"] += 1
        elif gs > hs:
            stats[ac]["w"] += 1
            stats[ac]["pts"] += 3
            stats[hc]["l"] += 1
        else:
            stats[hc]["d"] += 1
            stats[ac]["d"] += 1
            stats[hc]["pts"] += 1
            stats[ac]["pts"] += 1

    rows: list[GroupStandingRow] = []
    for code, name in roster:
        s = stats[code]
        gd = s["gf"] - s["ga"]
        rows.append(
            GroupStandingRow(
                code=code,
                name=name,
                team=team_by_code.get(code),
                played=s["p"],
                won=s["w"],
                drawn=s["d"],
                lost=s["l"],
                goals_for=s["gf"],
                goals_against=s["ga"],
                goal_diff=gd,
                points=s["pts"],
            )
        )
    rows.sort(key=lambda r: (-r.points, -r.goal_diff, -r.goals_for, r.code))
    return rows


def upcoming_group_matches(letter: str, limit: int = 24) -> list[Match]:
    letter = letter.upper()
    return list(
        Match.objects.filter(is_world_cup=True, round_name__startswith=f"Group {letter}")
        .select_related("home_team", "away_team")
        .order_by("kickoff", "id")[:limit]
    )
