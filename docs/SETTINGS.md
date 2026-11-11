# Settings reference

Every setting is optional and goes in your Django settings file (the one with
`INSTALLED_APPS`). With nothing set, the plugin enables any page model with a `body`
StreamField and renders previews unstyled. After changing a setting, restart the server
(`runserver` does this automatically) and hard-refresh the admin page.

- [Previews — make the canvas look like your site](#previews--make-the-canvas-look-like-your-site)
- [Which pages get the Layout tab](#which-pages-get-the-layout-tab)
- [Block visibility](#block-visibility)
- [New blocks and demo content](#new-blocks-and-demo-content)
- [Admin integration](#admin-integration)
- [Built-in blocks](#built-in-blocks)
- [Example](#example)

## Previews — make the canvas look like your site

| Setting | Default | What it does |
|---|---|---|
| `PRBLM_BUILDER_PREVIEW_CSS` | `[]` | CSS files loaded into every preview. Static paths (`"css/main.css"`) or full URLs, in load order. Also dicts for options (`media`, `integrity`, inline CSS) — see [Scripts and stylesheets](GUIDE.md#scripts-and-stylesheets). |
| `PRBLM_BUILDER_PREVIEW_JS` | `[]` | JS files loaded into every preview (e.g. sliders, accordions), in load order. Also dicts for `defer`, `type="module"`, `integrity`, inline scripts, import maps. |
| `PRBLM_BUILDER_PREVIEW_BODY_CLASS` | `""` | Classes for the preview `<body>`. Copy them from the `<body class="…">` in your `base.html` if your CSS relies on them (fonts, colours). Leave empty if your `<body>` has no classes. |
| `PRBLM_BUILDER_HEADER_TEMPLATE` | `""` | Template of your site header, shown above the canvas. Gets `page` / `self` (the page being edited; not set on a brand-new unsaved page). |
| `PRBLM_BUILDER_FOOTER_TEMPLATE` | `""` | Same, for the footer, shown below the canvas. |
| `PRBLM_BUILDER_CANVAS_WIDTH` | `1280` | Desktop width (px) sections render at before being scaled to fit the editor. Set it to your design width (e.g. `1440`). |
| `PRBLM_BUILDER_CANVAS_HEIGHT` | `900` | Screen height (px) previews pretend to have, so sections sized in `vh` (`min-h-[70vh]`, `h-screen`) look as on a real screen. Minimum 300. |
| `PRBLM_BUILDER_PREVIEW_TEMPLATE` | `""` | A template of yours that previews render each section inside — it extends your `base.html`, so the canvas gets your real `<head>`, `<body>` attributes and inline scripts. See [Your own preview template](GUIDE.md#your-own-preview-template). |
| `PRBLM_BUILDER_PREVIEW_SITES` | `{}` | Several sites with different CSS / headers: per-site overrides of the settings above, keyed by Wagtail Site hostname, site name or wildcard. See [Several sites](GUIDE.md#several-sites). |
| `PRBLM_BUILDER_PREVIEW_BODY_ATTRS` | `{}` | Extra `<body>` attributes for previews (and Builder pages using your assets), e.g. `{"x-data": "{ showModal: false }"}`. Ignored with a preview template. |
| `PRBLM_BUILDER_PREVIEW_HTML_ATTRS` | `{}` | Extra `<html>` attributes, e.g. `{"data-theme": "light"}`. Ignored with a preview template. |
| `PRBLM_BUILDER_CANVAS_OVERLAP` | `True` | Sections overlap on the canvas where they overlap on the live page: a **transparent** fixed/absolute header lies over the first section, and a section pulled up or down by a **negative margin** covers its neighbour. `False`: everything stacked (nothing is cut off either way). Per site: `"canvas_overlap"` in a `PRBLM_BUILDER_PREVIEW_SITES` profile. See [Overlapping headers and sections](GUIDE.md#overlapping-headers-and-sections). |
| `PRBLM_BUILDER_REDUCE_MOTION` | `True` | Animations and transitions finish instantly in previews (they're still pictures). Previews always have `class="prblm-canvas"` on `<html>`. See [Animations](GUIDE.md#animations-and-scroll-effects). |

## Which pages get the Layout tab

| Setting | Default | What it does |
|---|---|---|
| `PRBLM_BUILDER_FIELD_NAMES` | `["body"]` | StreamField name(s) to build on, in priority order — e.g. `["body", "content"]`. A model gets the tab if it has one of these. |
| `PRBLM_BUILDER_PAGE_MODELS` | `None` | `None` = every page model with a matching field. Or limit it: `["home.StandardPage", "blog.BlogPage"]`. |

## Block visibility

| Setting | Default | What it does |
|---|---|---|
| `PRBLM_BUILDER_EXCLUDE_BLOCKS` | `[]` | Hide blocks from the palette + Block library. Each entry is either the block's **name in the StreamField** (`"link"`) or the **full import path of its class** (`"core.blocks.LinkBlock"`, also hides subclasses). A bare class name like `"LinkBlock"` does **not** work — see [Hiding a block](GUIDE.md#hiding-a-block). |
| `PRBLM_BUILDER_EXCLUDE_TEMPLATE_PREFIXES` | `()` | Hide blocks whose template path starts with one of these (e.g. `("emails/",)` for email-only blocks). |
| `PRBLM_BUILDER_LIBRARY_SCOPE` | `"builder"` | What the Block library lists: `"builder"` = the same blocks as the Layout palette; `"all"` = top-level blocks of every StreamField on **any page type**, also ones without the Layout tab (not snippets, settings or menu apps — their blocks aren't page sections). |
| `PRBLM_BUILDER_BLOCK_ORDER` | `"usage"` | Order of blocks and groups in the Layout sidebar and Block library: `"usage"` = most used on published pages first; `"alpha"` = A–Z. |
| `PRBLM_BUILDER_DEMO` | `True` | `False` turns the Block library off (its menu item, header link and page). |

A block can also hide itself — see [Hiding a block](GUIDE.md#hiding-a-block).

## New blocks and demo content

| Setting | Default | What it does |
|---|---|---|
| `PRBLM_BUILDER_PLACEHOLDER_IMAGES` | `True` | Demo content picks library images that fit each image field (wide photos for banners, square or transparent images for logos). When none fits, the plugin creates a labelled placeholder of the right shape ("Banner · 1600×900", "Logo / icon · 400×400", "Photo · 1200×800"), once, in a **Builder placeholders** collection. `False` = never create them (the field stays empty if it's optional). |
| `PRBLM_BUILDER_INDEX_SCAN_LIMIT` | `500` | Published pages per model scanned to find real content for demos and the Block library's "Used on" counts (newest first). Lower it on very large sites. |

## Admin integration

| Setting | Default | What it does |
|---|---|---|
| `PRBLM_BUILDER_ADMIN_TWEAKS` | `True` | Two extras in the **page editor** that rely on Wagtail admin internals. Set `False` if a Wagtail upgrade breaks them — the Layout tab and saving keep working. See the table below. |
| `PRBLM_BUILDER_SITE_BLOCK_COLUMNS` | `False` | `True` = your **own** blocks' fields use the two-column layout too (short fields side by side, long ones full width; one column on narrow screens). The built-in blocks and the Theme page always use it. |

What `PRBLM_BUILDER_ADMIN_TWEAKS` changes (in the page editor only — not the Block library page or the canvas itself):

| | `True` (default) | `False` |
|---|---|---|
| Layout tab width | Stretches to the full editor width (while the preview / comments side panel is closed) | Wagtail's normal form width (~840px) |
| "Block library" button | Shown in the editor's top-right header, next to the preview / comments icons | Not shown (still reachable from **Page builder → Block library**) |

## Built-in blocks

| Setting | Default | What it does |
|---|---|---|
| `PRBLM_BUILDER_PAGE_TYPE` | `True` | `False` hides the ready-made **Builder page** type from *Add page*. Existing Builder pages keep working. Only applies when `prblm_builder.blocks` is installed. |
| `PRBLM_BUILDER_PAGE_PARENTS` | `[]` | Page types under which Builder pages may be added, e.g. `["home.HomePage"]` — needed when a page type limits its children with `subpage_types`. Unknown names give startup warning `prblm_builder_blocks.W001`. |
| `PRBLM_BUILDER_PAGE_EXTRA_BLOCKS` | `None` | Your own blocks on the Builder page: `[("name", "dotted.path.Block"), …]` or the dotted path of a function returning `[(name, block), …]`. No migration needed. |

The Theme, Headers and Footers are set in the admin, not in settings.

## Example

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
