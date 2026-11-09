"""Shared pieces every built-in section uses.

Module paths here are recorded in the migrations of every site that uses the blocks —
don't move or rename these classes after a release.
"""
import re

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.functional import cached_property
from wagtail import blocks
from wagtail.blocks.struct_block import StructBlockAdapter, StructBlockValidationError
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.admin.telepath import register

from prblm_builder.mixins import BuilderSettingsMixin

from .. import icons


LINK_TYPES = [
    ("page", "Page on this site"),
    ("url", "Web address"),
    ("anchor", "Section on this page"),
    ("document", "Document"),
    ("email", "Email address"),
    ("phone", "Phone number"),
]
# The field each link type uses.
LINK_TYPE_FIELDS = {"page": "page", "url": "url", "anchor": "anchor",
                    "document": "document", "email": "email", "phone": "phone"}


def link(label="", target=""):
    """A LinkBlock default value: ``"#contact"`` → a section on this page, anything else
    (``"https://…"``, ``"/path/"``, ``"#"``) → a web address."""
    if target.startswith("#") and len(target) > 1:
        return {"label": label, "link_type": "anchor", "anchor": target[1:]}
    return {"label": label, "link_type": "url", "url": target}


def infer_link_type(value):
    """For links saved before 0.5 (no ``link_type``): a chosen page → page, else address."""
    get = value.get
    return get("link_type") or ("page" if get("page") else "url")


class LinkValue(blocks.StructValue):
    @property
    def link_type(self):
        return infer_link_type(self)

    @property
    def href(self):
        """Where the link goes, according to its link type."""
        kind = self.link_type
        if kind == "page":
            page = self.get("page")
            return (page.url or "") if page else ""
        if kind == "anchor":
            anchor = (self.get("anchor") or "").lstrip("#")
            return f"#{anchor}" if anchor else ""
        if kind == "document":
            doc = self.get("document")
            if not doc:
                return ""
            try:
                return doc.url          # Wagtail's document view (permissions, tracking)
            except Exception:           # the site doesn't route wagtail.documents URLs
                return doc.file.url
        if kind == "email":
            email = self.get("email") or ""
            return f"mailto:{email}" if email else ""
        if kind == "phone":
            phone = re.sub(r"[^\d+]", "", self.get("phone") or "")
            return f"tel:{phone}" if phone else ""
        return self.get("url") or ""

    @property
    def is_external(self):
        return self.href.startswith(("http://", "https://", "//"))


class LinkBlock(blocks.StructBlock):
    """A link or button: a label, a link type, and the one field that type needs.

    In the editor only the selected type's field is shown (see ``link-block.js``)."""

    label = blocks.CharBlock(required=False, help_text="The text people click. Leave empty to hide it.")
    link_type = blocks.ChoiceBlock(
        choices=LINK_TYPES, required=False, label="Link to",
        help_text="What kind of link this is — only that field is shown below.")
    page = blocks.PageChooserBlock(required=False, label="Page")
    url = blocks.CharBlock(required=False, label="Web address",
                           help_text="https://example.com, or a path on this site like /contact/.")
    anchor = blocks.CharBlock(required=False, label="Section ID",
                              help_text="The Anchor ID of a section on this page, e.g. pricing.")
    document = DocumentChooserBlock(required=False, label="Document")
    email = blocks.EmailBlock(required=False, label="Email address")
    phone = blocks.CharBlock(required=False, label="Phone number", help_text="E.g. +44 20 1234 5678.")

    class Meta:
        icon = "link"
        value_class = LinkValue
        form_classname = "pbk-link-block"

    def clean(self, value):
        value = super().clean(value)
        if value.get("label"):
            field = LINK_TYPE_FIELDS.get(infer_link_type(value), "url")
            if not value.get(field):
                raise StructBlockValidationError(block_errors={
                    field: ValidationError("Fill this in, or clear the label to hide the link.")})
        return value


class LinkBlockAdapter(StructBlockAdapter):
    """Adds the small script that shows only the selected link type's field."""

    js_constructor = "prblm_builder.blocks.LinkBlock"

    @cached_property
    def media(self):
        base = super().media
        return forms.Media(js=[*base._js, "prblm_builder/blocks/link-block.js"])


register(LinkBlockAdapter(), LinkBlock)


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


class SectionBlock(BuilderSettingsMixin, blocks.StructBlock):
    """Base for the built-in sections. Their ``background`` and ``anchor_id`` are layout
    settings: edited from the ⚙ button in the Layout tab, and kept in Wagtail's collapsed
    settings area in the Content tab."""

    class Meta:
        group = "Built-in"
        builder_settings = ["background", "anchor_id"]
