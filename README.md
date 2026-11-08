# prblm-builder

A visual drag-and-drop **page builder** for Wagtail. It adds a **Layout** tab to the
page editor where you compose a page by dragging the site's own StreamField blocks onto
a canvas — reorder, duplicate and delete sections with live, desktop-scaled previews.
Arrange in the Layout tab; edit each block's words and images in the normal **Content**
tab; your arrangement saves with the page's own **Save draft / Publish** (nothing extra).

Works on any Wagtail site: it discovers your blocks by introspection — no block list to
maintain — and attaches itself automatically to every page type that has a buildable
StreamField.

## Requirements

- Python 3.12+
- Django 6.1+
- Wagtail 8.1+ (below 9)

## Install

Install from a GitHub release tag:

```bash
# public repo
pip install "prblm-builder @ git+https://github.com/prblmcodes/prblm-builder.git@v0.2.0"

# private repo (uses your GitHub SSH key)
pip install "prblm-builder @ git+ssh://git@github.com/prblmcodes/prblm-builder.git@v0.2.0"
```

Or put the same `prblm-builder @ git+…@v0.2.0` line in `requirements.txt`. You can also
download the wheel attached to a GitHub release and `pip install prblm_builder-0.2.0-py3-none-any.whl`.

Then add it to your settings:

```python
INSTALLED_APPS = [
    "prblm_builder",
    # … your apps, wagtail apps, …
]
```

No migrations, no URL changes — it registers its admin URLs through Wagtail hooks. Any
page model with a StreamField named `body` now has a **Layout** tab.

## Configure (all optional)

```python
# point previews at your front-end assets so sections look like production
PRBLM_BUILDER_PREVIEW_CSS = ["css/your-site.css"]     # static paths or URLs
PRBLM_BUILDER_PREVIEW_JS = ["js/your-site.js"]
PRBLM_BUILDER_PREVIEW_BODY_CLASS = ""                 # class on the preview <body>
PRBLM_BUILDER_HEADER_TEMPLATE = ""                    # site header shown on the canvas
PRBLM_BUILDER_FOOTER_TEMPLATE = ""                    # site footer shown on the canvas
PRBLM_BUILDER_FIELD_NAMES = ["body"]                  # which StreamField to build (priority order)
PRBLM_BUILDER_PAGE_MODELS = None                      # None = auto-detect; or ["app.Model"]
PRBLM_BUILDER_DEMO = True                             # the admin-only Block library
PRBLM_BUILDER_EXCLUDE_TEMPLATE_PREFIXES = ()          # block templates to hide (e.g. email blocks)
PRBLM_BUILDER_INDEX_SCAN_LIMIT = 500                  # pages/model scanned for real demo content

# since 0.2.0
PRBLM_BUILDER_EXCLUDE_BLOCKS = []                     # hide blocks by name ("link") or class path
PRBLM_BUILDER_LIBRARY_SCOPE = "builder"               # "builder" = palette blocks; "all" = every StreamField
PRBLM_BUILDER_SEED_NEW_BLOCKS = True                  # False = new blocks start empty, not with demo content
PRBLM_BUILDER_CANVAS_WIDTH = 1280                     # desktop width (px) sections render at on the canvas
PRBLM_BUILDER_PLACEHOLDER_IMAGES = True               # False = never add placeholder images to the library
PRBLM_BUILDER_ADMIN_TWEAKS = True                     # False = no full-width tab / header link (Wagtail internals)
```

With nothing configured, it enables any page model that has a StreamField named `body`
and renders previews unstyled. Blocks need their own `template` to be previewable.

## Which blocks show up

The Layout palette and the Block library list the **top-level blocks of your page
`body` fields** — the sections an editor can actually place. Blocks used only *inside*
other blocks (links, buttons, cards…) or only in non-page StreamFields never appear.

To hide a block that is a top-level option but isn't a real section, either:

```python
# 1. on the block itself — travels with the block, whatever it's called
class LinkBlock(blocks.StructBlock):
    ...
    class Meta:
        template = "components/link.html"
        builder = False

# 2. or in settings — by StreamField name, or by class (also hides subclasses)
PRBLM_BUILDER_EXCLUDE_BLOCKS = ["link", "core.blocks.LinkBlock"]
```

Blocks that error or render nothing with demo content are listed in a collapsed
**"Couldn't preview"** section at the bottom of the Block library, with the reason — they
stay available in the Layout palette.

## Header and footer on the canvas

`PRBLM_BUILDER_HEADER_TEMPLATE` / `_FOOTER_TEMPLATE` are rendered with the request, and
with `page` / `self` set to the page being edited (not set on a brand-new unsaved page).

## Use

- **Any page:** open it in the editor → the **Layout** tab. Drag sections from the left,
  reorder/duplicate/delete, and **Save draft / Publish** as usual. Undo/redo with
  Ctrl/⌘+Z and Ctrl/⌘+Shift+Z.
- **New page:** the Layout tab works before the first save — arrange, then the sections
  save with the page.
- **Block library:** Settings → *Block library* (or the link in the editor header) shows
  every block with realistic demo content.

## How it works

- **No block list.** It introspects each page model's StreamField(s) for the blocks to
  offer (`PRBLM_BUILDER_FIELD_NAMES`, default `body`).
- **Ride-along save.** The Layout tab writes the arrangement into hidden fields on the
  edit form; a composed `base_form_class` reconciles order + membership on the page's own
  save. Existing blocks keep their content; new ones are seeded with demo content.
- **Real demo content.** Previews prefer a real instance of each block used elsewhere on
  the site (real images + copy), falling back to deterministic synthesis. With
  `PRBLM_BUILDER_SEED_NEW_BLOCKS = False`, new blocks start empty instead and show a
  "New …" placeholder on the canvas until you fill them in. If the site has
  no images, it creates a few soft-gradient placeholder images (titled "Builder placeholder …") in the image library.

Some editor-chrome niceties (full-width canvas, the header link) rely on Wagtail admin
CSS classes and degrade gracefully if a future Wagtail version changes them.

## Development

```bash
pip install -e .
python runtests.py          # runs the suite against the bundled test project (tests/)
```

CI runs the tests on Python 3.12–3.14 against the latest Wagtail 8.x / Django 6.x.

## License

MIT — see [LICENSE](LICENSE).
