# Feature guide

Everything prblm-builder does, one feature at a time. New here? Do the
[Quick start](../README.md#quick-start) first — it gets the Layout tab working in a few
minutes; then come back for what you need.

1. [Using the Layout tab](#1-using-the-layout-tab)
2. [Which blocks show up](#2-which-blocks-show-up) — groups, hiding blocks
3. [The Block library](#3-the-block-library)
4. [Demo content](#4-demo-content) — `preview_value`, descriptions, where demo content comes from
5. [Section settings (⚙)](#5-section-settings-)
6. [Previews that match your site](#6-previews-that-match-your-site) — CSS, JS, preview template, several sites
7. [Built-in blocks (optional)](#7-built-in-blocks-optional) — 21 sections, Builder page, Theme, Headers & Footers
8. [A complete setup for an existing site](#8-a-complete-setup-for-an-existing-site)
9. [How it works](#9-how-it-works)
10. [What the plugin adds to your admin](#10-what-the-plugin-adds-to-your-admin)
11. [Uninstalling](#11-uninstalling)

Every setting: [SETTINGS.md](SETTINGS.md). Problems: [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
Copy-paste code for each feature: [EXAMPLES.md](EXAMPLES.md).

## 1. Using the Layout tab

Open any page in the editor: the **Layout** tab opens first. The left sidebar lists the
sections you can add; the right side is the page, rendered at desktop width and scaled to
fit.

### Arrange sections

- **Add:** drag a section from the sidebar onto the page, or click it to add it at the end.
- **Move, duplicate, delete:** hover a section for its toolbar (drag handle, up / down,
  copy, duplicate, delete), or right-click it for the same actions plus **Paste above /
  below**.
- **Copy & paste:** **Copy** in the toolbar or Ctrl/⌘+C on a selected section; paste with
  the right-click menu or Ctrl/⌘+V (below the selected one) — within the same page.
- **Undo / redo:** Ctrl/⌘+Z and Ctrl/⌘+Shift+Z.
- **Save:** with Wagtail's own **Save draft / Publish** — the arrangement saves with the
  page, nothing extra.

### Edit what a section says

- Words and images are edited in the normal **Content** tab.
- A new section starts with demo content (see [Demo content](#4-demo-content)). Until you
  change it, the canvas marks it **"Not edited yet"**, so placeholder text isn't published
  by accident. It's filled once, when you add it — sections already on a page are never
  refilled.
- Generated demo text is neutral and says what goes where ("Section heading", "Button
  label"), so it's easy to spot. The Block library and sidebar thumbnails shorten long
  text; the canvas shows the full text, exactly as it will be saved.
- **Layout and Content stay in sync.** On a saved page, after you add, remove or move
  sections, opening the Content tab waits for Wagtail's auto-save ("Saving your layout
  changes…") and reloads the editor on the Content tab with the new sections. Content-tab
  edits show on the canvas when you switch back. ⚙ settings update the Content tab at once,
  and the other way round.
- **A new page** (not saved yet) works too. Sections you add appear in the Content tab
  **after the first save** — a banner offers **Save draft now**; without a title it fills in
  "Untitled page 23" (Publish asks first while the page still has that title). With
  Wagtail's auto-save off (`WAGTAIL_AUTOSAVE_INTERVAL = 0`) every page works this way. If a
  save fails (e.g. a required field is empty), your arrangement is kept.

### Section settings (⚙)

Sections with settings (background, anchor ID…) have a ⚙ button in their toolbar: a small
panel, checked as you type, the canvas updates at once. Developers choose which fields
appear — see [Section settings](#5-section-settings-).

### The sidebar

- **Sections | Page** tabs; it always opens on **Sections**.
- **Search** looks through names and descriptions of every block.
- **All · Built-in · Your site's** pills show one kind of block at a time.
- **Most used first:** blocks are ordered by how many published pages use them (ties
  A–Z, unused last), groups by the total use of their blocks — on a multi-site project,
  that site's pages. `PRBLM_BUILDER_BLOCK_ORDER = "alpha"` keeps A–Z.
- **Fold** a group (or a whole kind) with the arrow next to it; your browser remembers it.
- **Page tab:** on **Builder pages** it chooses the header and footer. On your own page
  types it says where the header and footer on the canvas really come from, so nobody
  edits the wrong thing: **built into this page type** (its own code decides — change it in
  the page's content), **your site's shared header/footer** (the file name is shown for
  developers), a header/footer from **Page builder → Headers / Footers** (with a link), or
  **none**.

### On the canvas

- **Spacing:** select a section to see its margins as striped bands ("Space · 112px").
  Where two sections meet, the larger space is used, like on the live page.
- **Overlaps** look like the live page: a transparent header lies over the first section,
  and sections pulled over a neighbour by negative margins overlap it — see
  [Overlapping headers and sections](#overlapping-headers-and-sections).
- **Previews don't navigate:** links do nothing when clicked; script buttons (menus,
  accordions) still work.
- **Wider preview** (bottom right) hides the sidebar; drag the divider to resize it.
- **Wagtail's preview panel** follows the Layout tab as you work — a new section appears
  where you dropped it, so on a long page scroll the preview to see it.

### Two-column forms

The built-in blocks' forms (Content tab, Headers, Footers, Theme) show short fields two per
row and long ones full width. For your own blocks too: `PRBLM_BUILDER_SITE_BLOCK_COLUMNS = True`.

## 2. Which blocks show up

The Layout palette and the Block library list the **top-level blocks of your page
`body` fields** — the sections an editor can actually place. Blocks used only *inside*
other blocks (links, buttons, cards…) or only in non-page StreamFields never appear.
A block also needs its own `template` to be shown (it's what the preview renders).

### Groups

The headings in the section list (*Page openers*, *Content*…) come from each block's own
`group` — a standard Wagtail block option that also groups Wagtail's own block menu.
Blocks without one are listed under **Other**:

```python
class HeroSectionHome(blocks.StructBlock):
    ...
    class Meta:
        template = "home/blocks/hero_section_home.html"
        group = "Heroes"

# or on an inline block / when listing it:
("intro", blocks.RichTextBlock(group="Text", template="blocks/intro.html"))
```

The built-in blocks come with groups; give your own blocks one to group them the same way.

### Hiding a block

To hide a block that *is* a top-level option but isn't a real section, use **one** of
these three ways. Take this page model as the example:

```python
# core/blocks.py
class LinkBlock(blocks.StructBlock):
    ...

# core/models.py
class StandardPage(Page):
    body = StreamField([
        ("hero", HeroBlock()),
        ("link", LinkBlock()),     # ← "link" is the block's NAME in the StreamField
    ])
```

**A. On the block itself (recommended).** It travels with the block, whatever it's called
or wherever it's used:

```python
class LinkBlock(blocks.StructBlock):
    ...
    class Meta:
        template = "components/link.html"
        builder = False

# or on an inline block
("note", blocks.CharBlock(template="blocks/note.html", builder=False))
```

**B. In settings, by name.** Use the name from the StreamField: the first item of each
`("name", Block())` pair.

```python
PRBLM_BUILDER_EXCLUDE_BLOCKS = ["link"]
```

**C. In settings, by class.** Use the full import path: the module the class is defined
in, plus the class name. This also hides subclasses and catches the block under any name.

```python
PRBLM_BUILDER_EXCLUDE_BLOCKS = ["core.blocks.LinkBlock"]           # class in core/blocks.py
PRBLM_BUILDER_EXCLUDE_BLOCKS = ["core.blocks.links.LinkBlock"]     # class in core/blocks/links.py
```

| ✅ Works | ❌ Doesn't work | Why |
|---|---|---|
| `["link"]` | `["LinkBlock"]` | No dot → read as a StreamField *name*; no block is named `LinkBlock` |
| `["core.blocks.LinkBlock"]` | `["blocks.LinkBlock"]` | The path must be importable from your project (`from core.blocks import LinkBlock`) |
| `["link"]` | `"link"` | Must be a list; a plain string is read letter by letter |
| `["link"]` | `["Link"]` | Names are case-sensitive |

An entry that doesn't match anything is silently ignored (so a typo never breaks the
admin) — if a block still shows up, check the entry against the table above.

Blocks that error or show nothing with demo content are listed in a collapsed
**"Couldn't preview"** section at the bottom of the Block library, with the reason. They
stay available in the Layout palette — hide them with one of the options above if they
aren't sections.

## 3. The Block library

**Page builder → Block library** (also linked from the editor header) shows every block
with a live preview, grouped into *Built-in blocks* and *Your site's blocks*. Address:
`/admin/page-builder/demo/` (with your own admin prefix).

- **Check your setup here first:** blocks that can't be previewed are listed at the bottom
  with the reason (e.g. a required field the demo content can't fill).
- **Filter** All / Used on pages / Not used yet; each card says (top right) which
  published pages use the block — handy for spotting blocks nobody uses.
- **Search, kind pills, folding and order** work like the Layout sidebar.
- **Several Wagtail Sites:** the **Preview as** tabs at the top show the previews in that
  site's styles and count only that site's pages ("All sites" counts everywhere; a dropdown
  above 5 sites). Hidden with one Site.
- `PRBLM_BUILDER_LIBRARY_SCOPE = "all"` also lists page types that don't have the Layout
  tab; `PRBLM_BUILDER_DEMO = False` turns the library off.

The plugin's other menu items — **Theme**, **Headers**, **Footers** — come with the
[built-in blocks](#7-built-in-blocks-optional).

## 4. Demo content

A new section, the sidebar thumbnails and the Block library all show demo content, chosen
**field by field**. You can steer it with Wagtail's own block options.

### Block previews and descriptions

If your blocks use Wagtail's own block-preview options (Wagtail 6.4+), the plugin uses
them too:

```python
("promo", PromoBlock(
    preview_value={"title": "Spring sale", "text": "20% off everything"},
    description="A coloured band with a title and short text.",
))
```

- **`preview_value`** is the first choice for the Block library, the sidebar thumbnails
  and the starting content of a newly added section. It may leave fields out — they're
  filled from the rest of the chain below. **Leave images out**: image IDs differ between
  databases, so a portable `preview_value` can't name one; the plugin picks a fitting image.
- **`description`** shows under the block's name in the Block library and as a tooltip in
  the Layout sidebar (and is searchable). The built-in blocks have descriptions.

### Where demo content comes from

Every field of a new section (and of the previews) is filled by the first of these that
has something:

1. **The block's `preview_value`** — what the developer chose; it may be partial.
2. **Real content of the same block** — the fullest use of the same block class on a
   **published** page (the one with the most filled fields, then images, then length) (whatever it's called on that page type). Only sections someone
   actually edited, never the plugin's own untouched demo sections, and only content that
   passes the block's validation. Fields that section left empty fall through.
3. **The field's own `default`** (e.g. a `ChoiceBlock`'s default).
4. **Generated content**, neutral and obviously placeholder:
   - text from the field's label or help text, sized to the field: "Section heading" for
     a heading, a sentence for a `TextBlock`, a short paragraph for rich text (two for
     body-like fields), within `max_length`; list items numbered ("Feature 1, 2, 3");
   - images that fit the field (by name / label / help text: `background`, `hero`,
     `banner` → a wide photo; `logo`, `icon`, `avatar` → square, SVG or transparent),
     taking turns in lists, else a labelled placeholder of the right shape;
   - links: one consistent link — the type and only its field — to a real page, else `/`.
     Works for any link block whose dropdown names its fields (the built-in one,
     wagtail-link-block…);
   - lists: 3 items, or `min_num` if more, never above `max_num`;
   - documents: optional ones stay empty; snippet and page choosers get an existing one;
   - fields with a required pattern (`RegexBlock`, validators): the first of `/`, `/page/`,
     `https://example.com/`, `example`, `123`, `#section`… that passes.

Finally the whole value is checked with the block's own `clean()`; a field that fails falls
back a step, so a new section can always be saved.

## 5. Section settings (⚙)

Some fields are about *how* a section looks rather than *what it says* — background,
anchor ID, a "compact" switch. List them in the block's `Meta.builder_settings` and they
get a **⚙ button** on the section in the Layout tab, with a small settings panel (choices,
on/off switches and short text; background choices of light / muted / dark / brand show
as colour swatches). The built-in blocks already do this for their background and anchor ID.

```python
from prblm_builder.mixins import BuilderSettingsMixin   # optional, see below

class PromoBlock(BuilderSettingsMixin, blocks.StructBlock):
    title = blocks.CharBlock()
    text = blocks.TextBlock()
    background = blocks.ChoiceBlock(choices=[("light", "Light"), ("dark", "Dark")], default="light")
    compact = blocks.BooleanBlock(required=False)

    class Meta:
        template = "blocks/promo.html"
        builder_settings = ["background", "compact"]   # ← shown in the ⚙ panel
```

- `builder_settings` alone gives you the ⚙ panel. Adding **`BuilderSettingsMixin`** also
  moves those fields into Wagtail's collapsed **settings** area of the block in the Content
  tab (Wagtail 8.1 `form_layout`), so editors aren't distracted by them there. On older
  Wagtail the mixin does nothing: the fields show in both places, and either one works.
- Changes save with the page. Only fields you changed in the ⚙ panel are sent; if the
  same field was also changed in the Content tab, the Layout tab's change wins.
- Each value is checked by its own field as you type (e.g. an invalid anchor ID, a number
  above its `max_value`) and the message shows under it; only valid values are applied.
  Number fields (`IntegerBlock`, `DecimalBlock`, `FloatBlock`) get a number box with their
  limits. A dropdown with a `default` has no empty choice.
- Choosers, rich text and nested blocks aren't shown in the ⚙ panel — edit those in the
  Content tab.

## 6. Previews that match your site

Each section on the canvas (and in the Block library and thumbnails) renders in its own
small page. These options make that page behave like your real ones. For a step-by-step
walkthrough (preview template, several sites, Alpine, animations, analytics), see
[PREVIEWS.md](PREVIEWS.md).

### Scripts and stylesheets

`PRBLM_BUILDER_PREVIEW_CSS` / `_JS` load in **list order** — CSS in `<head>`, scripts at the
end of `<body>`. Put libraries first and your own files after them (a CSS framework listed
*after* your CSS overrides it; Alpine plugins go before Alpine itself). Entries are static
paths, full URLs, or dicts for options:

```python
PRBLM_BUILDER_PREVIEW_CSS = [
    "css/main.css",
    {"href": "https://cdn.example.com/lib.css", "integrity": "sha384-…", "crossorigin": "anonymous"},
    {"href": "css/print.css", "media": "print"},
    {"inline": ".cookie-banner{display:none}"},            # preview-only tweaks
]
PRBLM_BUILDER_PREVIEW_JS = [
    {"inline": "window.siteConfig = {lang: 'en'};"},        # runs before the files below
    {"src": "js/alpine-collapse.min.js", "defer": True},
    {"src": "js/alpine.min.js", "defer": True},
    {"src": "js/app.js", "type": "module"},
    {"importmap": {"imports": {"lib": "/static/js/lib.js"}}},
]
```

Script options: `defer`, `async`, `nomodule`, `type`, `integrity`, `crossorigin`,
`referrerpolicy`. Stylesheet options: `media`, `integrity`, `crossorigin`, `rel` (+ `as`
for preloads).

### Your own preview template

Your `base.html` may provide more than files: `<body>` attributes (`x-data` for Alpine,
`data-theme`), inline scripts, wrapper elements your CSS relies on. To give previews all of
it, write a small template that extends your base template and drops the section in — a
developer-only setting; editors see nothing different:

```django
{# templates/prblm_preview.html #}
{% extends "base.html" %}
{% block header %}{% endblock %}
{% block footer %}{% endblock %}
{% block content %}{{ prblm_section }}{% endblock %}
```

```python
PRBLM_BUILDER_PREVIEW_TEMPLATE = "prblm_preview.html"
```

The template gets `page` (the page being edited, when there is one), `request` and
`prblm_preview` (always `True`). The canvas measures only the section, so padding or
wrappers around it in your template don't add space. With a preview template, `PRBLM_BUILDER_PREVIEW_CSS` / `_JS` / `_BODY_CLASS` aren't
needed for previews (Builder pages still use them for your header/footer and blocks).

### Several sites

A project with several Wagtail sites (each with its own CSS build, fonts, header) sets what
differs per site, by the Site's hostname; anything not set comes from the settings above:

```python
PRBLM_BUILDER_PREVIEW_SITES = {
    "shop.example.com": {
        "css": ["shop/css/main.css"],
        "js": ["shop/js/app.js"],
        "body_class": "font-shop",
        "header_template": "shop/header.html",
        "footer_template": "shop/footer.html",
        "template": "shop/prblm_preview.html",
    },
}
```

A profile can also set `body_attrs` / `html_attrs` (see below).

**Matching.** A key matches a Site by, in this order: `"hostname:port"`, `"hostname"`, the
Site's **name** (Settings → Sites), then a **wildcard** on the hostname (`"landing.*"`,
`"*.example.com"`). Site names and wildcards work on every environment without listing
each hostname:

```python
PRBLM_BUILDER_PREVIEW_SITES = {
    "Main": {...},                 # the Site named "Main", on any server
    "landing.*": {...},            # landing.localhost, landing.example.com, …
}
```

The canvas uses the edited page's site (for a new page, its parent's). The Block library
gets a **Site** switcher; a site no key matches is marked "uses the default preview
settings" there, and the server log warns once.

### `<html>` and `<body>` attributes

Sections that rely on state on `<body>` (Alpine's `x-data`, `data-theme`, `dir`) need it in
previews too. A preview template keeps your real `<body>`; without one, set:

```python
PRBLM_BUILDER_PREVIEW_BODY_ATTRS = {"x-data": "{ showModal: false }"}
PRBLM_BUILDER_PREVIEW_HTML_ATTRS = {"data-theme": "light"}
# or "body_attrs" / "html_attrs" in a PRBLM_BUILDER_PREVIEW_SITES profile
```

A `class` in `body_attrs` joins `PRBLM_BUILDER_PREVIEW_BODY_CLASS`. They also go on published
Builder pages that show your header / footer or contain your own blocks. With a preview
template they're ignored.

### Animations and scroll effects

Previews are still pictures, and scroll-triggered effects often never fire in them (the
frame is scaled, not scrolled). Every preview has `class="prblm-canvas"` on `<html>` (also
with a preview template), and `PRBLM_BUILDER_REDUCE_MOTION = True` (default) makes CSS
animations and transitions finish instantly. Elements hidden until a script adds a class
(scroll-reveal, AOS, Alpine `x-intersect`) need one rule from you:

```css
.prblm-canvas .reveal, .prblm-canvas [data-aos] { opacity: 1 !important; transform: none !important; }
```

### Overlapping headers and sections

Two common designs draw one part of the page over another:

- a **transparent header** (`position: fixed` or `absolute`, no background) over a dark
  hero, often turning solid only after scrolling;
- a section **pulled over its neighbour** by a negative margin — a white box floating over
  the end of the hero, or a card hanging into the next section.

The canvas shows both like the live page at the top of the screen
(`PRBLM_BUILDER_CANVAS_OVERLAP = True`, the default): a header with no background of its
own lies over the first section, and a section reaching over a neighbour covers it, with
the neighbour showing through around it. Parts drawn outside a section are never cut off.

If the canvas guesses your header wrong — e.g. it should show solid — make it solid in
previews with one rule: `.prblm-canvas .site-header{background:#123}`. To stack everything
instead (header in its own strip, overlapping sections one under the other), set
`PRBLM_BUILDER_CANVAS_OVERLAP = False`, or `"canvas_overlap": False` for one site.

### Gaps between sections

On a page, the bottom margin of one section and the top margin of the next merge (the gap
is the larger of the two). The canvas does the same — also between the header and the first
section — unless your preview template puts sections in a flex or grid container, where
margins don't merge on the live page either.

### `vh` heights and fixed headers

- Sections sized in `vh` render against a screen `PRBLM_BUILDER_CANVAS_HEIGHT` tall (900px
  by default), so `min-h-[70vh]` is 630px on the canvas, as on a typical screen.
- A site header with `position: fixed` is measured at its real height above the canvas.
  On a published **Builder page** showing your site's own header, the sections start below
  it: the page measures a fixed header and pads the sections by its height. Set
  `--prblm-header-offset` (e.g. `:root{--prblm-header-offset:128px}`) to choose it yourself.
- A header or footer that renders nothing takes no space on the canvas.
- A transparent fixed header lies over the first section, as on the page — see
  [Overlapping headers and sections](#overlapping-headers-and-sections).

### Choosing the header/footer per page type in code

The `prblm_builder_chrome_for_page` hook decides which header/footer HTML the canvas shows
for a page (the built-in Builder page uses it). Return a string — `""` means "no header" —
or `None` to leave it to the settings:

```python
# yourapp/wagtail_hooks.py
from django.template.loader import render_to_string
from wagtail import hooks

@hooks.register("prblm_builder_chrome_for_page")
def landing_page_header(kind, request, page, model):
    if (model or type(page)).__name__ != "LandingPage":
        return None                                   # not mine
    if kind == "header":
        return render_to_string("landing/header.html", {"page": page}, request=request)
    return ""                                         # no footer on landing pages
```

## 7. Built-in blocks (optional)

A separate app inside the package adds 21 ready-made sections. Everything they need —
CSS, a few lines of JavaScript, icons, image placeholders — ships with the plugin, so your
site needs no extra CSS, JS, Node or Tailwind. Every block starts **pre-filled with
explanatory example content** ("Your main headline — say what you do in a few words"), so
it's clear what goes where.

### Enable

```python
INSTALLED_APPS = [
    "prblm_builder",
    "prblm_builder.blocks",          # the built-in blocks
    "wagtail.contrib.settings",      # needed for the Theme
    # …
]
```

```bash
python manage.py migrate
```

Then use the blocks in one (or both) of these ways.

**1. The ready-made "Builder page" (no code).** In the admin, *Add child page* → **Builder
page**. It has all 21 blocks and a Layout tab, and renders as a complete page: a header,
your sections, a footer (each page chooses which — see
[Headers & footers](#headers--footers)). To render it inside your own site layout instead,
create a template at `prblm_builder/blocks/builder_page.html` in your templates folder.
To hide the page type from *Add page*: `PRBLM_BUILDER_PAGE_TYPE = False`.

> **Builder page only offered at the very top (next to Home)?** Your home page type
> limits which pages can go under it (a `subpage_types` list in its code). Allow Builder
> pages there with a setting — no code change:
>
> ```python
> PRBLM_BUILDER_PAGE_PARENTS = ["home.HomePage"]   # "app_label.ModelName", one or more
> ```

**Your own blocks on the Builder page.** List them in a setting — they appear in the
Builder page's palette under *Your site's blocks*, and no migration is needed:

```python
PRBLM_BUILDER_PAGE_EXTRA_BLOCKS = [
    ("quote_card", "core.blocks.QuoteCardBlock"),   # ("name", "dotted path to the block")
]
# or a function that returns [(name, block), …]:
# PRBLM_BUILDER_PAGE_EXTRA_BLOCKS = "core.blocks.builder_page_blocks"
```

Names must not clash with the built-in ones (`hero`, `faq`, …) — you'll get a clear error
at startup if they do, or if a path can't be imported. The name can differ from the one
your other page types use (`hero_home` here, `hero_section_home` on your HomePage): the
plugin recognises the same block by its **class**, so it uses the same real content for
its demo and thumbnail, and the Block library lists it once.

To offer **all** your blocks, point the setting at a function:

```python
# settings
PRBLM_BUILDER_PAGE_EXTRA_BLOCKS = "home.blocks.builder_page_blocks"

# home/blocks.py (after your block classes)
def builder_page_blocks():
    return [
        ("hero_home", HeroSectionHome()),
        ("level_icons", LevelIconsSection()),
        # …
    ]
```

A Builder page that contains your own blocks (or shows your site's own header/footer)
loads your `PRBLM_BUILDER_PREVIEW_CSS` / `_JS`, so they look as on the rest of your site.

**2. In your own page models**, next to your own blocks:

```python
from prblm_builder.blocks import builder_blocks

class LandingPage(Page):
    body = StreamField(
        builder_blocks() + [("my_block", MyBlock())],
        blank=True,
    )
```

Already have a list of blocks? Add the built-in ones to it:

```python
all_blocks = [
    ("hero_section_home", HeroSectionHome()),
    ("description_section", DescriptionSection()),
] + builder_blocks(only=["faq", "pricing"])          # or builder_blocks() for all 21

class HomePage(Page):
    body = StreamField(all_blocks, blank=True)
```

then run `python manage.py makemigrations` and `migrate` (Wagtail records the allowed
blocks in your app's migrations — that's why this step can't be automatic).
`builder_blocks(exclude=["hero"])` leaves blocks out (e.g. if you already have your own
`hero`); `builder_blocks(only=["faq", "pricing"])` picks just some. An unknown name
raises an error listing the available ones. It needs `"prblm_builder.blocks"` in
`INSTALLED_APPS`.

**Style them on your live pages:** your own page templates don't load the built-in blocks'
CSS by themselves. Add it once to your `base.html`, after your own CSS:

```django
{% load static prblm_blocks %}
<link rel="stylesheet" href="{% static 'css/main.css' %}">
{% prblm_assets %}
```

(The canvas and the Builder page do this automatically.)

### The blocks

Every section has a **background** choice (Light, Muted, Dark, Brand colour — all from
the Theme) and an optional **anchor ID**, so menus and buttons can link to `#pricing`
etc.

**Links** (buttons, menus, cards…) have a **Label**, a **Link to** choice and only the field
that choice needs: **Page on this site**, **Web address** (`https://…` or `/path/`),
**Section on this page** (an anchor ID like `pricing`), **Document**, **Email address** or
**Phone number**. Clear the label to hide a link.

| Block | Name | What it's for |
|---|---|---|
| Header | `header` | Logo or site name, menu with one-level dropdowns, button; mobile menu; optional sticky |
| Footer | `footer` | Logo, short description, link columns, social links, © year added automatically |
| Hero | `hero` | Big page opener: headline, text, two buttons, image beside or behind the text |
| Page banner | `page_banner` | Title strip for inner pages, with optional breadcrumbs |
| Text | `text` | Formatted long text in a readable column |
| Text + image | `text_image` | Text beside an image, image on the left or right |
| Features | `features` | Grid of benefits with icons (2/3/4 columns) |
| Cards | `cards` | Image + title + text + link cards for services, projects or articles |
| Steps | `steps` | Numbered process ("1. … 2. … 3. …") |
| Quote | `quote` | One large highlighted quote |
| Testimonials | `testimonials` | Customer quotes with name, role and optional photo |
| Logo strip | `logo_strip` | Client/partner logos (or names), optional greyscale |
| Stats | `stats` | Big numbers with labels |
| Call to action | `call_to_action` | Coloured band with a headline and buttons |
| FAQ | `faq` | Questions that expand on click (works without JavaScript) |
| Pricing | `pricing` | Plan columns with features and a highlighted plan |
| Gallery | `gallery` | Image grid with captions |
| Video | `video` | YouTube or Vimeo embed (privacy-friendly; built from the link, no API call) |
| Team | `team` | People with photo, name, role, short bio |
| Contact info | `contact_info` | Address, email, phone, opening hours, map link |
| Divider | `divider` | A line or empty space |

Image fields left empty show a neutral placeholder labelled with its purpose and size
("Hero image · 1200×900") — nothing is added to your image library. Icons come from a
built-in set of ~50 line icons, picked from a dropdown.

### Reusing the link block

Your own blocks can use the built-in link block (Label → *Link to* → the one field that
type needs): `from prblm_builder.blocks import LinkBlock`, then `link = LinkBlock()` in
your StructBlock and `{{ value.link.href }}` in its template. Full example:
[docs/EXAMPLES.md — Reuse the built-in link block](https://github.com/prblmcodes/prblm-builder/blob/main/docs/EXAMPLES.md#5-reuse-the-built-in-link-block).

### Styles stay separate

The built-in blocks' CSS only styles the blocks, and the blocks are shielded from your
site's global CSS (Tailwind's reset, `p`/`ul`/`a`/`header` rules…), so they look the same on
any site. Builder pages load your site's CSS/JS only when they show your site's header or
footer or contain your own blocks. Details:
[docs/EXAMPLES.md — Header and footer](https://github.com/prblmcodes/prblm-builder/blob/main/docs/EXAMPLES.md#8-header-and-footer-in-your-base-template).

### Theme

**Page builder → Theme** sets, per site: brand colour (and text on it), text colours,
the three background colours, fonts and corner roundness / content width. It restyles
every built-in block at once. Font fields are left empty by default, which means "use
my site's font"; enter a CSS font list (e.g. `Inter, sans-serif`) to override — the font
itself must already be loaded by your site.

The Theme only affects the built-in blocks, never your own blocks or the rest of your
site. Developers can also override the CSS variables (`--pbk-c-brand`, `--pbk-radius`, …)
in their own CSS, or override any block template by placing a file with the same path
(e.g. `prblm_builder/blocks/hero.html`) in their templates folder.

### Headers & footers

**Page builder → Headers** and **Page builder → Footers** are lists: create as many as
you like (e.g. "Main header", "Campaign header"), click one to edit it. A new one starts
pre-filled with example content. Tick **Use as site default** on the one most pages
should use — only one header and one footer can be the default.

Which one shows where:

| Where | Header / footer shown |
|---|---|
| **Builder page** | Its own choice, in the **Layout** tab → sidebar **Page** tab (one dropdown each): **Site default**, any header/footer by name, **My site's own** (your `PRBLM_BUILDER_HEADER_TEMPLATE` / `_FOOTER_TEMPLATE`, shown only when set), or **None**. The canvas shows your choice right away. |
| **Layout canvas of your other page types** | Your `PRBLM_BUILDER_HEADER/FOOTER_TEMPLATE` if set, otherwise the site default, otherwise nothing. |
| **Your own templates** (optional) | Wherever you add the tags below. |

```django
{% load prblm_blocks %}
{% prblm_header %}                    {# the site default (on a Builder page: its choice) #}
…
{% prblm_footer %}
{% prblm_header "Campaign header" %}  {# a specific one, by name #}
```

Each tag renders nothing if there's no matching header/footer, so they're safe to add.
Headers and footers are shared by all sites in a multi-site setup.

They're stored as Wagtail *snippets*, so Wagtail's own **Snippets** menu also appears and
lists them — editing them there is the same.

### Rules that keep your content safe

Block **names** (`hero`, `faq`, …), their **fields** and the block **class paths** are
stored in your pages and migrations. They won't be renamed in future versions — new
fields and blocks may be added.

## 8. A complete setup for an existing site

What a typical site with its own blocks, header/footer and CSS needs. Each step is
optional unless you use that feature.

```python
# settings (the file with INSTALLED_APPS)
INSTALLED_APPS = [
    "prblm_builder",
    "prblm_builder.blocks",          # 1. built-in blocks, Builder page, Theme, Headers/Footers
    "wagtail.contrib.settings",      #    … needed by the built-in blocks (Theme)
    # … your apps, wagtail apps …
]

PRBLM_BUILDER_PREVIEW_CSS = ["css/main.css"]          # 2. your compiled CSS (static path)
PRBLM_BUILDER_PREVIEW_JS = ["js/core.js"]             #    scripts your blocks/header need
# PRBLM_BUILDER_PREVIEW_BODY_CLASS = "…"              #    only if your <body> has classes

PRBLM_BUILDER_HEADER_TEMPLATE = "components/header.html"   # 3. your header/footer on the canvas
PRBLM_BUILDER_FOOTER_TEMPLATE = "components/footer.html"   #    (+ "My site's own" on Builder pages)

PRBLM_BUILDER_PAGE_PARENTS = ["home.HomePage"]        # 4. allow Builder pages under Home
PRBLM_BUILDER_PAGE_EXTRA_BLOCKS = [                   # 5. your blocks on the Builder page
    ("hero_home", "home.blocks.HeroSectionHome"),
]
# PRBLM_BUILDER_SITE_BLOCK_COLUMNS = True             # 6. two-column forms for your blocks too
# PRBLM_BUILDER_PREVIEW_TEMPLATE = "prblm_preview.html"  # 7. previews inside your base.html
# PRBLM_BUILDER_PREVIEW_SITES = {…}                   # 8. several sites: CSS/header per site
# PRBLM_BUILDER_PREVIEW_BODY_ATTRS = {"x-data": "…"}  # 9. Alpine state on <body> (no template)
```

Then:

1. `python manage.py migrate` (the plugin's small demo-content table, plus the Builder
   page, Theme, Headers and Footers tables).
2. **Built-in blocks in your own page types** (optional): add `builder_blocks()` to their
   StreamField, run `makemigrations` + `migrate`, and add `{% prblm_assets %}` to your
   `base.html` so they're styled on the live site — see
   [Built-in blocks → Enable](#enable), way 2.
3. Restart the server, open a page in the editor: the **Layout** tab opens first.
4. Open **Page builder → Block library** to check every block previews correctly. Blocks
   that can't be previewed are listed at the bottom with the reason.

Good to know:

- Paths in `PRBLM_BUILDER_PREVIEW_CSS` / `_JS` are what you'd write in `{% static '…' %}`.
  They're linked as `/static/…`, so they load in the canvas, Wagtail's preview panel and on
  Builder pages whatever host name your Wagtail **Site** record has.
- **Your blocks need a `template`** to appear in the Layout palette and Block library.
- **Demo content** for a new section is chosen field by field: the block's
  `preview_value` (it may leave fields out), real content of the same block on a published
  page, the field's default, then neutral placeholder text ("Section heading"). See
  [Where demo content comes from](#where-demo-content-comes-from).
- **Third-party blocks work too** (e.g. [wagtail-link-block](https://pypi.org/project/wagtail-link-block/)):
  demo content is checked against each block's own validation, so new sections always save.
- **Sections using `vh` heights** (`min-h-[70vh]`, `h-screen`) render as on a 900px-tall
  screen (`PRBLM_BUILDER_CANVAS_HEIGHT`). **A fixed site header** is measured on the canvas,
  and Builder pages leave room for it. **Alpine / inline scripts / `<body>` attributes** from
  your `base.html`: use a [preview template](#your-own-preview-template). Step-by-step
  guide: [PREVIEWS.md](PREVIEWS.md).

## 9. How it works

- **Edits the draft.** Like Wagtail's own editor, the Layout tab shows and builds on the
  page's latest draft (revision), not only what's published.
- **No block list.** It asks each page model's StreamField which blocks it allows
  (`PRBLM_BUILDER_FIELD_NAMES`, default `body`). Models, templates and static files are
  found the normal Django/Wagtail way, so no paths need configuring.
- **Auto-attach.** On startup it adds the Layout tab to each enabled page model's editor
  and wraps its form, so your models need no code changes.
- **Ride-along save.** The Layout tab writes the arrangement into hidden fields on the
  edit form; on Save/Publish the form rebuilds the StreamField in that order. Existing
  blocks keep their content; new ones get demo content; duplicates copy their source.
  Blocks added or deleted in the Content tab are respected.
- **Remembers its own demo content.** Each section it fills is recorded (a small table)
  with a fingerprint of its content: until someone changes it, it shows "Not edited yet"
  and it's never borrowed as "real content" for other demos.
- **Demo content, field by field** — see [Where demo content comes from](#where-demo-content-comes-from).
  Blocks are matched by class, so a block reused under another name shares its content.
  Long text is shortened in the Block library and sidebar thumbnails only — the canvas
  shows what will be saved.
- **Scaled previews.** Each section renders in its own iframe at desktop width
  (`PRBLM_BUILDER_CANVAS_WIDTH`) and a screen height of `PRBLM_BUILDER_CANVAS_HEIGHT`, and is
  scaled down to fit, so you see the desktop layout even in a narrow editor column.

## 10. What the plugin adds to your admin

- A **Layout** tab (first) in the editor of every enabled page type, and a **Block library**
  button in its header.
- A **Page builder** section in the admin sidebar (Block library; with the built-in
  blocks app also Theme, Headers, Footers).
- With the built-in blocks app: a **Snippets** menu (Headers and Footers are snippets), a
  **Builder page** type in *Add page*, and the **Theme** settings.
- A **Builder placeholders** image collection, only when demo content needs an image and no
  library image fits (`PRBLM_BUILDER_PLACEHOLDER_IMAGES = False` to never create it).
- If your blocks have a `group`, Wagtail's own "Add block" menu is grouped the same way
  (that's Wagtail using the same option).

## 11. Uninstalling

1. **Your own models using `builder_blocks()`** (built-in blocks in your page types): remove
   them from the StreamField, then `python manage.py makemigrations` and `migrate`. Content
   stored in those blocks is dropped from the field (keep a database backup if you want it).
   Old migrations of your app still import `prblm_builder.blocks…` — keep the package
   installed until you've squashed or edited those migrations, or Django can't load them.
2. **Builder pages**: delete them (or move their content to your own page types) first.
3. Remove the tables: `python manage.py migrate prblm_builder_blocks zero` and
   `python manage.py migrate prblm_builder zero`.
4. Remove `"prblm_builder"` / `"prblm_builder.blocks"` from `INSTALLED_APPS`, every
   `PRBLM_BUILDER_*` setting, and the template tags you added (`{% prblm_assets %}`,
   `{% prblm_header %}`, `{% prblm_footer %}`, `{% load prblm_blocks %}`).
5. `pip uninstall prblm-builder`. Your page content in your own blocks is untouched — the
   plugin only arranged it.
