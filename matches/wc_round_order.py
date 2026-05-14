"""Canonical ordering for World Cup (and other) round names in the UI."""

from __future__ import annotations

import re


def round_name_url_safe(round_name: object) -> bool:
    """
    True if we can build predictions:round URLs for this name.

    The route uses ``<path:round_name>`` (regex ``.+``), so ``reverse()`` fails
    for an empty string — which would 500 any page that lists rounds in the nav.
    """
    return bool(str(round_name or "").strip())

# Order index for knockout phases (after all group-stage rows).
_KO_PHASE_ORDER: dict[str, int] = {
    "Round of 32": 100,
    "Round of 16": 200,
    "Quarter-finals": 300,
    "Semi-finals": 400,
    "Third-place play-off": 500,
    "Final": 600,
}


def wc_round_sort_key(round_name: object) -> tuple:
    """
    Sort key: group stage first (by letter A–L, then matchday), then knockout in bracket order.
    Unknown names sort last within their bucket.
    """
    try:
        name = str(round_name or "").strip()
    except Exception:
        return (2, 99999, "")
    m = re.match(r"^Group\s+([A-Za-z])", name)
    if m:
        letter = m.group(1).upper()
        md_m = re.search(r"Matchday\s+(\d+)", name)
        md = int(md_m.group(1)) if md_m else 0
        return (0, letter, md, name)
    idx = _KO_PHASE_ORDER.get(name)
    if idx is not None:
        return (1, idx, name)
    return (2, 9999, name)
