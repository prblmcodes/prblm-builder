"""Site structure: Header and Footer."""
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

from .base import BackgroundBlock, LinkBlock, SocialChoiceBlock

T = "prblm_builder/blocks/"


class MenuItemBlock(LinkBlock):
    """A menu link with optional one-level dropdown links."""

    children = blocks.ListBlock(
        LinkBlock(), default=[], label="Dropdown links",
        help_text="Optional. Links shown in a dropdown under this item.")


class HeaderBlock(blocks.StructBlock):
    logo = ImageChooserBlock(required=False, help_text="Your logo. Leave empty to show the site name as text.")
    site_name = blocks.CharBlock(default="Your site name", help_text="Shown when there's no logo, and read by screen readers.")
    menu = blocks.ListBlock(MenuItemBlock(), label="Menu", default=[
        {"label": "About", "url": "#about"},
        {"label": "Services", "url": "#services", "children": [
            {"label": "First service", "url": "#services"},
            {"label": "Second service", "url": "#services"},
        ]},
        {"label": "Pricing", "url": "#pricing"},
        {"label": "Contact", "url": "#contact"},
    ])
    button = LinkBlock(default={"label": "Get in touch", "url": "#contact"},
                       help_text="Optional highlighted button on the right. Clear the label to hide it.")
    sticky = blocks.BooleanBlock(required=False, default=False,
                                 help_text="Keep the header at the top of the screen while scrolling.")
    background = BackgroundBlock()

    class Meta:
        template = T + "header.html"
        icon = "list-ul"
        label = "Header"
        group = "Site structure"


class FooterColumnBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False)
    links = blocks.ListBlock(LinkBlock())


class SocialLinkBlock(blocks.StructBlock):
    network = SocialChoiceBlock()
    url = blocks.CharBlock(help_text="Full address of your profile, e.g. https://linkedin.com/company/…")


class FooterBlock(blocks.StructBlock):
    logo = ImageChooserBlock(required=False, help_text="Leave empty to show the site name as text.")
    site_name = blocks.CharBlock(default="Your site name")
    description = blocks.TextBlock(
        required=False,
        default="One or two sentences about who you are and what you do. "
                "Replace this text in the Content tab.")
    columns = blocks.ListBlock(FooterColumnBlock(), label="Link columns", default=[
        {"title": "Company", "links": [{"label": "About us", "url": "#about"},
                                       {"label": "Careers", "url": "#"}]},
        {"title": "Help", "links": [{"label": "FAQ", "url": "#faq"},
                                    {"label": "Contact", "url": "#contact"}]},
        {"title": "Legal", "links": [{"label": "Privacy policy", "url": "#"},
                                     {"label": "Terms", "url": "#"}]},
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
        group = "Site structure"
