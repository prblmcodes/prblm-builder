"""Built-in blocks app models: the Theme, reusable Headers / Footers, the Builder page."""
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting
from wagtail.fields import StreamField
from wagtail.models import Page

from . import builder_blocks, theme
from .fields import BuilderBodyField, body_blocks
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


def _stored(name, block):
    # Stored (JSON-ready) form — works both for new model instances and as the initial
    # value of Wagtail's add form (which can't read (name, value) tuples).
    return [{"type": name, "value": block.get_prep_value(block.get_default())}]


def header_default():
    """A new Header starts with the block's explanatory example content."""
    return _stored("header", HeaderBlock())


def footer_default():
    return _stored("footer", FooterBlock())


class _ChromeItemForm(WagtailAdminModelForm):
    """Wagtail's add view builds this form without an instance, so Django would use the
    field's raw callable default (which the StreamField widget can't render) and add a
    hidden "initial" copy of it. Take the starting content from a fresh instance instead."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "content" in self.fields:
            self.fields["content"].show_hidden_initial = False
            if not self.is_bound and "content" not in self.initial:
                self.initial["content"] = self.instance.content


class _SiteChromeItem(models.Model):
    """Shared by SiteHeader / SiteFooter: a named, reusable header or footer."""

    name = models.CharField(max_length=100, help_text="For your reference, e.g. \"Main header\".")
    is_default = models.BooleanField(
        default=False, verbose_name="Use as site default",
        help_text="Shown on pages that don't choose another one (only one can be the default).")

    base_form_class = _ChromeItemForm

    class Meta:
        abstract = True
        ordering = ["-is_default", "name"]

    def __str__(self):
        return f"{self.name} (site default)" if self.is_default else self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:  # only one default per kind
            type(self).objects.exclude(pk=self.pk).filter(is_default=True).update(is_default=False)

    def render(self, request=None, page=None):
        """This header/footer's HTML (``""`` if its content is empty)."""
        stream = self.content
        if not stream:
            return ""
        return stream[0].render(context={"request": request, "page": page, "self": page})


class SiteHeader(_SiteChromeItem):
    content = StreamField([("header", HeaderBlock())], min_num=1, max_num=1,
                          default=header_default, verbose_name="Header")

    panels = [FieldPanel("name"), FieldPanel("is_default"), FieldPanel("content")]

    class Meta(_SiteChromeItem.Meta):
        verbose_name = "Header"
        verbose_name_plural = "Headers"


class SiteFooter(_SiteChromeItem):
    content = StreamField([("footer", FooterBlock())], min_num=1, max_num=1,
                          default=footer_default, verbose_name="Footer")

    panels = [FieldPanel("name"), FieldPanel("is_default"), FieldPanel("content")]

    class Meta(_SiteChromeItem.Meta):
        verbose_name = "Footer"
        verbose_name_plural = "Footers"


CHROME_CHOICES = [
    ("default", "Site default"),
    ("custom", "Choose one"),
    ("site", "My site's own (from the template setting)"),
    ("none", "None"),
]


class BuilderPage(Page):
    """A ready-made page type built from the 21 built-in blocks — no code needed.

    Renders as a complete page (header, sections, footer) from
    ``prblm_builder/blocks/builder_page.html``; put a template with that name in your own
    templates folder to render it inside your site's layout instead. Hide the type from
    "Add page" with ``PRBLM_BUILDER_PAGE_TYPE = False``.
    """

    # Built-ins + PRBLM_BUILDER_PAGE_EXTRA_BLOCKS; migrations only ever see the built-ins.
    body = BuilderBodyField(
        body_blocks(builder_blocks(), getattr(settings, "PRBLM_BUILDER_PAGE_EXTRA_BLOCKS", None)),
        blank=True, migration_blocks=builder_blocks())
    header_choice = models.CharField(
        "Header", max_length=10, choices=CHROME_CHOICES, default="default",
        help_text="\"My site's own\" uses PRBLM_BUILDER_HEADER_TEMPLATE.")
    header = models.ForeignKey(
        SiteHeader, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        help_text="Used when Header is \"Choose one\".")
    footer_choice = models.CharField(
        "Footer", max_length=10, choices=CHROME_CHOICES, default="default",
        help_text="\"My site's own\" uses PRBLM_BUILDER_FOOTER_TEMPLATE.")
    footer = models.ForeignKey(
        SiteFooter, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        help_text="Used when Footer is \"Choose one\".")

    content_panels = Page.content_panels + [FieldPanel("body")]
    # Header / footer are layout, not content: edited from the "Page" tab of the Layout
    # sidebar (one dropdown each), which writes into these hidden fields.
    builder_layout_panels = [
        FieldPanel(name, attrs={"data-prblm-page-option": ""})
        for name in ("header_choice", "header", "footer_choice", "footer")
    ]
    template = "prblm_builder/blocks/builder_page.html"

    class Meta:
        verbose_name = "Builder page"
