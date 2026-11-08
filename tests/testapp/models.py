from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page


class StandardPage(Page):
    """A typical block-based page — the plugin should attach to it with no wiring."""

    body = StreamField([
        ("rich_text", blocks.RichTextBlock(template="testapp/blocks/rich_text.html")),
        ("heading", blocks.CharBlock(template="testapp/blocks/heading.html")),
        ("hero", blocks.StructBlock([
            ("title", blocks.CharBlock()),
            ("text", blocks.TextBlock(required=False)),
            ("image", ImageChooserBlock(required=False)),
        ], template="testapp/blocks/hero.html")),
    ], blank=True)

    content_panels = Page.content_panels + [FieldPanel("body")]
