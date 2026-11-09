# prblm-builder

A visual drag-and-drop **page builder** for Wagtail. It adds a **Layout** tab to the
page editor where you compose a page by dragging the site's own StreamField blocks onto
a canvas — reorder, duplicate and delete sections with live, desktop-scaled previews.
Arrange in the Layout tab; edit each block's words and images in the normal **Content**
tab; your arrangement saves with the page's own **Save draft / Publish** (nothing extra).

Works on any Wagtail site: it discovers your blocks by introspection — no block list to
maintain — and attaches itself automatically to every page type that has a buildable
StreamField.

Optionally, it also ships **21 ready-made section blocks** (header, hero, features,
pricing, FAQ, footer, …), a ready-made **Builder page** type, a **Theme** page and
reusable **Headers & Footers** — fully self-contained, nothing extra to install. See
[Built-in blocks](#built-in-blocks-optional).

**New here?** [docs/EXAMPLES.md](docs/EXAMPLES.md) has copy-paste page models and blocks
for every feature (each one is checked by the test suite).

- [Requirements](#requirements)
- [Install](#install)
- [Quick setup](#quick-setup)
- [Use](#use)
- [Built-in blocks (optional)](#built-in-blocks-optional)
- [Settings reference](#settings-reference)
- [Which blocks show up](#which-blocks-show-up)
  - [Hiding a block](#hiding-a-block)
- [Section settings (⚙)](#section-settings-)
- [Block previews and descriptions](#block-previews-and-descriptions)
- [Examples](docs/EXAMPLES.md)
- [How it works](#how-it-works)
- [Project structure](#project-structure)
- [Development](#development)
- [Upgrading](#upgrading)
- [Troubleshooting](#troubleshooting)

## Requirements

- Python 3.12+
- Django 6.1+
- Wagtail 8.1+ (below 9)

No front-end tooling is needed (no Node, no Tailwind). The builder ships its own CSS/JS;
previews simply load your site's compiled CSS.

## Install

Install from a GitHub release tag:

```bash
# public repo
pip install "prblm-builder @ git+https://github.com/prblmcodes/prblm-builder.git@v0.5.0"

# private repo (uses your GitHub SSH key)
pip install "prblm-builder @ git+ssh://git@github.com/prblmcodes/prblm-builder.git@v0.5.0"
```

Or put the same `prblm-builder @ git+…@v0.5.0` line in `requirements.txt`. You can also
download the wheel attached to a GitHub release and
`pip install prblm_builder-0.5.0-py3-none-any.whl`.

To upgrade later, change the tag (e.g. `@v0.5.0` → `@v0.6.0`) and reinstall. See
[CHANGELOG.md](CHANGELOG.md) for what changed in each version.

## Quick setup

1. Add the app to your settings (the file with `INSTALLED_APPS`, e.g.
   `<project>/settings/base.py`):

   ```python
   INSTALLED_APPS = [
       "prblm_builder",
       # … your apps, wagtail apps, …
   ]
   ```

2. That's it for the basics — no migrations, no URL changes (admin URLs are registered
   through Wagtail hooks). Every page model with a StreamField named `body` now has a
   **Layout** tab. Want ready-made sections too? Add the optional
   [built-in blocks](#built-in-blocks-optional).

3. Recommended: make previews look like your site by pointing them at your front-end CSS,
   in the same settings file. Paths are relative to a `static/` or `templates/` folder,
   exactly as you'd write them in `{% static '…' %}` or `{% include '…' %}`:

   ```python
   # file on disk: core/static/css/main.css  →  "css/main.css"
   PRBLM_BUILDER_PREVIEW_CSS = ["css/main.css"]

   # file on disk: core/templates/components/footer.html  →  "components/footer.html"
   PRBLM_BUILDER_FOOTER_TEMPLATE = "components/footer.html"
   ```

4. In production, run `python manage.py collectstatic` as usual so the builder's
   CSS/JS are served.

## Use

- **Any page:** open it in the editor — the **Layout** tab opens first. Drag sections from the left,
  reorder/duplicate/delete, and **Save draft / Publish** as usual. Undo/redo with
  Ctrl/⌘+Z and Ctrl/⌘+Shift+Z.
- **Edit content:** each section's words and images are edited in the normal **Content**
  tab. New sections start with demo content; until you change it, the canvas marks the
  section **"Not edited yet"** so placeholder text doesn't get published by accident.
- **Layout and Content stay in sync:** on a saved page, after you add, remove or move
  sections, opening the **Content** tab waits for Wagtail's auto-save ("Saving your layout
  changes…") and reloads the editor on the Content tab with the new sections in it. Edits
  made in the Content tab show on the canvas when you switch back to Layout. ⚙ settings
  update the Content tab at once, and the other way round.
- **New page (not saved yet):** the Layout tab works before the first save. Sections you
  add show in the Content tab **after you save** — a banner says so, with a **Save draft
  now** button; without a title it fills in **"Untitled page 23"** (rename it later). With
  Wagtail's auto-save turned off (`WAGTAIL_AUTOSAVE_INTERVAL = 0`) every page works this
  way. If a save fails (e.g. a required field is empty), your arrangement is kept and the
  editor opens the tab with the error.
- **Two-column forms:** the built-in blocks' forms (Content tab, Headers, Footers, Theme)
  show short fields two per row — text, dropdowns, choosers — and long text, rich text and
  lists full width. Turn it on for your own blocks with
  `PRBLM_BUILDER_SITE_BLOCK_COLUMNS = True`.
- **Sidebar:** the Layout sidebar always opens on **Sections**; **Page** shows only when
  you click it.
- **Section settings (⚙):** sections with settings (e.g. background, anchor ID) have a ⚙
  button in their toolbar. It opens a small panel; the canvas updates as you change
  things, and the change saves with the page. See [Section settings](#section-settings-).
- **Copy & paste:** copy a section with its toolbar's **Copy** button (or select it and
  press Ctrl/⌘+C). To paste, **right-click** a section → **Paste above** / **Paste below**,
  or press Ctrl/⌘+V to paste below the selected one — within the same page. The
  right-click menu also has Duplicate, Settings, Move and Delete; the Duplicate button
  copies a section right below in one click.
- **Page tab:** the Layout sidebar has **Sections | Page** tabs. On **Builder pages** the
  Page tab chooses the header and footer. On your own page types it explains where they
  come from — your site's template for that page type — since they're not chosen per page
  there.
- **Fold groups:** in the Layout sidebar and the Block library, click the arrow next to a
  group (or *Built-in blocks* / *Your site's blocks*) to fold it. In the Block library,
  folding in the sidebar also hides those previews. Your browser remembers what's folded.
- **Page builder menu:** the plugin adds a **Page builder** section to the admin sidebar:
  - **Block library** — every block with a live preview, grouped into *Built-in blocks*
    and *Your site's blocks*. Address: `/admin/page-builder/demo/` (use your own admin
    prefix if it isn't `admin/`). Also linked from the editor header.
  - **Theme**, **Headers** and **Footers** — only when the built-in blocks app is installed.

## Built-in blocks (optional)

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
at startup if they do, or if a path can't be imported.

**2. In your own page models**, next to your own blocks:

```python
from prblm_builder.blocks import builder_blocks

class LandingPage(Page):
    body = StreamField(
        builder_blocks() + [("my_block", MyBlock())],
        blank=True,
    )
```

then run `python manage.py makemigrations` and `migrate` (Wagtail records the allowed
blocks in your app's migrations — that's why this step can't be automatic).
`builder_blocks(exclude=["hero"])` leaves blocks out (e.g. if you already have your own
`hero`); `builder_blocks(only=["faq", "pricing"])` picks just some. An unknown name
raises an error listing the available ones.

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
[docs/EXAMPLES.md — Reuse the built-in link block](docs/EXAMPLES.md#5-reuse-the-built-in-link-block).

### Styles stay separate

The built-in blocks' CSS only styles the blocks, and the blocks are shielded from your
site's global CSS (Tailwind's reset, `p`/`ul`/`a`/`header` rules…), so they look the same on
any site. Builder pages load your site's CSS/JS only when they show your site's header or
footer or contain your own blocks. Details:
[docs/EXAMPLES.md — Header and footer](docs/EXAMPLES.md#8-header-and-footer-in-your-base-template).

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

## Settings reference

Every setting is optional and goes in your Django settings file (the one with
`INSTALLED_APPS`). With nothing set, the plugin enables any page model with a `body`
StreamField and renders previews unstyled. After changing a setting, restart the server
(`runserver` does this automatically) and hard-refresh the admin page.

### Previews — make the canvas look like your site

| Setting | Default | What it does |
|---|---|---|
| `PRBLM_BUILDER_PREVIEW_CSS` | `[]` | CSS files loaded into every preview. Static paths (`"css/main.css"`) or full URLs. |
| `PRBLM_BUILDER_PREVIEW_JS` | `[]` | JS files loaded into every preview (e.g. sliders, accordions). |
| `PRBLM_BUILDER_PREVIEW_BODY_CLASS` | `""` | Classes for the preview `<body>`. Copy them from the `<body class="…">` in your `base.html` if your CSS relies on them (fonts, colours). Leave empty if your `<body>` has no classes. |
| `PRBLM_BUILDER_HEADER_TEMPLATE` | `""` | Template of your site header, shown above the canvas. Gets `page` / `self` (the page being edited; not set on a brand-new unsaved page). |
| `PRBLM_BUILDER_FOOTER_TEMPLATE` | `""` | Same, for the footer, shown below the canvas. |
| `PRBLM_BUILDER_CANVAS_WIDTH` | `1280` | Desktop width (px) sections render at before being scaled to fit the editor. Set it to your design width (e.g. `1440`). |

### Which pages get the Layout tab

| Setting | Default | What it does |
|---|---|---|
| `PRBLM_BUILDER_FIELD_NAMES` | `["body"]` | StreamField name(s) to build on, in priority order — e.g. `["body", "content"]`. A model gets the tab if it has one of these. |
| `PRBLM_BUILDER_PAGE_MODELS` | `None` | `None` = every page model with a matching field. Or limit it: `["home.StandardPage", "blog.BlogPage"]`. |

### Block visibility

| Setting | Default | What it does |
|---|---|---|
| `PRBLM_BUILDER_EXCLUDE_BLOCKS` | `[]` | Hide blocks from the palette + Block library. Each entry is either the block's **name in the StreamField** (`"link"`) or the **full import path of its class** (`"core.blocks.LinkBlock"`, also hides subclasses). A bare class name like `"LinkBlock"` does **not** work — see [Hiding a block](#hiding-a-block). |
| `PRBLM_BUILDER_EXCLUDE_TEMPLATE_PREFIXES` | `()` | Hide blocks whose template path starts with one of these (e.g. `("emails/",)` for email-only blocks). |
| `PRBLM_BUILDER_LIBRARY_SCOPE` | `"builder"` | What the Block library lists: `"builder"` = the same blocks as the Layout palette; `"all"` = top-level blocks of *every* StreamField in the project (snippets, settings models…). |
| `PRBLM_BUILDER_DEMO` | `True` | `False` turns the Block library off (its menu item, header link and page). |

A block can also hide itself — see [Hiding a block](#hiding-a-block).

### New blocks and demo content

| Setting | Default | What it does |
|---|---|---|
| `PRBLM_BUILDER_PLACEHOLDER_IMAGES` | `True` | Only matters when your Wagtail **image library is empty**. Demo previews normally use real images from your library; if there are none, the plugin creates a few grey gradient images titled "Builder placeholder …". `False` = never create them (demos then have no image). On a site that already has images, changing this does nothing visible. |
| `PRBLM_BUILDER_INDEX_SCAN_LIMIT` | `500` | Pages per model scanned to find real content to use in demos (newest first). Lower it on very large sites. |

### Admin integration

| Setting | Default | What it does |
|---|---|---|
| `PRBLM_BUILDER_ADMIN_TWEAKS` | `True` | Two extras in the **page editor** that rely on Wagtail admin internals. Set `False` if a Wagtail upgrade breaks them — the Layout tab and saving keep working. See the table below. |

| `PRBLM_BUILDER_SITE_BLOCK_COLUMNS` | `False` | `True` = your **own** blocks' fields use the two-column layout too (short fields side by side, long ones full width; one column on narrow screens). The built-in blocks and the Theme page always use it. |

What `PRBLM_BUILDER_ADMIN_TWEAKS` changes (in the page editor only — not the Block library page or the canvas itself):

| | `True` (default) | `False` |
|---|---|---|
| Layout tab width | Stretches to the full editor width (while the preview / comments side panel is closed) | Wagtail's normal form width (~840px) |
| "Block library" button | Shown in the editor's top-right header, next to the preview / comments icons | Not shown (still reachable from **Page builder → Block library**) |

### Built-in blocks

| Setting | Default | What it does |
|---|---|---|
| `PRBLM_BUILDER_PAGE_TYPE` | `True` | `False` hides the ready-made **Builder page** type from *Add page*. Existing Builder pages keep working. Only applies when `prblm_builder.blocks` is installed. |
| `PRBLM_BUILDER_PAGE_PARENTS` | `[]` | Page types under which Builder pages may be added, e.g. `["home.HomePage"]` — needed when a page type limits its children with `subpage_types`. Unknown names give startup warning `prblm_builder_blocks.W001`. |
| `PRBLM_BUILDER_PAGE_EXTRA_BLOCKS` | `None` | Your own blocks on the Builder page: `[("name", "dotted.path.Block"), …]` or the dotted path of a function returning `[(name, block), …]`. No migration needed. |

The Theme, Headers and Footers are set in the admin, not in settings.

### Example

```python
# <project>/settings/base.py
INSTALLED_APPS = ["prblm_builder", ...]

PRBLM_BUILDER_PREVIEW_CSS = ["css/main.css"]
PRBLM_BUILDER_PREVIEW_BODY_CLASS = "font-sans text-gray-900"
PRBLM_BUILDER_HEADER_TEMPLATE = "components/header.html"
PRBLM_BUILDER_FOOTER_TEMPLATE = "components/footer.html"
PRBLM_BUILDER_CANVAS_WIDTH = 1440
PRBLM_BUILDER_EXCLUDE_BLOCKS = ["core.blocks.LinkBlock"]
```

## Which blocks show up

The Layout palette and the Block library list the **top-level blocks of your page
`body` fields** — the sections an editor can actually place. Blocks used only *inside*
other blocks (links, buttons, cards…) or only in non-page StreamFields never appear.
A block also needs its own `template` to be shown (it's what the preview renders).

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

## Section settings (⚙)

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
  tab (Wagtail 8.1 `form_layout`), so editors aren't distracted by them there.
- Changes save with the page. Only fields you changed in the ⚙ panel are sent; if the
  same field was also changed in the Content tab, the Layout tab's change wins.
- Each value is checked by its own field (e.g. an invalid anchor ID) — a bad value shows
  as a normal error when saving, and your layout is kept.
- Choosers, rich text and nested blocks aren't shown in the ⚙ panel — edit those in the
  Content tab.

## Block previews and descriptions

If your blocks use Wagtail's own block-preview options (Wagtail 6.4+), the plugin uses
them too:

```python
("promo", PromoBlock(
    preview_value={"title": "Spring sale", "text": "20% off everything"},
    description="A coloured band with a title and short text.",
))
```

- **`preview_value`** is the first choice for the Block library, the sidebar thumbnails
  and the starting content of a newly added section (before real site content or
  generated text).
- **`description`** shows under the block's name in the Block library and as a tooltip in
  the Layout sidebar (and is searchable). The built-in blocks have descriptions.

## How it works

- **Edits the draft.** Like Wagtail's own editor, the Layout tab shows and builds on the
  page's latest draft (revision), not only what's published.
- **No block list.** It asks each page model's StreamField which blocks it allows
  (`PRBLM_BUILDER_FIELD_NAMES`, default `body`). Models, templates and static files are
  found the normal Django/Wagtail way, so no paths need configuring.
- **Auto-attach.** On startup it adds the Layout tab to each enabled page model's editor
  and wraps its form, so your models need no code changes.
- **Ride-along save.** The Layout tab writes the arrangement into hidden fields on the
  edit form; on Save/Publish the form rebuilds the StreamField in that order. Existing
  blocks keep their content; new ones get demo content (flagged "Not edited yet" until changed); duplicates copy
  their source. Blocks added or deleted in the Content tab are respected.
- **Real demo content.** Previews prefer a real instance of each block used elsewhere on
  the site (real images + copy, with its page as context), falling back to generated
  content. Long text is shortened in previews only — never in saved content.
- **Scaled previews.** Each section renders in its own iframe at desktop width
  (`PRBLM_BUILDER_CANVAS_WIDTH`) and is scaled down to fit, so you see the desktop layout
  even in a narrow editor column.

## Project structure

```
prblm_builder/                  the installable Django app
  apps.py                       on startup → integration.autoenable()
  integration.py                adds the Layout tab + save form to every enabled page model
  panels.py                     LayoutBuilderPanel — the Layout tab (embeds the builder iframe)
  forms.py                      LayoutBuilderForm — applies the arrangement on Save/Publish
  layout.py                     reconcile() — merges arrangement + content; new-block values
  registry.py                   finds page models + blocks; palette/library lists; hiding rules
  previews.py                   demo content (real → generated → trimmed) + preview HTML frame
  views.py                      builder, builder_new, preview, demo (Block library), save
  wagtail_hooks.py              admin URLs + the "Page builder" sidebar section
  settings.py                   reads every PRBLM_BUILDER_* setting (with defaults)
  checks.py                     startup warnings (e.g. removed settings)
  mixins.py                     BuilderSettingsMixin (⚙ settings → Wagtail's settings area)
  chrome.py                     header/footer around the canvas (template setting / hooks)
  templates/prblm_builder/      builder.html (canvas), layout_panel.html (tab), demo.html (library)
  static/prblm_builder/         builder.js, builder.css, fold.js, vendor/sortable.min.js
  tests/test_builder.py         generic tests — also runnable inside a host project
  blocks/                       optional app "prblm_builder.blocks" (built-in blocks)
    __init__.py                 builder_blocks() helper
    sections/                   the 21 blocks: site, heroes, content, conversion, media, utility
      base.py                   shared LinkBlock, BackgroundBlock, AnchorBlock, icon choice
    models.py                   ThemeSettings, SiteHeader, SiteFooter, BuilderPage
    fields.py                   Builder page body: built-ins + PRBLM_BUILDER_PAGE_EXTRA_BLOCKS
    theme.py                    theme values → CSS variables
    chrome.py                   which header/footer a page shows
    icons.py                    the built-in line icons
    templatetags/prblm_blocks.py  prblm_assets, prblm_header/footer, pbk_icon, pbk_image
    templates/prblm_builder/blocks/  one template per block + builder_page.html
    static/prblm_builder/blocks/     blocks.css, blocks.js, link-block.js (link type switch)
    wagtail_hooks.py            Theme / Headers / Footers menu items, canvas header/footer
tests/                          test project for this repo (not shipped)
  settings.py, urls.py          minimal Wagtail settings
  testapp/                      StandardPage + edge-case blocks; BlocksPage (built-ins)
  test_options.py               settings and Block library rules
  test_blocks*.py, test_site_chrome.py, test_builder_page.py   built-in blocks
  test_save_flow.py, test_page_options.py   save banner, folding, page placement, extra blocks
  test_v05.py                   preview values, links, ⚙ settings, copy/paste, Page tab, drafts
runtests.py                     runs all tests against tests/
.github/workflows/test.yml      CI: tests on Python 3.12–3.14 + wheel build check
docs/DEVELOPMENT_HISTORY.md     architecture, design decisions, bugs + lessons, roadmap
CHANGELOG.md                    what changed in each release
```

## Development

```bash
git clone git@github.com:prblmcodes/prblm-builder.git
cd prblm-builder
python -m venv .venv && source .venv/bin/activate
pip install -e .
python runtests.py                                   # all tests
python runtests.py tests.test_options                # one module
python runtests.py makemigrations                    # after changing tests/testapp/models.py
python runtests.py makemigrations prblm_builder_blocks   # after changing the built-in blocks
```

Inside a host project you can also run the generic tests against its own models:
`python manage.py test prblm_builder` (needs a page model whose StreamField has a
`rich_text` block).

Releasing: bump `version` in `pyproject.toml`, add a `CHANGELOG.md` entry, commit, then
`git tag -a vX.Y.Z -m "…" && git push origin main vX.Y.Z`, and create the GitHub release
from the tag (attach the wheel from `python -m build`).

## Upgrading

**0.5 → 0.6**
- No migrations, no setting changes needed — just install the new version.
- The **Layout** tab is now the first tab in the page editor.
- The built-in blocks' forms use two columns. Want it for your own blocks too?
  `PRBLM_BUILDER_SITE_BLOCK_COLUMNS = True`.
- Builder pages that show your site's header/footer, or contain your own blocks, now load
  your site's CSS/JS (`PRBLM_BUILDER_PREVIEW_CSS` / `_JS`) — so make sure those are set.
- Built-in blocks are now shielded from your site's global CSS. If you relied on a site rule
  changing a built-in block (other than fonts, which they still inherit), use the Theme or
  your own block instead.

**0.4 → 0.5**
- Run `python manage.py migrate` (migration `0003_link_types` only updates the built-in
  blocks' stored definitions — no content changes).
- If you use `builder_blocks()` in your own page models, run `python manage.py
  makemigrations` once: it records the new link fields as an "Alter field" (no data change).
- Existing links keep working: their link type is worked out from what they contain.
- Builder pages: the header/footer choice moved from the Content tab to the Layout
  sidebar's **Page** tab.
- Sections added with 0.4's example content may lose their "Not edited yet" badge (the
  example links changed shape). Nothing else changes.

**0.3 → 0.4**
- Run `python manage.py migrate`. Your 0.3 **Header & footer** content moves
  automatically into **Page builder → Headers / Footers**, marked as the site default.
- `{% prblm_header %}` / `{% prblm_footer %}` keep working (they show the site default).
- Builder pages get *Header* / *Footer* options; existing ones use **Site default**, so
  nothing changes on your site.
- New optional settings: `PRBLM_BUILDER_PAGE_PARENTS`, `PRBLM_BUILDER_PAGE_EXTRA_BLOCKS`.

**0.2 → 0.3**
- `PRBLM_BUILDER_SEED_NEW_BLOCKS` was removed: new blocks always start with content and
  the canvas marks them **"Not edited yet"**. Delete the setting (a startup warning,
  `prblm_builder.W001`, reminds you).
- The Block library moved from *Settings* to the new **Page builder** sidebar section.
- The built-in blocks are new and optional — nothing changes unless you add
  `prblm_builder.blocks`.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| No Layout tab on a page type | Its StreamField isn't called `body` → set `PRBLM_BUILDER_FIELD_NAMES`, or check `PRBLM_BUILDER_PAGE_MODELS`. |
| A block is missing from the palette | It has no `template`, or it's hidden (`builder = False`, `PRBLM_BUILDER_EXCLUDE_BLOCKS`, template prefix). |
| A non-section block (link, button) shows up | It's a top-level option of a page `body` field → hide it with `builder = False` or `PRBLM_BUILDER_EXCLUDE_BLOCKS`. |
| `PRBLM_BUILDER_EXCLUDE_BLOCKS` has no effect | You used a bare class name (`"LinkBlock"`) — use the StreamField name (`"link"`) or the full path (`"core.blocks.LinkBlock"`). See [Hiding a block](#hiding-a-block). |
| `PRBLM_BUILDER_PLACEHOLDER_IMAGES` does nothing | Expected when your image library has images — it only applies to an empty library. |
| `PRBLM_BUILDER_ADMIN_TWEAKS` seems to do nothing | Look in the **page editor**: Layout tab width and the "Block library" button in the top-right header. If that button never appears even with `True`, please open an issue. |
| Previews are unstyled | `PRBLM_BUILDER_PREVIEW_CSS` not set or wrong path (relative to `static/`). |
| Fonts/colours differ from the site | Your CSS relies on `<body>` classes → set `PRBLM_BUILDER_PREVIEW_BODY_CLASS`. |
| `/demo` gives 404 | The Block library lives under the admin: `/admin/page-builder/demo/`. |
| Block library 404 at the right address | `PRBLM_BUILDER_DEMO = False` is set. |
| Canvas blank on a server | `collectstatic` not run. |
| Full-width tab / header link broke after a Wagtail upgrade | Set `PRBLM_BUILDER_ADMIN_TWEAKS = False` and open an issue. |
| Error `prblm_builder_blocks.E001` on startup | Add `"wagtail.contrib.settings"` to `INSTALLED_APPS`. |
| Built-in blocks not in a page's palette | They must be in that page's StreamField: use the **Builder page**, or add `builder_blocks()` to your model and run `makemigrations` + `migrate`. |
| Your site's header looks unstyled on a Builder page | Set `PRBLM_BUILDER_PREVIEW_CSS` (and `_JS`) to your site's files — Builder pages load them when they show your site's header/footer. |
| `PRBLM_BUILDER_SITE_BLOCK_COLUMNS = True` changes nothing | Hard-refresh the admin (Ctrl+Shift+R). Two columns apply to StructBlock forms; a plain text/rich-text block has a single field. |
| No "Builder page" in *Add page* | `prblm_builder.blocks` not installed / not migrated, or `PRBLM_BUILDER_PAGE_TYPE = False`. |
| Theme changes don't affect my own blocks | Expected — the Theme only styles the built-in blocks. |
| Site-wide header not on my live pages | Add `{% load prblm_blocks %}{% prblm_header %}` to your base template (the Builder page shows it automatically). |
| Builder page only offered at the top level, not under Home | Your home page type restricts its children: add `PRBLM_BUILDER_PAGE_PARENTS = ["home.HomePage"]`. |
| New sections don't appear in the Content tab | Save the page first (use **Save draft now** in the banner) — the Content tab only shows saved sections. |
| `ImproperlyConfigured: PRBLM_BUILDER_PAGE_EXTRA_BLOCKS …` | A block path can't be imported, an entry isn't a `("name", "path")` pair, or a name clashes with a built-in block. The message says which. |
| A "Snippets" menu appeared | Headers and Footers are stored as snippets; Wagtail lists them there too. |
| No ⚙ button on my block's sections | List the fields in the block's `Meta.builder_settings` (only choice, on/off and short-text fields are shown). |
| My block's settings still show in the Content tab | Add `BuilderSettingsMixin` to the block to move them into Wagtail's collapsed settings area. |
| Paste is greyed out in the right-click menu | Copy a section first — copy & paste work within the same page. |
| `makemigrations` wants to alter my page's `body` after upgrading to 0.5 | Expected if you use `builder_blocks()`: the built-in link fields changed. Run it; no data changes. |
| Warning `prblm_builder.W001` | Remove `PRBLM_BUILDER_SEED_NEW_BLOCKS` from your settings. |

## License

MIT — see [LICENSE](LICENSE).
