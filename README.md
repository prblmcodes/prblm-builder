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
pricing, FAQ, footer, …), a ready-made **Builder page** type, a **Theme** page and a
site-wide **Header & footer** — fully self-contained, nothing extra to install. See
[Built-in blocks](#built-in-blocks-optional).

- [Requirements](#requirements)
- [Install](#install)
- [Quick setup](#quick-setup)
- [Use](#use)
- [Built-in blocks (optional)](#built-in-blocks-optional)
- [Settings reference](#settings-reference)
- [Which blocks show up](#which-blocks-show-up)
  - [Hiding a block](#hiding-a-block)
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
pip install "prblm-builder @ git+https://github.com/prblmcodes/prblm-builder.git@v0.3.0"

# private repo (uses your GitHub SSH key)
pip install "prblm-builder @ git+ssh://git@github.com/prblmcodes/prblm-builder.git@v0.3.0"
```

Or put the same `prblm-builder @ git+…@v0.3.0` line in `requirements.txt`. You can also
download the wheel attached to a GitHub release and
`pip install prblm_builder-0.3.0-py3-none-any.whl`.

To upgrade later, change the tag (e.g. `@v0.3.0` → `@v0.4.0`) and reinstall. See
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

- **Any page:** open it in the editor → the **Layout** tab. Drag sections from the left,
  reorder/duplicate/delete, and **Save draft / Publish** as usual. Undo/redo with
  Ctrl/⌘+Z and Ctrl/⌘+Shift+Z.
- **Edit content:** each section's words and images are edited in the normal **Content**
  tab. New sections start with demo content; until you change it, the canvas marks the
  section **"Not edited yet"** so placeholder text doesn't get published by accident.
- **New page:** the Layout tab works before the first save — arrange, then the sections
  save with the page.
- **Page builder menu:** the plugin adds a **Page builder** section to the admin sidebar:
  - **Block library** — every block with a live preview, grouped into *Built-in blocks*
    and *Your site's blocks*. Address: `/admin/page-builder/demo/` (use your own admin
    prefix if it isn't `admin/`). Also linked from the editor header.
  - **Theme** and **Header & footer** — only when the built-in blocks app is installed.

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
    "wagtail.contrib.settings",      # needed for Theme and Header & footer
    # …
]
```

```bash
python manage.py migrate
```

Then use the blocks in one (or both) of these ways.

**1. The ready-made "Builder page" (no code).** In the admin, *Add child page* → **Builder
page**. It has all 21 blocks and a Layout tab, and renders as a complete page: the
site-wide header, your sections, the site-wide footer. To render it inside your own site
layout instead, create a template at `prblm_builder/blocks/builder_page.html` in your
templates folder. To hide the page type from *Add page*: `PRBLM_BUILDER_PAGE_TYPE = False`.

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
etc. Links everywhere accept a page on your site *or* a typed address (`https://…`,
`/contact/`, `#section`).

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

### Header & footer (site-wide)

**Page builder → Header & footer** holds one Header and one Footer for the whole site.

- **In the builder:** they're shown above and below every page on the Layout canvas.
  (If you've set `PRBLM_BUILDER_HEADER_TEMPLATE` / `_FOOTER_TEMPLATE`, those win.)
- **On the Builder page:** shown automatically.
- **On your own templates (optional):** add the tags where you want them:

  ```django
  {% load prblm_blocks %}
  {% prblm_header %}
  …
  {% prblm_footer %}
  ```

  Each renders nothing if no Header / Footer has been set, so they're safe to add.

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

What `PRBLM_BUILDER_ADMIN_TWEAKS` changes (in the page editor only — not the Block library page or the canvas itself):

| | `True` (default) | `False` |
|---|---|---|
| Layout tab width | Stretches to the full editor width (while the preview / comments side panel is closed) | Wagtail's normal form width (~840px) |
| "Block library" button | Shown in the editor's top-right header, next to the preview / comments icons | Not shown (still reachable from **Page builder → Block library**) |

### Built-in blocks

| Setting | Default | What it does |
|---|---|---|
| `PRBLM_BUILDER_PAGE_TYPE` | `True` | `False` hides the ready-made **Builder page** type from *Add page*. Existing Builder pages keep working. Only applies when `prblm_builder.blocks` is installed. |

The Theme and the site-wide Header & footer are set in the admin, not in settings.

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

## How it works

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
  templates/prblm_builder/      builder.html (canvas), layout_panel.html (tab), demo.html (library)
  static/prblm_builder/         builder.js, builder.css, vendor/sortable.min.js
  tests/test_builder.py         generic tests — also runnable inside a host project
  blocks/                       optional app "prblm_builder.blocks" (built-in blocks)
    __init__.py                 builder_blocks() helper
    sections/                   the 21 blocks: site, heroes, content, conversion, media, utility
      base.py                   shared LinkBlock, BackgroundBlock, AnchorBlock, icon choice
    models.py                   ThemeSettings, SiteChrome (Header & footer), BuilderPage
    theme.py                    theme values → CSS variables
    chrome.py                   renders the site-wide header/footer
    icons.py                    the built-in line icons
    templatetags/prblm_blocks.py  prblm_assets, prblm_header/footer, pbk_icon, pbk_image
    templates/prblm_builder/blocks/  one template per block + builder_page.html
    static/prblm_builder/blocks/     blocks.css, blocks.js
    wagtail_hooks.py            Theme / Header & footer menu items, canvas header/footer
tests/                          test project for this repo (not shipped)
  settings.py, urls.py          minimal Wagtail settings
  testapp/                      StandardPage + edge-case blocks; BlocksPage (built-ins)
  test_options.py               settings and Block library rules
  test_blocks*.py, test_site_chrome.py, test_builder_page.py   built-in blocks
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
| No "Builder page" in *Add page* | `prblm_builder.blocks` not installed / not migrated, or `PRBLM_BUILDER_PAGE_TYPE = False`. |
| Theme changes don't affect my own blocks | Expected — the Theme only styles the built-in blocks. |
| Site-wide header not on my live pages | Add `{% load prblm_blocks %}{% prblm_header %}` to your base template (the Builder page shows it automatically). |
| Warning `prblm_builder.W001` | Remove `PRBLM_BUILDER_SEED_NEW_BLOCKS` from your settings. |

## License

MIT — see [LICENSE](LICENSE).
