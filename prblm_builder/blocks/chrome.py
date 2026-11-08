"""Headers / Footers: which one a page shows.

- A **Builder page** decides by its own Header / Footer options (site default, a chosen
  one, the site's own template, or none).
- Any other page shows the **site default** (unless the core's template setting applies
  first — see ``prblm_builder.chrome``).
"""
from django.utils.safestring import mark_safe


def _models():
    from .models import BuilderPage, SiteFooter, SiteHeader
    return {"header": SiteHeader, "footer": SiteFooter}, BuilderPage


def default(kind):
    """The site-default Header / Footer object, or ``None``."""
    try:
        models, _ = _models()
        return models[kind].objects.filter(is_default=True).first()
    except Exception:
        return None


def named(kind, name):
    try:
        models, _ = _models()
        return models[kind].objects.filter(name=name).first()
    except Exception:
        return None


def _render(obj, request, page):
    return mark_safe(obj.render(request, page)) if obj is not None else ""


def for_page(kind, request=None, page=None, model=None):
    """HTML for a Builder page's header/footer per its own choice; ``None`` when ``page``
    / ``model`` isn't a Builder page (so the caller decides)."""
    _m, BuilderPage = _models()
    cls = type(page) if page is not None else model
    if cls is None or not isinstance(cls, type) or not issubclass(cls, BuilderPage):
        return None
    choice = getattr(page, f"{kind}_choice", "default") if page is not None else "default"
    if choice == "none":
        return ""
    if choice == "site":
        from prblm_builder.chrome import template_html
        return mark_safe(template_html(kind, request, page))
    if choice == "custom" and page is not None and getattr(page, f"{kind}_id", None):
        return _render(getattr(page, kind), request, page)
    return _render(default(kind), request, page)


def render(kind, request=None, page=None, name=None):
    """What ``{% prblm_header %}`` / ``{% prblm_footer %}`` output: a named one if asked,
    else the Builder page's own choice, else the site default."""
    if name:
        return _render(named(kind, name), request, page)
    result = for_page(kind, request, page)
    if result is not None:
        return result
    return _render(default(kind), request, page)
