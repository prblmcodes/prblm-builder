"""Preview settings per Wagtail Site (``PRBLM_BUILDER_PREVIEW_SITES``).

A project with several sites (each with its own CSS build, header, base template) sets
what differs per site; anything not set falls back to the global settings::

    PRBLM_BUILDER_PREVIEW_SITES = {
        "shop.example.com": {
            "css": ["shop/css/main.css"], "js": ["shop/js/app.js"],
            "body_class": "font-shop",
            "header_template": "shop/header.html", "footer_template": "shop/footer.html",
            "template": "shop/prblm_preview.html",
        },
    }

Keys are Site hostnames (``"shop.example.com"``, or ``"shop.example.com:8000"`` to tell
ports apart). The site is the page's own; for the Block library, the one chosen in its site
switcher (``?site=``), else the one the admin is opened on.
"""
from . import settings as cfg

KEYS = ("css", "js", "body_class", "header_template", "footer_template", "template")


def site_for(page=None, request=None, hostname=None):
    """The Wagtail Site for a page / request / hostname (``None`` if there's none)."""
    try:
        from wagtail.models import Site
    except Exception:  # pragma: no cover
        return None
    try:
        if hostname:
            site = Site.objects.filter(hostname=hostname).first()
            if site is not None:
                return site
        if page is not None and getattr(page, "pk", None):
            site = page.get_site()
            if site is not None:
                return site
        if request is not None:
            if request.GET.get("site"):
                site = Site.objects.filter(hostname=request.GET["site"]).first()
                if site is not None:
                    return site
            parent = request.GET.get("parent")
            if parent and parent.isdigit():
                from wagtail.models import Page
                parent_page = Page.objects.filter(pk=parent).first()
                if parent_page is not None:
                    site = parent_page.get_site()
                    if site is not None:
                        return site
            site = Site.find_for_request(request)
            if site is not None:
                return site
        return Site.objects.filter(is_default_site=True).first()
    except Exception:
        return None


def config(page=None, request=None, site=None):
    """``{css, js, body_class, header_template, footer_template, template}`` for a page /
    request: the global settings, overridden by that site's entry in
    ``PRBLM_BUILDER_PREVIEW_SITES``."""
    out = {
        "css": cfg.preview_css(), "js": cfg.preview_js(), "body_class": cfg.preview_body_class(),
        "header_template": cfg.header_template(), "footer_template": cfg.footer_template(),
        "template": cfg.preview_template(),
    }
    sites = cfg.preview_sites()
    if not sites:
        return out
    site = site or site_for(page, request)
    if site is None:
        return out
    entry = sites.get(f"{site.hostname}:{site.port}") or sites.get(site.hostname) or {}
    for key in KEYS:
        if key in entry and entry[key] is not None:
            out[key] = list(entry[key]) if key in ("css", "js") else entry[key]
    return out


def choices():
    """``[(hostname, label)]`` of the sites with their own preview settings (for the
    Block library's site switcher), or ``[]`` when there's only one setup."""
    sites = cfg.preview_sites()
    if not sites:
        return []
    try:
        from wagtail.models import Site
        return [(s.hostname, s.site_name or s.hostname)
                for s in Site.objects.order_by("-is_default_site", "hostname")]
    except Exception:
        return []
