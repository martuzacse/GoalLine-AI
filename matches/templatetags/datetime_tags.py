from __future__ import annotations

from django import template

register = template.Library()


@register.filter(name="iso8601")
def iso8601(value) -> str:
    """Safe ISO string for <time datetime>; avoids template errors on unexpected types."""
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return str(value)
