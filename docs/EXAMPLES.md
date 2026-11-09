# prblm-builder — examples

Copy-paste examples for using the plugin with **your own** page models and blocks. Every
example here is real code: it lives in [`tests/examples/`](../tests/examples/) and is
checked by [`tests/test_examples.py`](../tests/test_examples.py), so it keeps working.

For installation and the full settings list, see the [README](../README.md).

- [1. A page model the builder picks up](#1-a-page-model-the-builder-picks-up)
- [2. A simple block: template, description, preview value](#2-a-simple-block-template-description-preview-value)
- [3. A block that isn't a section (hidden from the palette)](#3-a-block-that-isnt-a-section-hidden-from-the-palette)
- [4. A section with layout settings (⚙)](#4-a-section-with-layout-settings-)
- [5. Reuse the built-in link block](#5-reuse-the-built-in-link-block)
- [6. Built-in blocks next to your own](#6-built-in-blocks-next-to-your-own)
- [7. Your blocks on the ready-made Builder page](#7-your-blocks-on-the-ready-made-builder-page)
- [8. Header and footer in your base template](#8-header-and-footer-in-your-base-template)
- [9. A different field name, or only some page types](#9-a-different-field-name-or-only-some-page-types)
- [10. Checklist: why isn't my block in the palette?](#10-checklist-why-isnt-my-block-in-the-palette)

---

## 1. A page model the builder picks up

A page model with a **StreamField named `body`** gets the **Layout** tab automatically —
no mixin, no registration. Each block that has a **template** becomes a section you can drag
onto the canvas.

```python
# myapp/models.py
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page

from .blocks import ButtonLinkBlock, HeadingBlock, PromoBlock


class ArticlePage(Page):
    body = StreamField([
        ("heading", HeadingBlock()),
        ("paragraph", blocks.RichTextBlock(template="myapp/blocks/paragraph.html")),
        ("promo", PromoBlock()),
        ("button", ButtonLinkBlock()),   # allowed in the body, but hidden from the palette
    ], blank=True)

    content_panels = Page.content_panels + [FieldPanel("body")]
```

```django
{# myapp/templates/myapp/blocks/paragraph.html #}
<div class="paragraph">{{ value }}</div>
```

What editors get: **Layout** opens first (drag, reorder, duplicate, copy / paste, ⚙
settings), the **Content** tab is Wagtail's normal editor, and both save with the page.

## 2. A simple block: template, description, preview value

```python
# myapp/blocks.py
from wagtail import blocks


class HeadingBlock(blocks.CharBlock):
    class Meta:
        template = "myapp/blocks/heading.html"
        icon = "title"
        description = "A large heading that starts a new part of the page."
        preview_value = "A heading for the next part of the page"
```

```django
{# myapp/templates/myapp/blocks/heading.html #}
<h2 class="heading">{{ value }}</h2>
```

- **`template`** is required — it's what the canvas and the Block library render.
- **`description`** (Wagtail 6.4+) shows in the Block library and as a tooltip in the
  Layout sidebar, and is searchable.
- **`preview_value`** (Wagtail 6.4+) is the content used for the sidebar thumbnail, the
  Block library, and as the starting content when the block is added to a page. Without it
  the plugin uses real content from elsewhere on the site, else generated text.

## 3. A block that isn't a section (hidden from the palette)

Small pieces used *inside* other blocks — links, buttons, cards — usually shouldn't be
dragged onto a page on their own. If one is also a top-level option of your `body` (like
`"button"` above), hide it:

```python
class ButtonLinkBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=False)
    url = blocks.CharBlock(required=False, help_text="https://…, /path/ or #section")

    class Meta:
        template = "myapp/blocks/button.html"
        icon = "link"
        builder = False          # not a section: never offered in the Layout palette
```

```django
{# myapp/templates/myapp/blocks/button.html #}
{% if value.label %}<a class="button" href="{{ value.url|default:"#" }}">{{ value.label }}</a>{% endif %}
```

Blocks used **only** inside other blocks never appear anyway — `builder = False` is for
the ones that are also offered at the top level. You can also hide blocks from settings:
`PRBLM_BUILDER_EXCLUDE_BLOCKS = ["button", "myapp.blocks.ButtonLinkBlock"]` (by name, or by
full class path — see the README's *Hiding a block*).

## 4. A section with layout settings (⚙)

Some fields are about *how* a section looks, not *what it says*: a background, an anchor
ID, a "compact" switch. List them in `Meta.builder_settings` and they get a **⚙** button on
the section in the Layout tab. Add `BuilderSettingsMixin` to also move them into Wagtail's
collapsed **settings** area in the Content tab.

```python
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

from prblm_builder.mixins import BuilderSettingsMixin


class PromoBlock(BuilderSettingsMixin, blocks.StructBlock):
    title = blocks.CharBlock()
    text = blocks.TextBlock(required=False)
    image = ImageChooserBlock(required=False)
    button = ButtonLinkBlock()
    # Layout settings — listed in Meta.builder_settings:
    background = blocks.ChoiceBlock(
        choices=[("light", "Light"), ("dark", "Dark")], default="light")
    anchor_id = blocks.CharBlock(required=False, label="Anchor ID")

    class Meta:
        template = "myapp/blocks/promo.html"
        icon = "pick"
        group = "Marketing"
        description = "A highlighted band with a title, text, image and button."
        preview_value = {
            "title": "Spring sale: 20% off everything",
            "text": "Use this block to point people at one thing you want them to do.",
            "button": {"label": "Shop now", "url": "#shop"},
            "background": "dark",
        }
        builder_settings = ["background", "anchor_id"]
```

Use the settings in the template like any other field:

```django
{# myapp/templates/myapp/blocks/promo.html #}
{% load wagtailcore_tags wagtailimages_tags %}
<section class="promo promo--{{ value.background }}"{% if value.anchor_id %} id="{{ value.anchor_id }}"{% endif %}>
  <h2>{{ value.title }}</h2>
  {% if value.text %}<p>{{ value.text }}</p>{% endif %}
  {% if value.image %}{% image value.image width-800 %}{% endif %}
  {% include_block value.button %}
</section>
```

Good to know:

- The ⚙ panel shows **choices, on/off switches and short text** fields. Choosers, rich
  text and nested blocks stay in the Content tab.
- A change in the ⚙ panel shows on the canvas at once and also updates the same field in
  the Content tab (and the other way round).
- **`group`** puts the block under its own heading ("Marketing") in the Layout sidebar and
  the Block library.
- Colour **swatches**: the four background names `light / muted / dark / brand` show as
  swatches; for the built-in blocks they use your Theme's colours, for your own blocks just
  the names (your CSS decides what "dark" means).
- **Two-column fields** in the Content tab are always on for the built-in blocks; turn them
  on for your own blocks with `PRBLM_BUILDER_SITE_BLOCK_COLUMNS = True`.

## 5. Reuse the built-in link block

With `prblm_builder.blocks` installed, use its link block inside your own blocks. Editors get
a **Label**, a **Link to** choice (page on this site, web address, section on this page,
document, email, phone) and only the one field that choice needs.

```python
from wagtail import blocks

from prblm_builder.blocks import LinkBlock


class CardBlock(blocks.StructBlock):
    title = blocks.CharBlock()
    text = blocks.TextBlock(required=False)
    link = LinkBlock(label="Button")

    class Meta:
        template = "myapp/blocks/card.html"
        icon = "doc-full"
        preview_value = {
            "title": "Our services",
            "text": "What we do, in one or two sentences.",
            "link": {"label": "Read more", "link_type": "anchor", "anchor": "services"},
        }
```

In the template, `href` gives the right address for whichever type was chosen
(`/about/`, `https://…`, `#services`, `mailto:…`, `tel:…`, a document URL), and
`is_external` tells you if it leaves the site:

```django
{# myapp/templates/myapp/blocks/card.html #}
<div class="card">
  <h3>{{ value.title }}</h3>
  {% if value.text %}<p>{{ value.text }}</p>{% endif %}
  {% with link=value.link %}
    {% if link.label and link.href %}
      <a class="card__button" href="{{ link.href }}"{% if link.is_external %} target="_blank" rel="noopener"{% endif %}>{{ link.label }}</a>
    {% endif %}
  {% endwith %}
</div>
```

- A link with an **empty label** is treated as "no link" — editors can leave it empty to
  hide the button. With a label, the field for the chosen type must be filled in.
- More than one: `buttons = blocks.ListBlock(LinkBlock())`, then `{% for link in
  value.buttons %}…{% endfor %}`.
- The import path `prblm_builder.blocks.LinkBlock` stays stable (it ends up in your
  migrations).

## 6. Built-in blocks next to your own

With the optional `prblm_builder.blocks` app installed, add the 21 built-in sections to any
page model:

```python
from prblm_builder.blocks import builder_blocks


class LandingPage(Page):
    body = StreamField(
        builder_blocks(exclude=["text"]) + [("promo", PromoBlock()), ("card", CardBlock())],
        blank=True,
    )

    content_panels = Page.content_panels + [FieldPanel("body")]
```

- `exclude=[…]` leaves built-in blocks out (e.g. one whose name clashes with yours);
  `only=[…]` keeps just some. An unknown name raises an error listing the valid ones.
- Run `python manage.py makemigrations` after adding `builder_blocks()` — Wagtail records a
  page's allowed blocks in your app's migrations. (Plugin upgrades that change the built-in
  blocks may add another small "Alter field" migration; it never changes your content.)
- The Layout sidebar lists **Built-in blocks** and **Your site's blocks** separately.

## 7. Your blocks on the ready-made Builder page

The Builder page (from `prblm_builder.blocks`) has all built-in blocks. Add your own — no
migration needed:

```python
# settings.py
PRBLM_BUILDER_PAGE_EXTRA_BLOCKS = [
    ("promo", "myapp.blocks.PromoBlock"),      # ("name", "full.path.to.Block")
]
# or a function returning [(name, block), …]:
# PRBLM_BUILDER_PAGE_EXTRA_BLOCKS = "myapp.blocks.builder_page_blocks"

# The name may differ from the one your other pages use ("promo" vs "site_promo"): blocks
# are matched by class, so demos and the Block library treat them as one block.

# Let editors add Builder pages under your home page (if it limits its child page types):
PRBLM_BUILDER_PAGE_PARENTS = ["home.HomePage"]
```

## 8. Header and footer in your base template

Headers and Footers are created under **Page builder → Headers / Footers**. To show the
site-default ones (and the built-in blocks' styles) on your own pages too — the Builder page
does this automatically:

```django
{# templates/base.html #}
{% load static prblm_blocks %}
<head>
  …
  <link rel="stylesheet" href="{% static 'css/main.css' %}">
  {% prblm_assets %}   {# the built-in blocks' CSS + Theme colours — after your own CSS #}
</head>
<body>
  {% prblm_header %}
  {% block content %}{% endblock %}
  {% prblm_footer %}
</body>
```

`{% prblm_header "Campaign header" %}` picks one by name. Each tag renders nothing if there
is no matching header/footer.

**Styles stay separate both ways.** The built-in blocks' CSS only styles the blocks (every
rule is scoped to `.pbk…` classes), so it never touches your header, footer or own
sections. And inside a built-in block every element is reset to the browser's defaults
before the block's own styles apply, so your site's global rules (`p { line-height: 2 }`,
`ul { list-style: none }`, Tailwind's reset, `header { position: sticky }`…) don't change
how a built-in block looks. Only rules with `!important`, or rules on the blocks' own
`pbk-` class names, can still reach them.

**Builder pages** are standalone pages. They load your site's CSS / JS
(`PRBLM_BUILDER_PREVIEW_CSS` / `_JS`, plus `PRBLM_BUILDER_PREVIEW_BODY_CLASS`) only when they
need it: when the page shows **your site's header or footer**, or contains **your own
blocks**. A Builder page with only built-in blocks and plugin headers/footers loads none of
your CSS. To show *your own* header on the builder canvas instead, set
`PRBLM_BUILDER_HEADER_TEMPLATE = "includes/header.html"` (and `_FOOTER_TEMPLATE`).

## 9. A different field name, or only some page types

```python
# settings.py
PRBLM_BUILDER_FIELD_NAMES = ["body", "content"]   # first one a model has is used
PRBLM_BUILDER_PAGE_MODELS = ["myapp.ArticlePage", "myapp.LandingPage"]   # None = all
```

## 10. Checklist: why isn't my block in the palette?

1. It's a **top-level** option of the page's `body` (or the field set in
   `PRBLM_BUILDER_FIELD_NAMES`) — blocks nested inside others aren't offered.
2. It has a **`template`**.
3. It isn't hidden: no `builder = False`, not in `PRBLM_BUILDER_EXCLUDE_BLOCKS`, its template
   doesn't start with a `PRBLM_BUILDER_EXCLUDE_TEMPLATE_PREFIXES` entry.
4. You ran `makemigrations` / `migrate` after changing the StreamField, and restarted the
   server.

If a block appears but its preview is empty or broken, the Block library lists it under
**"Couldn't preview"** with the reason.
