"""Template tags for the built-in blocks.

``{% prblm_assets %}``           CSS + theme + JS, emitted once per page render
``{% pbk_icon name %}``          an inline icon
``{% pbk_image image spec label %}``  an <img>, or a labelled placeholder when empty
``{% pbk_placeholder label w h %}``   a labelled SVG placeholder
"""
import re
from importlib import metadata

from django import template
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .. import icons
from .. import theme as theme_mod

register = template.Library()

try:
    VERSION = metadata.version("prblm-builder")
except metadata.PackageNotFoundError:  # pragma: no cover - running from a checkout
    VERSION = "dev"


@register.simple_tag(takes_context=True)
def prblm_assets(context):
    """The blocks' stylesheet, the site's theme variables and the small script — once per
    request, so a page with ten sections loads them once. Without a request (e.g. a
    block rendered on its own) they're emitted each time, which is harmless."""
    request = context.get("request")
    if request is not None:
        if getattr(request, "_prblm_assets_done", False):
            return ""
        request._prblm_assets_done = True
    return format_html(
        '<link rel="stylesheet" href="{}?v={}"><style>{}</style>'
        '<script src="{}?v={}" defer></script>',
        static("prblm_builder/blocks/blocks.css"), VERSION,
        mark_safe(theme_mod.css(theme_mod.values_for(request))),
        static("prblm_builder/blocks/blocks.js"), VERSION,
    )


@register.simple_tag
def pbk_icon(name, css_class="pbk-icon"):
    return icons.svg(name, css_class)


_SIZE = re.compile(r"(\d+)x(\d+)")
_WIDTH = re.compile(r"width-(\d+)")


def _spec_size(spec):
    m = _SIZE.search(spec or "")
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _WIDTH.search(spec or "")
    if m:
        w = int(m.group(1))
        return w, round(w * 2 / 3)
    return 1200, 800


@register.simple_tag
def pbk_placeholder(label, width=1200, height=800, css_class="pbk-img"):
    """A neutral SVG standing in for an image, labelled with its purpose and size so the
    block explains itself. Nothing is added to the image library."""
    width, height = int(width), int(height)
    text = f"{label} · {width}×{height}"
    fs = max(12, round(min(width, height * 1.6) / 26))
    icon = 1.0 * fs
    cx, cy = width / 2, height / 2
    return format_html(
        '<svg class="{cls} pbk-ph" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid slice" '
        'role="img" aria-label="Placeholder: {text}">'
        '<rect class="pbk-ph__bg" width="{w}" height="{h}"/>'
        '<g class="pbk-ph__fg" fill="none" stroke-width="{sw}" transform="translate({ix} {iy}) scale({sc})">'
        '<rect x="2" y="4" width="20" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.8"/>'
        '<path d="M22 16l-5.5-5.5L6 20"/></g>'
        '<text class="pbk-ph__text" x="{cx}" y="{ty}" text-anchor="middle" font-size="{fs}">{text}</text>'
        '</svg>',
        cls=css_class, w=width, h=height, text=text, fs=fs,
        sw=round(1.6, 2), sc=round(icon * 2 / 24, 3),
        ix=round(cx - icon, 1), iy=round(cy - icon * 2.2, 1), cx=cx, ty=round(cy + fs * 1.2, 1),
    )


@register.simple_tag
def pbk_image(image, spec="width-1200", label="Image", css_class="pbk-img", loading="lazy"):
    """``<img>`` for a Wagtail image at ``spec`` — or a labelled placeholder when no image
    is chosen (or its file is missing)."""
    w, h = _spec_size(spec)
    if not image:
        return pbk_placeholder(label, w, h, css_class)
    try:
        from wagtail.images.shortcuts import get_rendition_or_not_found
        rendition = get_rendition_or_not_found(image, spec)
    except Exception:
        return pbk_placeholder(label, w, h, css_class)
    alt = getattr(image, "default_alt_text", None) or getattr(image, "title", "") or ""
    return format_html(
        '<img class="{}" src="{}" width="{}" height="{}" alt="{}" loading="{}">',
        css_class, rendition.url, rendition.width, rendition.height, alt, loading)
