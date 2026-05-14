"""Template context shared across pages (navigation + quick exploration)."""

from __future__ import annotations

from django.db.models import Count
from django.db.utils import OperationalError, ProgrammingError


def nav_explore(request):
    """Rounds list for header dropdown; skip DB on admin to keep admin fast."""
    if request.path.startswith("/admin"):
        return {"nav_rounds": [], "wc_group_letters": list("ABCDEFGHIJKL")}

    try:
        from matches.models import Match

        from matches.wc_round_order import round_name_url_safe, wc_round_sort_key

        nav_rounds = list(
            Match.objects.values("round_name")
            .annotate(match_count=Count("id"))
        )
        nav_rounds = [r for r in nav_rounds if round_name_url_safe(r.get("round_name"))]
        nav_rounds.sort(key=lambda r: wc_round_sort_key(r["round_name"]))
        nav_rounds = nav_rounds[:80]
    except (ProgrammingError, OperationalError):
        nav_rounds = []
    except Exception:
        nav_rounds = []

    return {
        "nav_rounds": nav_rounds,
        "wc_group_letters": list("ABCDEFGHIJKL"),
    }
