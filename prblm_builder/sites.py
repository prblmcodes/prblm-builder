"""Preview settings per Wagtail Site (``PRBLM_BUILDER_PREVIEW_SITES``).

A project with several sites (each with its own CSS build, header, base template) sets
what differs per site; anything not set falls back to the global settings::

    PRBLM_BUILDER_PREVIEW_SITES = {
        "shop.example.com": {
            "css": ["shop/css/main.css"], "js": ["shop/js/app.js"],
            "body_class": "font-shop",
            "body_attrs": {"x-data": "{ showModal: false }"}, "html_attrs": {"data-theme": "light"},
            "header_template": "shop/header.html", "footer_template": "shop/footer.html",
            "template": "shop/prblm_preview.html",
        },
        "Landing": {...},            # the Site's name
        "staging-*.example.com": {...},  # a wildcard
    }

A key matches a Site by, in this order: ``"hostname:port"``, ``"hostname"``, the Site's
**name** (as set in Settings → Sites — the same on every server if you name sites
consistently), or a **wildcard** on the hostname (``"landing.*"``, ``"*.example.com"``). The
site is the page's own; for the Block library, the one chosen in its site switcher
(``?site=``), else the one the admin is opened on. A site no key matches uses the global
settings (with one log warning, and a note in the Block library).
"""
import logging
from fnmatch import fnmatchcase

from . import settings as cfg

logger = logging.getLogger("prblm_builder")
_WARNED = set()

KEYS = ("css", "js", "body_class", "body_attrs", "html_attrs", "header_template",
        "footer_template", "template")


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
        "body_attrs": cfg.preview_body_attrs(), "html_attrs": cfg.preview_html_attrs(),
    }
    sites = cfg.preview_sites()
    if not sites:
        return _merge_class(out)
    site = site or site_for(page, request)
    if site is None:
        return _merge_class(out)
    entry = entry_for(site, sites)
    if entry is None:
        _warn(site)
        entry = {}
    for key in KEYS:
        if key in entry and entry[key] is not None:
            out[key] = list(entry[key]) if key in ("css", "js") else entry[key]
    return _merge_class(out)


def entry_for(site, sites=None):
    """The ``PRBLM_BUILDER_PREVIEW_SITES`` entry for ``site``, or ``None``."""
    sites = cfg.preview_sites() if sites is None else sites
    host = (site.hostname or "").lower()
    for key in (f"{host}:{site.port}", host):
        if key in sites:
            return sites[key]
    name = (site.site_name or "").strip()
    if name and name in sites:
        return sites[name]
    for key, entry in sites.items():
        if any(ch in key for ch in "*?[") and fnmatchcase(host, key.lower()):
            return entry
    return None


def _warn(site):
    key = (site.hostname, site.port)
    if key in _WARNED:
        return
    _WARNED.add(key)
    logger.warning("prblm-builder: no PRBLM_BUILDER_PREVIEW_SITES entry matches the site "
                   "%r (%s:%s) — its previews use the global preview settings. Add its "
                   "hostname, its site name or a wildcard.", site.site_name, site.hostname, site.port)


def _merge_class(out):
    """A ``class`` in ``body_attrs`` joins ``body_class`` (one class attribute)."""
    attrs = dict(out.get("body_attrs") or {})
    extra = attrs.pop("class", "")
    if extra:
        out["body_class"] = " ".join(x for x in (out.get("body_class") or "", str(extra)) if x)
    out["body_attrs"] = attrs
    out["html_attrs"] = dict(out.get("html_attrs") or {})
    return out


ALL = "all"


def choices():
    """``[(hostname, label)]`` for the Block library's site switcher, ending with
    ``("all", "All sites")`` — ``[]`` when the project has one Site and no per-site preview
    settings. With ``PRBLM_BUILDER_PREVIEW_SITES``, sites no entry matches say so."""
    sites = cfg.preview_sites()
    try:
        from wagtail.models import Site
        all_sites = list(Site.objects.order_by("-is_default_site", "hostname"))
    except Exception:
        return []
    if len(all_sites) < 2 and not sites:
        return []
    out = []
    for s in all_sites:
        label = s.site_name or s.hostname
        if sites and entry_for(s, sites) is None:
            label += " — uses the default preview settings"
        out.append((s.hostname, label))
    out.append((ALL, "All sites"))
    return out
