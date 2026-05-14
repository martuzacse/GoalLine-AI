from __future__ import annotations

from django import template

register = template.Library()


@register.filter(name="is_dict")
def is_dict(value) -> bool:
    return isinstance(value, dict)
