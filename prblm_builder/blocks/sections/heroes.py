"""Page openers: Hero and Page banner."""
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

from .base import AnchorBlock, BackgroundBlock, LinkBlock

T = "prblm_builder/blocks/"


class HeroBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(required=False, default="Short label above the headline",
                               help_text="Optional small text above the headline.")
    heading = blocks.CharBlock(default="Your main headline — say what you do in a few words")
    text = blocks.TextBlock(
        required=False,
        default="One or two sentences explaining who this is for and why it matters. "
                "Edit this text, the buttons and the image in the Content tab.")
    primary_button = LinkBlock(default={"label": "Main action", "url": "#contact"})
    secondary_button = LinkBlock(default={"label": "Second action", "url": "#about"})
    image = ImageChooserBlock(required=False)
    image_position = blocks.ChoiceBlock(
        choices=[("side", "Beside the text"), ("background", "Behind the text"), ("none", "No image")],
        default="side")
    alignment = blocks.ChoiceBlock(choices=[("left", "Left"), ("center", "Centre")], default="left",
                                   help_text="Text alignment (centre works best without a side image).")
    background = BackgroundBlock()
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "hero.html"
        icon = "image"
        label = "Hero"
        description = "Big page opener: headline, text, two buttons and an image."
        group = "Page openers"


class PageBannerBlock(blocks.StructBlock):
    heading = blocks.CharBlock(default="Page title")
    intro = blocks.TextBlock(
        required=False,
        default="A short introduction to this page — one or two sentences.")
    show_breadcrumbs = blocks.BooleanBlock(
        required=False, default=True,
        help_text="Show the path to this page (Home › Section › Page) above the title.")
    background = BackgroundBlock(default="muted")
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "page_banner.html"
        icon = "title"
        label = "Page banner"
        description = "Title strip for inner pages, with optional breadcrumbs."
        group = "Page openers"
