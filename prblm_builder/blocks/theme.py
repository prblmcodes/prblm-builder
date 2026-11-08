"""Theme values → CSS custom properties for the built-in blocks."""
import re

DEFAULTS = {
    "brand_color": "#2563eb",
    "on_brand_color": "#ffffff",
    "text_color": "#111827",
    "muted_text_color": "#4b5563",
    "background_color": "#ffffff",
    "muted_background_color": "#f3f4f6",
    "dark_background_color": "#0f172a",
    "on_dark_color": "#f8fafc",
    "font_family": "",
    "heading_font_family": "",
    "radius": "medium",
    "content_width": "normal",
}

RADIUS_CHOICES = [("none", "Square"), ("small", "Small"), ("medium", "Medium"), ("large", "Large")]
RADIUS_CSS = {"none": "0px", "small": "4px", "medium": "10px", "large": "20px"}
WIDTH_CHOICES = [("narrow", "Narrow (960px)"), ("normal", "Normal (1200px)"), ("wide", "Wide (1360px)")]
WIDTH_CSS = {"narrow": "960px", "normal": "1200px", "wide": "1360px"}

COLOR_VARS = {
    "brand_color": "--pbk-c-brand",
    "on_brand_color": "--pbk-c-on-brand",
    "text_color": "--pbk-c-text",
    "muted_text_color": "--pbk-c-muted-text",
    "background_color": "--pbk-c-bg",
    "muted_background_color": "--pbk-c-muted-bg",
    "dark_background_color": "--pbk-c-dark-bg",
    "on_dark_color": "--pbk-c-on-dark",
}
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_FONT_UNSAFE = re.compile(r"[;{}<>\\]")


def values_for(request=None):
    """The theme as a plain dict — from the site's Theme settings, else the defaults.
    Never raises (e.g. before ``migrate`` has run, or without a request/site)."""
    out = dict(DEFAULTS)
    try:
        from wagtail.models import Site

        from .models import ThemeSettings
        if request is not None:
            obj = ThemeSettings.for_request(request)
        else:
            site = Site.objects.filter(is_default_site=True).first()
            obj = ThemeSettings.for_site(site) if site else None
        if obj is not None:
            out.update({k: getattr(obj, k) for k in DEFAULTS})
    except Exception:
        pass
    return out


def css(values):
    """``:root{--pbk-…}`` for a theme dict. Values are validated, so a bad entry can't
    break out of the style block."""
    decls = []
    for key, var in COLOR_VARS.items():
        v = values.get(key) or DEFAULTS[key]
        decls.append(f"{var}:{v if _HEX.match(v) else DEFAULTS[key]}")
    decls.append(f"--pbk-radius:{RADIUS_CSS.get(values.get('radius'), RADIUS_CSS['medium'])}")
    decls.append(f"--pbk-width:{WIDTH_CSS.get(values.get('content_width'), WIDTH_CSS['normal'])}")
    for key, var in (("font_family", "--pbk-font"), ("heading_font_family", "--pbk-heading-font")):
        font = _FONT_UNSAFE.sub("", values.get(key) or "").strip()
        if font:
            decls.append(f"{var}:{font}")
    return ":root{" + ";".join(decls) + "}"
