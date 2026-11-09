"""Site structure: Header and Footer."""
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

from .base import BackgroundBlock, LinkBlock, SocialChoiceBlock, link, SectionBlock

T = "prblm_builder/blocks/"


class MenuItemBlock(LinkBlock):
    """A menu link with optional one-level dropdown links."""

    children = blocks.ListBlock(
        LinkBlock(), default=[], label="Dropdown links",
        help_text="Optional. Links shown in a dropdown under this item.")


class HeaderBlock(SectionBlock):
    logo = ImageChooserBlock(required=False, help_text="Your logo. Leave empty to show the site name as text.")
    site_name = blocks.CharBlock(default="Your site name", help_text="Shown when there's no logo, and read by screen readers.")
    menu = blocks.ListBlock(MenuItemBlock(), label="Menu", default=[
        link("About", "#about"),
        {**link("Services", "#services"), "children": [
            link("First service", "#services"),
            link("Second service", "#services"),
        ]},
        link("Pricing", "#pricing"),
        link("Contact", "#contact"),
    ])
    button = LinkBlock(default=link("Get in touch", "#contact"),
                       help_text="Optional highlighted button on the right. Clear the label to hide it.")
    sticky = blocks.BooleanBlock(required=False, default=False,
                                 help_text="Keep the header at the top of the screen while scrolling.")
    background = BackgroundBlock()

    class Meta:
        template = T + "header.html"
        icon = "list-ul"
        label = "Header"
        description = "Logo or site name, menu with dropdowns and a button; collapses on mobile."
        group = "Site structure"


class FooterColumnBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False)
    links = blocks.ListBlock(LinkBlock())


class SocialLinkBlock(blocks.StructBlock):
    network = SocialChoiceBlock()
    url = blocks.CharBlock(help_text="Full address of your profile, e.g. https://linkedin.com/company/…")


class FooterBlock(SectionBlock):
    logo = ImageChooserBlock(required=False, help_text="Leave empty to show the site name as text.")
    site_name = blocks.CharBlock(default="Your site name")
    description = blocks.TextBlock(
        required=False,
        default="One or two sentences about who you are and what you do. "
                "Replace this text in the Content tab.")
    columns = blocks.ListBlock(FooterColumnBlock(), label="Link columns", default=[
        {"title": "Company", "links": [link("About us", "#about"),
                                       link("Careers", "#")]},
        {"title": "Help", "links": [link("FAQ", "#faq"),
                                    link("Contact", "#contact")]},
        {"title": "Legal", "links": [link("Privacy policy", "#"),
                                     link("Terms", "#")]},
    ])
    social = blocks.ListBlock(SocialLinkBlock(), label="Social links", default=[
        {"network": "linkedin", "url": "https://www.linkedin.com/"},
        {"network": "instagram", "url": "https://www.instagram.com/"},
    ])
    copyright = blocks.CharBlock(
        required=False, default="Your company name. All rights reserved.",
        help_text="The © symbol and current year are added automatically.")
    background = BackgroundBlock(default="dark")

    class Meta:
        template = T + "footer.html"
        icon = "list-ul"
        label = "Footer"
        description = "Logo, short description, link columns, social links and copyright."
        group = "Site structure"
