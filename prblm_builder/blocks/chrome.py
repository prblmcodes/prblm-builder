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


def option_value(kind, page=None):
    """A Builder page's header/footer as one dropdown value: ``default`` / ``none`` /
    ``site`` / ``id:<pk>`` (a chosen one)."""
    choice = getattr(page, f"{kind}_choice", "default") if page is not None else "default"
    if choice == "custom":
        pk = getattr(page, f"{kind}_id", None)
        return f"id:{pk}" if pk else "default"
    return choice if choice in ("none", "site") else "default"


def _override(kind, request):
    """An unsaved choice from the Layout sidebar (``?options={"header": "id:3"}``), used
    to show it on the canvas before saving."""
    import json
    raw = request.GET.get("options") if request is not None else None
    if not raw:
        return None
    try:
        value = json.loads(raw).get(kind)
    except (ValueError, AttributeError):
        return None
    return value if isinstance(value, str) else None


def for_page(kind, request=None, page=None, model=None):
    """HTML for a Builder page's header/footer per its own choice; ``None`` when ``page``
    / ``model`` isn't a Builder page (so the caller decides)."""
    _m, BuilderPage = _models()
    cls = type(page) if page is not None else model
    if cls is None or not isinstance(cls, type) or not issubclass(cls, BuilderPage):
        return None
    value = _override(kind, request) or option_value(kind, page)
    if value == "none":
        return ""
    if value == "site":
        from prblm_builder.chrome import template_html
        return mark_safe(template_html(kind, request, page))
    if value.startswith("id:"):
        models, _ = _models()
        obj = models[kind].objects.filter(pk=value[3:]).first() if value[3:].isdigit() else None
        if obj is not None:
            return _render(obj, request, page)
    return _render(default(kind), request, page)


def needs_site_assets(page, request=None):
    """Whether a Builder page needs the site's own CSS / JS (``PRBLM_BUILDER_PREVIEW_CSS`` /
    ``_JS``): it shows the site's own header or footer template, or contains one of the
    site's own blocks. A page with only built-in blocks and plugin headers / footers stays
    self-contained, so the site's CSS can't change how it looks."""
    from prblm_builder.chrome import template_name
    from prblm_builder.registry import is_builtin
    for kind in ("header", "footer"):
        value = _override(kind, request) or option_value(kind, page)
        if value == "site" and template_name(kind):
            return True
    for child in (getattr(page, "body", None) or []):
        try:
            if not is_builtin(child.block):
                return True
        except Exception:
            continue
    return False


def page_info(kind):
    """Information-only "Page" tab entry for the site's own page types when a plugin
    site-default header/footer is what the canvas shows (``None`` otherwise — the core
    then explains the template setting)."""
    from django.urls import reverse

    from prblm_builder.chrome import template_name
    if template_name(kind):
        return None
    current = default(kind)
    if current is None:
        return None
    models, _ = _models()
    Model = models[kind]
    noun = kind
    return {
        "name": kind, "label": noun.capitalize(),
        "info": (f"The canvas shows the site default {noun}, \u201c{current.name}\u201d. On the live "
                 f"site, your template for this page type decides (add {{% prblm_{kind} %}} to "
                 f"show it there)."),
        "hint": f"{noun.capitalize()}s can be chosen per page on Builder pages.",
        "manage_url": reverse(f"wagtailsnippets_{Model._meta.app_label}_{Model._meta.model_name}:list"),
        "manage_label": f"Manage {noun}s",
    }


def page_option(kind, page=None):
    """The "Page" tab dropdown for a Builder page's header or footer."""
    from django.urls import reverse

    from prblm_builder.chrome import template_name
    models, _ = _models()
    Model = models[kind]
    current = default(kind)
    noun = "header" if kind == "header" else "footer"
    clear = {f"{kind}_choice": "", kind: ""}
    choices = [
        {"value": "default",
         "label": f"Site default ({current.name})" if current else "Site default (none set yet)",
         "set": {**clear, f"{kind}_choice": "default"}},
        {"value": "none", "label": f"No {noun}", "set": {**clear, f"{kind}_choice": "none"}},
    ]
    if template_name(kind):
        choices.append({"value": "site", "label": f"My site's own {noun}",
                        "set": {**clear, f"{kind}_choice": "site"}})
    for obj in Model.objects.order_by("name"):
        choices.append({"value": f"id:{obj.pk}", "label": obj.name,
                        "set": {f"{kind}_choice": "custom", kind: str(obj.pk)}})
    return {
        "name": kind, "label": noun.capitalize(), "chrome": kind,
        "value": option_value(kind, page),
        "help": f"Shown {'above' if kind == 'header' else 'below'} this page's sections.",
        "choices": choices,
        "manage_url": reverse(f"wagtailsnippets_{Model._meta.app_label}_{Model._meta.model_name}:list"),
        "manage_label": f"Manage {noun}s",
    }


def render(kind, request=None, page=None, name=None):
    """What ``{% prblm_header %}`` / ``{% prblm_footer %}`` output: a named one if asked,
    else the Builder page's own choice, else the site default."""
    if name:
        return _render(named(kind, name), request, page)
    result = for_page(kind, request, page)
    if result is not None:
        return result
    return _render(default(kind), request, page)
