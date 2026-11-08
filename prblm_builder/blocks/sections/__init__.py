"""All built-in section blocks, in palette order."""


def all_blocks():
    """``[(name, block instance), …]`` — fresh instances each call.

    The names are stored in every page that uses a block: never rename one.
    """
    from .content import (CardsBlock, FeaturesBlock, QuoteBlock, StepsBlock, TextImageBlock,
                          TextSectionBlock)
    from .conversion import (CallToActionBlock, FAQBlock, LogoStripBlock, PricingBlock,
                             StatsBlock, TestimonialsBlock)
    from .heroes import HeroBlock, PageBannerBlock
    from .media import GalleryBlock, TeamBlock, VideoBlock
    from .site import FooterBlock, HeaderBlock
    from .utility import ContactInfoBlock, DividerBlock

    return [
        ("header", HeaderBlock()),
        ("hero", HeroBlock()),
        ("page_banner", PageBannerBlock()),
        ("text", TextSectionBlock()),
        ("text_image", TextImageBlock()),
        ("features", FeaturesBlock()),
        ("cards", CardsBlock()),
        ("steps", StepsBlock()),
        ("quote", QuoteBlock()),
        ("testimonials", TestimonialsBlock()),
        ("logo_strip", LogoStripBlock()),
        ("stats", StatsBlock()),
        ("call_to_action", CallToActionBlock()),
        ("faq", FAQBlock()),
        ("pricing", PricingBlock()),
        ("gallery", GalleryBlock()),
        ("video", VideoBlock()),
        ("team", TeamBlock()),
        ("contact_info", ContactInfoBlock()),
        ("divider", DividerBlock()),
        ("footer", FooterBlock()),
    ]
