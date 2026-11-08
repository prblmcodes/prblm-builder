from django.db import models
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page

from prblm_builder.blocks import builder_blocks


class LinkBlock(blocks.StructBlock):
    """A reusable link fragment — used inside other blocks and in the footer snippet,
    never as a page section."""
    text = blocks.CharBlock()
    url = blocks.URLBlock(required=False)

    class Meta:
        template = "testapp/blocks/link.html"


class StandardPage(Page):
    """A typical block-based page — the plugin should attach to it with no wiring."""

    body = StreamField([
        ("rich_text", blocks.RichTextBlock(template="testapp/blocks/rich_text.html")),
        ("heading", blocks.CharBlock(template="testapp/blocks/heading.html")),
        ("hero", blocks.StructBlock([
            ("title", blocks.CharBlock()),
            ("text", blocks.TextBlock(required=False)),
            ("image", ImageChooserBlock(required=False)),
            ("cta", LinkBlock(required=False)),
        ], template="testapp/blocks/hero.html")),
        # Opted out of the builder via its own Meta.
        ("internal_note", blocks.CharBlock(template="testapp/blocks/heading.html", builder=False)),
        # Can't be previewed: errors / shows nothing.
        ("broken", blocks.CharBlock(template="testapp/blocks/broken.html")),
        ("spacer", blocks.CharBlock(template="testapp/blocks/spacer.html", required=False)),
    ], blank=True)

    content_panels = Page.content_panels + [FieldPanel("body")]


class FooterSettings(models.Model):
    """A non-page model with a StreamField — its blocks aren't page sections."""

    links = StreamField([("footer_link", LinkBlock())], blank=True)


class BlocksPage(Page):
    """A page made only of the built-in blocks (via the helper), plus one own block."""

    body = StreamField(
        builder_blocks() + [("own_heading", blocks.CharBlock(template="testapp/blocks/heading.html"))],
        blank=True)

    content_panels = Page.content_panels + [FieldPanel("body")]
