"""Site settings for the built-in blocks: the Theme (and, later, Header & footer)."""
from django.core.validators import RegexValidator
from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting
from wagtail.fields import StreamField

from . import theme
from .sections.site import FooterBlock, HeaderBlock

D = theme.DEFAULTS
HEX = RegexValidator(r"^#[0-9a-fA-F]{6}$", "Use a 6-digit hex colour, like #2563eb.")


def _color(default, help_text):
    return models.CharField(max_length=7, default=default, validators=[HEX], help_text=help_text)


def _color_panel(name):
    from django import forms
    return FieldPanel(name, widget=forms.TextInput(attrs={"type": "color"}))


class ThemeSettings(BaseSiteSetting):
    """Colours, fonts and shapes for every built-in block, per site."""

    brand_color = _color(D["brand_color"], "Main accent: buttons, links, 'Brand' backgrounds.")
    on_brand_color = _color(D["on_brand_color"], "Text on top of the brand colour.")
    text_color = _color(D["text_color"], "Main text and headings on light backgrounds.")
    muted_text_color = _color(D["muted_text_color"], "Secondary text (intros, captions).")
    background_color = _color(D["background_color"], "The 'Light' section background.")
    muted_background_color = _color(D["muted_background_color"], "The 'Muted' section background.")
    dark_background_color = _color(D["dark_background_color"], "The 'Dark' section background.")
    on_dark_color = _color(D["on_dark_color"], "Text on dark backgrounds.")
    font_family = models.CharField(
        max_length=200, blank=True,
        help_text="Leave empty to use your site's font. Or a CSS font list, e.g. "
                  "\"Inter, sans-serif\" (the font must already be loaded by your site).")
    heading_font_family = models.CharField(
        max_length=200, blank=True, help_text="Optional different font for headings.")
    radius = models.CharField(
        max_length=10, choices=theme.RADIUS_CHOICES, default=D["radius"],
        help_text="Corner roundness of buttons, cards and images.")
    content_width = models.CharField(
        max_length=10, choices=theme.WIDTH_CHOICES, default=D["content_width"],
        help_text="Maximum width of section content.")

    panels = [
        MultiFieldPanel([_color_panel("brand_color"), _color_panel("on_brand_color")],
                        heading="Brand"),
        MultiFieldPanel([_color_panel("text_color"), _color_panel("muted_text_color"),
                         _color_panel("background_color"), _color_panel("muted_background_color")],
                        heading="Light sections"),
        MultiFieldPanel([_color_panel("dark_background_color"), _color_panel("on_dark_color")],
                        heading="Dark sections"),
        MultiFieldPanel([FieldPanel("font_family"), FieldPanel("heading_font_family")],
                        heading="Fonts"),
        MultiFieldPanel([FieldPanel("radius"), FieldPanel("content_width")], heading="Shape"),
    ]

    class Meta:
        verbose_name = "Theme"
        verbose_name_plural = "Theme"


class SiteChrome(BaseSiteSetting):
    """One Header and one Footer for the whole site. Always shown around the page on the
    builder canvas; on the live site via ``{% prblm_header %}`` / ``{% prblm_footer %}``."""

    header = StreamField(
        [("header", HeaderBlock())], blank=True, max_num=1,
        help_text="Add one Header. It's shown above every page in the builder; put "
                  "{% prblm_header %} in your base template to show it on the site too.")
    footer = StreamField(
        [("footer", FooterBlock())], blank=True, max_num=1,
        help_text="Add one Footer. It's shown below every page in the builder; put "
                  "{% prblm_footer %} in your base template to show it on the site too.")

    panels = [FieldPanel("header"), FieldPanel("footer")]

    class Meta:
        verbose_name = "Header & footer"
        verbose_name_plural = "Header & footer"
