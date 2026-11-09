"""Utility sections."""
from wagtail import blocks

from .base import AnchorBlock, BackgroundBlock, LinkBlock, link

T = "prblm_builder/blocks/"


class ContactInfoBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(required=False, default="Contact")
    heading = blocks.CharBlock(default="How to reach us")
    intro = blocks.TextBlock(required=False,
                             default="Tell people the best way to get in touch and when you'll reply.")
    address = blocks.TextBlock(required=False, default="Street and number\nPostcode City\nCountry")
    email = blocks.EmailBlock(required=False, default="hello@example.com")
    phone = blocks.CharBlock(required=False, default="+00 123 456 789")
    hours = blocks.TextBlock(required=False, default="Monday – Friday: 9:00 – 17:00\nWeekends: closed")
    map_link = LinkBlock(default=link("Get directions", "https://www.openstreetmap.org/"),
                         help_text="Optional link to a map. Leave the label empty to hide it.")
    background = BackgroundBlock(default="muted")
    anchor_id = AnchorBlock(default="contact")

    class Meta:
        template = T + "contact_info.html"
        icon = "mail"
        label = "Contact info"
        description = "Address, email, phone, opening hours and a map link."
        group = "Utility"


class DividerBlock(blocks.StructBlock):
    style = blocks.ChoiceBlock(choices=[("line", "Line"), ("space", "Empty space")], default="line")
    size = blocks.ChoiceBlock(choices=[("small", "Small"), ("medium", "Medium"), ("large", "Large")],
                              default="medium", help_text="How much space above and below.")
    background = BackgroundBlock()

    class Meta:
        template = T + "divider.html"
        icon = "minus"
        label = "Divider"
        description = "A line or empty space between sections."
        group = "Utility"
