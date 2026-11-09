"""Template tags for the builder's own pages (the canvas, the Block library)."""
from django import template
from django.templatetags.static import static

from ..assets import version

register = template.Library()


@register.simple_tag
def prblm_static(path):
    """``{% static %}`` plus ``?v=<plugin version>``, so browsers load the new file after
    an upgrade instead of a cached old one."""
    return f"{static(path)}?v={version()}"
