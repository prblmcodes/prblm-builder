"""The example page models from docs/EXAMPLES.md (kept identical — tests use them)."""
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page

from prblm_builder.blocks import builder_blocks

from .blocks import ButtonLinkBlock, CardBlock, HeadingBlock, PromoBlock


# A. Your own blocks only. A StreamField named `body` is all the plugin needs.
class ArticlePage(Page):
    body = StreamField([
        ("heading", HeadingBlock()),
        ("paragraph", blocks.RichTextBlock(template="examples/blocks/paragraph.html")),
        ("promo", PromoBlock()),
        ("button", ButtonLinkBlock()),   # allowed in the body, but hidden from the palette
    ], blank=True)

    content_panels = Page.content_panels + [FieldPanel("body")]


# B. Built-in blocks + your own, side by side.
class LandingPage(Page):
    body = StreamField(
        builder_blocks(exclude=["text"]) + [("promo", PromoBlock()), ("card", CardBlock())],
        blank=True,
    )

    content_panels = Page.content_panels + [FieldPanel("body")]
