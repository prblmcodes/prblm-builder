"""Opt-in configuration for the page builder, read from Django settings.

All optional — with nothing set, the builder enables any Page model that has a
StreamField named ``body`` and renders previews unstyled. A host site points the
previews at its own front-end CSS/JS so sections look like production.

    # yoursite/settings.py
    PRBLM_BUILDER_PREVIEW_CSS = ["css/site.css"]         # static paths or URLs
    PRBLM_BUILDER_PREVIEW_JS = ["js/site.js"]
    PRBLM_BUILDER_PREVIEW_BODY_CLASS = "font-body antialiased"
    PRBLM_BUILDER_FIELD_NAMES = ["body"]                 # which StreamField to build
    PRBLM_BUILDER_PAGE_MODELS = ["home.StandardPage"]    # None = auto-detect
    PRBLM_BUILDER_EXCLUDE_BLOCKS = ["link"]              # hide by name or class path

See the README for the full list.
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


def exclude_blocks():
    """Blocks hidden from the palette + Block library, by StreamField name
    (``"link"``) or dotted block class path (``"core.blocks.LinkBlock"`` — also
    hides subclasses). A block can opt out itself with ``class Meta: builder = False``."""
    return tuple(_get("PRBLM_BUILDER_EXCLUDE_BLOCKS", ()))


def library_scope():
    """What the Block library lists: ``"builder"`` (default) = the blocks offered in the
    Layout palettes (top-level blocks of builder-enabled page fields); ``"all"`` = the
    top-level blocks of every StreamField in the project (snippets, settings, …)."""
    scope = _get("PRBLM_BUILDER_LIBRARY_SCOPE", "builder")
    return scope if scope in ("builder", "all") else "builder"


def canvas_width():
    """Desktop width (px) sections render at on the canvas before being scaled to fit."""
    try:
        return max(320, int(_get("PRBLM_BUILDER_CANVAS_WIDTH", 1280)))
    except (TypeError, ValueError):
        return 1280


def placeholder_images():
    """Whether the plugin may create gradient placeholder images in the image library
    when the site has no images to use for demo content."""
    return bool(_get("PRBLM_BUILDER_PLACEHOLDER_IMAGES", True))


def admin_tweaks():
    """Editor niceties that hook into Wagtail admin internals: the full-width Layout tab
    and the 'Block library' link in the editor header. Turn off if a Wagtail upgrade
    breaks them. (The Layout tab and saving work either way.)"""
    return bool(_get("PRBLM_BUILDER_ADMIN_TWEAKS", True))


def site_block_columns():
    """Two-column field layout for the site's **own** blocks too (``True``), or only for the
    built-in blocks and the plugin's own forms (``False``, default). The built-in blocks
    always use two columns, whatever this is."""
    return bool(_get("PRBLM_BUILDER_SITE_BLOCK_COLUMNS", False))


def page_parents():
    """Page types (``"app_label.Model"``) under which editors may add a Builder page."""
    return list(_get("PRBLM_BUILDER_PAGE_PARENTS", []))


def page_type_enabled():
    """Whether editors can create the built-in "Builder page" type (needs the optional
    ``prblm_builder.blocks`` app). Existing Builder pages keep working either way."""
    return bool(_get("PRBLM_BUILDER_PAGE_TYPE", True))
