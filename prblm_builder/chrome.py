"""The site header/footer shown around the builder canvas.

Resolution order for a page (``kind`` is "header" or "footer"):

1. ``prblm_builder_chrome_for_page`` hooks — an app that owns the page type decides
   outright (return a string, ``""`` meaning "none"); return ``None`` for "not mine".
   The optional blocks app uses this for its Builder page.
2. The site's own template: ``PRBLM_BUILDER_HEADER_TEMPLATE`` / ``_FOOTER_TEMPLATE``.
3. ``prblm_builder_chrome`` hooks — a fallback (the blocks app's site-default header/footer).
"""
from django.template.loader import render_to_string
from wagtail import hooks


PAGE_HOOK = "prblm_builder_chrome_for_page"
DEFAULT_HOOK = "prblm_builder_chrome"


def template_name(kind, page=None, request=None):
    """The site's own header/footer template for this page's site (``""`` if none)."""
    from .sites import config
    return config(page, request)[f"{kind}_template"]


def template_html(kind, request, page=None):
    """The site's own header/footer template, rendered (``""`` if not configured)."""
    tmpl = template_name(kind, page, request)
    if not tmpl:
        return ""
    ctx = {"page": page, "self": page} if page is not None else {}
    return render_to_string(tmpl, ctx, request=request)  # request → context processors


def html(kind, request, page=None, model=None):
    """HTML of the header/footer for ``page`` (or, for a new unsaved page, its ``model``)."""
    for fn in hooks.get_hooks(PAGE_HOOK):
        try:
            result = fn(kind, request, page, model)
        except Exception:
            result = None
        if result is not None:
            return result
    out = template_html(kind, request, page)
    if out:
        return out
    for fn in hooks.get_hooks(DEFAULT_HOOK):
        try:
            result = fn(kind, request, page)
        except Exception:
            result = ""
        if result:
            return result
    return ""


def _blank(html):
    import re

    from django.utils.html import strip_tags
    html = str(html or "")
    return not strip_tags(html).strip() and not re.search(
        r"<(img|picture|svg|video|iframe|canvas|object|embed|hr)\b", html, re.I)


def source(kind, request, page=None, model=None):
    """Where the canvas's header/footer for ``page`` comes from, in the same order as
    ``html()``: ``("page", shows)`` — the page type's own code (a
    ``prblm_builder_chrome_for_page`` hook; ``shows`` False when it returns nothing);
    ``("template", name)`` — the site's own template; ``("default", None)`` — a fallback
    hook (the built-in blocks' site-default header/footer); ``("none", None)``."""
    for fn in hooks.get_hooks(PAGE_HOOK):
        try:
            result = fn(kind, request, page, model)
        except Exception:
            result = None
        if result is not None:
            return "page", not _blank(result)
    tmpl = template_name(kind, page, request)
    if tmpl:
        return "template", tmpl
    for fn in hooks.get_hooks(DEFAULT_HOOK):
        try:
            result = fn(kind, request, page)
        except Exception:
            result = ""
        if result and not _blank(result):
            return "default", None
    return "none", None
