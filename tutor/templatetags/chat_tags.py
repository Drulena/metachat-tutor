"""Secure template filters for the MetaChat Tutor UI."""

import html
from typing import Optional

import markdown as md_lib
from django import template
from django.utils.safestring import SafeString, mark_safe

register = template.Library()


@register.filter
def markdown(value: Optional[str]) -> SafeString:
    """Render Markdown as safe HTML.

    The raw text is HTML-escaped *before* markdown conversion so that any
    embedded HTML/JS (including user-derived content) is neutralized. This
    keeps **bold**, lists, emoji and newline rendering while preventing XSS.
    """
    text = html.escape(value if value is not None else "")
    return mark_safe(md_lib.markdown(text, extensions=["nl2br"]))
