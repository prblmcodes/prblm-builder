"""Trust and conversion sections."""
from wagtail import blocks

from .base import AnchorBlock, BackgroundBlock, LinkBlock

T = "prblm_builder/blocks/"


class CallToActionBlock(blocks.StructBlock):
    heading = blocks.CharBlock(default="Ready to take the next step?")
    text = blocks.TextBlock(
        required=False,
        default="One sentence that tells people what happens when they click the button.")
    primary_button = LinkBlock(default={"label": "Main action", "url": "#contact"})
    secondary_button = LinkBlock(default={"label": "", "url": ""},
                                 help_text="Optional second button. Leave the label empty to hide it.")
    background = BackgroundBlock(default="brand")
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "call_to_action.html"
        icon = "pick"
        label = "Call to action"
        group = "Trust & conversion"


class FAQItemBlock(blocks.StructBlock):
    question = blocks.CharBlock()
    answer = blocks.RichTextBlock(features=["bold", "italic", "link", "ul", "ol"])


class FAQBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(required=False, default="FAQ")
    heading = blocks.CharBlock(default="Frequently asked questions")
    intro = blocks.TextBlock(required=False, default="Answers to the questions people ask most.")
    items = blocks.ListBlock(FAQItemBlock(), default=[
        {"question": "What should go in an FAQ?",
         "answer": "<p>The questions customers ask you most often — before buying, booking or "
                   "getting in touch.</p>"},
        {"question": "How long should an answer be?",
         "answer": "<p>Short: one or two sentences, with a link if there's more to read.</p>"},
        {"question": "How do I change these questions?",
         "answer": "<p>Open the <b>Content</b> tab, find this FAQ block and edit, add or "
                   "remove questions.</p>"},
    ])
    background = BackgroundBlock()
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "faq.html"
        icon = "help"
        label = "FAQ"
        group = "Trust & conversion"
