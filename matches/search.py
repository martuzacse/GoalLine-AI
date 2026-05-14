"""Reusable ORM filters for match list / fixtures search."""

from __future__ import annotations

from django.db.models import Q, QuerySet

from matches.models import Match


def filter_matches_by_search(qs: QuerySet[Match], q: str) -> QuerySet[Match]:
    """
    Case-insensitive search across teams, group letter, round/competition labels,
    status, and (for queries of length ≥ 3) tactical + news digest text.

    Single letters A–L also match World Cup group membership / round names like “Group A”.
    """
    raw = (q or "").strip()
    if not raw:
        return qs

    fl = (
        Q(home_team__name__icontains=raw)
        | Q(away_team__name__icontains=raw)
        | Q(home_team__code__icontains=raw)
        | Q(away_team__code__icontains=raw)
        | Q(round_name__icontains=raw)
        | Q(competition_display__icontains=raw)
    )

    u = raw.upper()
    if len(u) == 1 and "A" <= u <= "L":
        fl |= Q(home_team__group_label__iexact=u) | Q(away_team__group_label__iexact=u)
        fl |= Q(round_name__icontains=f"Group {u}")

    if len(raw) >= 3:
        fl |= Q(tactical_notes_home__icontains=raw) | Q(tactical_notes_away__icontains=raw)
        fl |= Q(external_news_digest__icontains=raw)
        fl |= Q(status__icontains=raw)

    # Do not chain .distinct() here: on PostgreSQL, later .order_by("-kickoff", …) on the same
    # queryset can raise ProgrammingError ("SELECT DISTINCT ON expressions must match…").
    # OR filters on this model do not duplicate Match rows, so distinct() is unnecessary.
    return qs.filter(fl)
