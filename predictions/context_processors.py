"""Template context shared across pages (navigation + quick exploration)."""

from __future__ import annotations

from django.db.models import Count


def nav_explore(request):
    """Rounds list for header dropdown; skip DB on admin to keep admin fast."""
    if request.path.startswith("/admin"):
        return {"nav_rounds": [], "wc_group_letters": list("ABCDEFGHIJKL")}

    try:
        from matches.models import Match

        nav_rounds = list(
            Match.objects.values("round_name")
            .annotate(match_count=Count("id"))
            .order_by("round_name")[:80]
        )
    except Exception:
        nav_rounds = []

    return {
        "nav_rounds": nav_rounds,
        "wc_group_letters": list("ABCDEFGHIJKL"),
    }
