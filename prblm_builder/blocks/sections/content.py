"""Content sections."""
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

from .base import AnchorBlock, BackgroundBlock, IconChoiceBlock, LinkBlock

T = "prblm_builder/blocks/"

COLUMNS = [("2", "2"), ("3", "3"), ("4", "4")]


def eyebrow(default=""):
    return blocks.CharBlock(required=False, default=default,
                            help_text="Optional small label above the heading.")


class TextSectionBlock(blocks.StructBlock):
    content = blocks.RichTextBlock(default=(
        "<h2>A heading for this text</h2>"
        "<p>Use this block for longer writing: an introduction, a story or details "
        "about a service. You can add <b>bold</b> text, <a href=\"#\">links</a> and lists.</p>"
        "<ul><li>Keep paragraphs short</li><li>Use headings to break up long text</li></ul>"
        "<p>Replace this text in the Content tab.</p>"))
    width = blocks.ChoiceBlock(choices=[("narrow", "Narrow (easiest to read)"), ("wide", "Wide")],
                               default="narrow")
    alignment = blocks.ChoiceBlock(choices=[("left", "Left"), ("center", "Centre")], default="left")
    background = BackgroundBlock()
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "text.html"
        icon = "pilcrow"
        label = "Text"
        group = "Content"


class TextImageBlock(blocks.StructBlock):
    eyebrow = eyebrow("Short label")
    heading = blocks.CharBlock(default="A heading that sums up this section")
    text = blocks.RichTextBlock(default=(
        "<p>Explain one idea here, with the image backing it up. Two or three short "
        "paragraphs work best.</p><p>Change the image, and choose which side it sits on, "
        "in the Content tab.</p>"))
    button = LinkBlock(default={"label": "Learn more", "url": "#"})
    image = ImageChooserBlock(required=False)
    image_side = blocks.ChoiceBlock(choices=[("right", "Right"), ("left", "Left")], default="right")
    background = BackgroundBlock()
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "text_image.html"
        icon = "doc-full"
        label = "Text + image"
        group = "Content"


class FeatureItemBlock(blocks.StructBlock):
    icon = IconChoiceBlock()
    title = blocks.CharBlock()
    text = blocks.TextBlock(required=False)


class FeaturesBlock(blocks.StructBlock):
    eyebrow = eyebrow("Why choose us")
    heading = blocks.CharBlock(default="What makes you different")
    intro = blocks.TextBlock(required=False, default="A sentence introducing the points below.")
    columns = blocks.ChoiceBlock(choices=COLUMNS, default="3")
    items = blocks.ListBlock(FeatureItemBlock(), default=[
        {"icon": "zap", "title": "First benefit",
         "text": "One or two sentences about this benefit. Pick an icon that fits."},
        {"icon": "shield", "title": "Second benefit",
         "text": "Keep each point short — people scan these rather than read them."},
        {"icon": "heart", "title": "Third benefit",
         "text": "Three, four or six items look best. Add or remove them in the Content tab."},
    ])
    background = BackgroundBlock()
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "features.html"
        icon = "grid"
        label = "Features"
        group = "Content"


class CardItemBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=False)
    title = blocks.CharBlock()
    text = blocks.TextBlock(required=False)
    link = LinkBlock()


class CardsBlock(blocks.StructBlock):
    eyebrow = eyebrow("Our services")
    heading = blocks.CharBlock(default="Cards for services, projects or articles")
    intro = blocks.TextBlock(required=False, default="Each card can have an image, a short text and a link.")
    columns = blocks.ChoiceBlock(choices=COLUMNS, default="3")
    items = blocks.ListBlock(CardItemBlock(), default=[
        {"title": "First card", "text": "A short description of this item.",
         "link": {"label": "Read more", "url": "#"}},
        {"title": "Second card", "text": "Cards look best with images of the same shape.",
         "link": {"label": "Read more", "url": "#"}},
        {"title": "Third card", "text": "Leave the link label empty to hide the link.",
         "link": {"label": "Read more", "url": "#"}},
    ])
    background = BackgroundBlock(default="muted")
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "cards.html"
        icon = "table"
        label = "Cards"
        group = "Content"
