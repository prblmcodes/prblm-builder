"""Shared pieces every built-in section uses.

Module paths here are recorded in the migrations of every site that uses the blocks —
don't move or rename these classes after a release.
"""
from django.core.validators import RegexValidator
from wagtail import blocks

from .. import icons


class LinkValue(blocks.StructValue):
    @property
    def href(self):
        """The link target: the chosen page's URL, else the typed address."""
        page = self.get("page")
        if page:
            return page.url or ""
        return self.get("url") or ""

    @property
    def is_external(self):
        return self.href.startswith(("http://", "https://", "//"))


class LinkBlock(blocks.StructBlock):
    """A link or button: a label plus a page on this site *or* a typed address."""

    label = blocks.CharBlock(required=False, help_text="The text people click. Leave empty to hide it.")
    page = blocks.PageChooserBlock(required=False, help_text="Link to a page on this site…")
    url = blocks.CharBlock(
        required=False,
        help_text="…or type an address: https://example.com, /contact/ or #section-id. "
                  "Used when no page is chosen.")

    class Meta:
        icon = "link"
        value_class = LinkValue
        form_classname = "pbk-link-block"


class BackgroundBlock(blocks.ChoiceBlock):
    """The section background — colours come from the Theme."""

    choices = [
        ("light", "Light"),
        ("muted", "Muted (soft grey)"),
        ("dark", "Dark"),
        ("brand", "Brand colour"),
    ]

    # ChoiceBlock ignores Meta.default (its __init__ passes default=None), so set it here.
    def __init__(self, **kwargs):
        kwargs.setdefault("default", "light")
        kwargs.setdefault("help_text", "Section background. Alternate them so the page "
                                       "doesn't look flat.")
        super().__init__(**kwargs)


class AnchorBlock(blocks.CharBlock):
    """An optional HTML id, so menus and buttons can link to ``#this-section``."""

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("max_length", 60)
        kwargs.setdefault("validators", [RegexValidator(
            r"^[A-Za-z][A-Za-z0-9_-]*$",
            "Start with a letter; use only letters, numbers, - and _.")])
        kwargs.setdefault("help_text", "Optional. Lets links jump here: an ID of 'pricing' "
                                       "is reached with #pricing.")
        kwargs.setdefault("label", "Anchor ID")
        super().__init__(**kwargs)


class IconChoiceBlock(blocks.ChoiceBlock):
    """Pick one of the built-in icons."""

    choices = icons.choices()

    def __init__(self, **kwargs):
        kwargs.setdefault("default", "check")
        super().__init__(**kwargs)

    class Meta:
        icon = "pick"


class SocialChoiceBlock(blocks.ChoiceBlock):
    choices = icons.social_choices()

    def __init__(self, **kwargs):
        kwargs.setdefault("default", "linkedin")
        super().__init__(**kwargs)


class SectionBlock(blocks.StructBlock):
    """Base for full-width sections. Subclasses add their fields, then end with
    ``background = BackgroundBlock()`` and ``anchor_id = AnchorBlock()``."""

    class Meta:
        group = "Built-in"
