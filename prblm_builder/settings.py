"""Opt-in configuration for the page builder, read from Django settings.

All optional — with nothing set, the builder enables any Page model that has a
StreamField named ``body`` and renders previews unstyled. A host site points the
previews at its own front-end CSS/JS so sections look like production.

    # bemore/settings/base.py
    PRBLM_BUILDER_PREVIEW_CSS = ["css/bemore.css"]       # static paths or URLs
    PRBLM_BUILDER_PREVIEW_JS = ["js/bemore.js"]
    PRBLM_BUILDER_PREVIEW_BODY_CLASS = "font-body text-ink antialiased"
    PRBLM_BUILDER_FIELD_NAMES = ["body"]                 # which StreamField to build
    PRBLM_BUILDER_PAGE_MODELS = ["core.StandardPage"]    # None = auto-detect
"""
from django.conf import settings

# StreamField names the builder will target, in priority order.
DEFAULT_FIELD_NAMES = ("body",)


def _get(name, default):
    return getattr(settings, name, default)


def preview_css():
    """Static paths or absolute URLs of front-end CSS to load in preview frames."""
    return list(_get("PRBLM_BUILDER_PREVIEW_CSS", []))


def preview_js():
    return list(_get("PRBLM_BUILDER_PREVIEW_JS", []))


def preview_body_class():
    return _get("PRBLM_BUILDER_PREVIEW_BODY_CLASS", "")


def field_names():
    return tuple(_get("PRBLM_BUILDER_FIELD_NAMES", DEFAULT_FIELD_NAMES))


def page_models():
    """Dotted ``app_label.Model`` strings to enable, or ``None`` to auto-detect."""
    return _get("PRBLM_BUILDER_PAGE_MODELS", None)


def header_template():
    """Template that renders the site header, shown atop the builder canvas (or '')."""
    return _get("PRBLM_BUILDER_HEADER_TEMPLATE", "")


def footer_template():
    """Template that renders the site footer, shown below the builder canvas (or '')."""
    return _get("PRBLM_BUILDER_FOOTER_TEMPLATE", "")


def demo_enabled():
    """Whether the block-library/demo page is available (admin-only). On by default."""
    return _get("PRBLM_BUILDER_DEMO", True)


def index_scan_limit():
    """Max pages per model to scan when finding real demo content (newest first).
    Bounds the cost on very large sites; most sites are well under this."""
    return int(_get("PRBLM_BUILDER_INDEX_SCAN_LIMIT", 500))


def exclude_template_prefixes():
    """Block templates under these prefixes are left out of the palette + demo
    (e.g. newsletter email blocks that only render inside an email)."""
    return tuple(_get("PRBLM_BUILDER_EXCLUDE_TEMPLATE_PREFIXES", ()))
