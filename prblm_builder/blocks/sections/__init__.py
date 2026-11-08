"""All built-in section blocks, in palette order."""


def all_blocks():
    """``[(name, block instance), …]`` — fresh instances each call.

    The names are stored in every page that uses a block: never rename one.
    """
    from .content import CardsBlock, FeaturesBlock, TextImageBlock, TextSectionBlock
    from .conversion import CallToActionBlock, FAQBlock
    from .heroes import HeroBlock, PageBannerBlock
    from .site import FooterBlock, HeaderBlock
    from .utility import ContactInfoBlock

    return [
        ("header", HeaderBlock()),
        ("hero", HeroBlock()),
        ("page_banner", PageBannerBlock()),
        ("text", TextSectionBlock()),
        ("text_image", TextImageBlock()),
        ("features", FeaturesBlock()),
        ("cards", CardsBlock()),
        ("call_to_action", CallToActionBlock()),
        ("faq", FAQBlock()),
        ("contact_info", ContactInfoBlock()),
        ("footer", FooterBlock()),
    ]
