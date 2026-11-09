"""The example blocks from docs/EXAMPLES.md (kept identical — tests use them)."""
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

from prblm_builder.mixins import BuilderSettingsMixin


# 1. A simple block: a template, a description and a preview value.
class HeadingBlock(blocks.CharBlock):
    class Meta:
        template = "examples/blocks/heading.html"
        icon = "title"
        description = "A large heading that starts a new part of the page."
        preview_value = "A heading for the next part of the page"


# 2. A small piece used inside other blocks — hidden from the Layout palette.
class ButtonLinkBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=False)
    url = blocks.CharBlock(required=False, help_text="https://…, /path/ or #section")

    class Meta:
        template = "examples/blocks/button.html"
        icon = "link"
        builder = False          # not a section: never offered in the Layout palette


# 3. A section with layout settings (⚙ in the Layout tab).
class PromoBlock(BuilderSettingsMixin, blocks.StructBlock):
    title = blocks.CharBlock()
    text = blocks.TextBlock(required=False)
    image = ImageChooserBlock(required=False)
    button = ButtonLinkBlock()
    # Layout settings — listed in Meta.builder_settings:
    background = blocks.ChoiceBlock(
        choices=[("light", "Light"), ("dark", "Dark")], default="light")
    anchor_id = blocks.CharBlock(required=False, label="Anchor ID")

    class Meta:
        template = "examples/blocks/promo.html"
        icon = "pick"
        group = "Marketing"
        description = "A highlighted band with a title, text, image and button."
        preview_value = {
            "title": "Spring sale: 20% off everything",
            "text": "Use this block to point people at one thing you want them to do.",
            "button": {"label": "Shop now", "url": "#shop"},
            "background": "dark",
        }
        builder_settings = ["background", "anchor_id"]
