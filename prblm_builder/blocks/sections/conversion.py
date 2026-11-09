"""Trust and conversion sections."""
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

from .base import AnchorBlock, BackgroundBlock, LinkBlock, link

T = "prblm_builder/blocks/"


class CallToActionBlock(blocks.StructBlock):
    heading = blocks.CharBlock(default="Ready to take the next step?")
    text = blocks.TextBlock(
        required=False,
        default="One sentence that tells people what happens when they click the button.")
    primary_button = LinkBlock(default=link("Main action", "#contact"))
    secondary_button = LinkBlock(default=link("", ""),
                                 help_text="Optional second button. Leave the label empty to hide it.")
    background = BackgroundBlock(default="brand")
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "call_to_action.html"
        icon = "pick"
        label = "Call to action"
        description = "A coloured band with a headline and buttons."
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
        description = "Questions that expand to show their answers."
        group = "Trust & conversion"


class TestimonialItemBlock(blocks.StructBlock):
    quote = blocks.TextBlock()
    name = blocks.CharBlock()
    role = blocks.CharBlock(required=False, help_text="Role, company or city.")
    photo = ImageChooserBlock(required=False, help_text="Optional. A square photo works best.")


class TestimonialsBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(required=False, default="Testimonials")
    heading = blocks.CharBlock(default="What people say about you")
    intro = blocks.TextBlock(required=False, default="Real quotes from real customers build trust.")
    items = blocks.ListBlock(TestimonialItemBlock(), default=[
        {"quote": "Paste a short quote from a happy customer here. Two or three sentences is plenty.",
         "name": "Customer name", "role": "Their role or company"},
        {"quote": "Specific quotes work best: what problem you solved and what changed for them.",
         "name": "Customer name", "role": "Their role or company"},
        {"quote": "Ask permission before using someone's name and photo.",
         "name": "Customer name", "role": "Their role or company"},
    ])
    background = BackgroundBlock()
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "testimonials.html"
        icon = "openquote"
        label = "Testimonials"
        description = "Customer quotes with name, role and optional photo."
        group = "Trust & conversion"


class LogoItemBlock(blocks.StructBlock):
    logo = ImageChooserBlock(required=False, help_text="Leave empty to show the name as text.")
    name = blocks.CharBlock(help_text="Used as the logo's alt text.")
    url = blocks.CharBlock(required=False, help_text="Optional link to their website.")


class LogoStripBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False, default="Trusted by teams at")
    items = blocks.ListBlock(LogoItemBlock(), default=[
        {"name": "Client one"}, {"name": "Client two"}, {"name": "Client three"},
        {"name": "Client four"}, {"name": "Client five"},
    ])
    greyscale = blocks.BooleanBlock(required=False, default=True,
                                    help_text="Show logos in grey so they look consistent.")
    background = BackgroundBlock()
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "logos.html"
        icon = "image"
        label = "Logo strip"
        description = "A row of client or partner logos (or names)."
        group = "Trust & conversion"


class StatItemBlock(blocks.StructBlock):
    number = blocks.CharBlock(help_text="E.g. 500+, 98%, 12 yrs.")
    label = blocks.CharBlock()
    note = blocks.CharBlock(required=False)


class StatsBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False, default="Numbers that show your impact")
    items = blocks.ListBlock(StatItemBlock(), default=[
        {"number": "500+", "label": "Happy customers", "note": "Replace with your own numbers"},
        {"number": "12", "label": "Years of experience", "note": ""},
        {"number": "98%", "label": "Would recommend us", "note": ""},
        {"number": "24h", "label": "Average reply time", "note": ""},
    ])
    background = BackgroundBlock(default="dark")
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "stats.html"
        icon = "order"
        label = "Stats"
        description = "Big numbers with labels, like “500+ customers”."
        group = "Trust & conversion"


class PlanBlock(blocks.StructBlock):
    name = blocks.CharBlock()
    price = blocks.CharBlock(help_text="E.g. €29, Free, On request.")
    period = blocks.CharBlock(required=False, help_text="E.g. per month.")
    description = blocks.TextBlock(required=False)
    features = blocks.ListBlock(blocks.CharBlock(label="Feature"), default=[])
    button = LinkBlock()
    highlighted = blocks.BooleanBlock(required=False, help_text="Make this plan stand out.")


class PricingBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(required=False, default="Pricing")
    heading = blocks.CharBlock(default="Simple, clear pricing")
    intro = blocks.TextBlock(required=False, default="Two to four plans. Highlight the one most people choose.")
    plans = blocks.ListBlock(PlanBlock(), default=[
        {"name": "Basic", "price": "€19", "period": "per month",
         "description": "For people just getting started.",
         "features": ["What's included", "Another feature", "Keep the list short"],
         "button": link("Choose Basic", "#contact"), "highlighted": False},
        {"name": "Popular", "price": "€49", "period": "per month",
         "description": "The plan most people pick — it's highlighted.",
         "features": ["Everything in Basic", "A bigger feature", "Priority support"],
         "button": link("Choose Popular", "#contact"), "highlighted": True},
        {"name": "Custom", "price": "On request", "period": "",
         "description": "For larger teams with special needs.",
         "features": ["Everything in Popular", "Tailored setup"],
         "button": link("Contact us", "#contact"), "highlighted": False},
    ])
    background = BackgroundBlock()
    anchor_id = AnchorBlock(default="pricing")

    class Meta:
        template = T + "pricing.html"
        icon = "list-ul"
        label = "Pricing"
        description = "Plan columns with prices, features and a highlighted plan."
        group = "Trust & conversion"
