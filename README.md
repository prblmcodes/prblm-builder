# prblm-builder

A visual drag-and-drop **page builder** for Wagtail. It adds a **Layout** tab to the
page editor where you compose a page by dragging the site's own StreamField blocks onto
a canvas — reorder, duplicate and delete sections with live, desktop-scaled previews.
Arrange in the Layout tab; edit each block's words and images in the normal **Content**
tab; your arrangement saves with the page's own **Save draft / Publish** (nothing extra).

Works on any Wagtail site: it discovers your blocks by introspection — no block list to
maintain — and attaches itself automatically to every page type that has a buildable
StreamField.

## Install

```python
# requirements.txt   (local editable during development)
-e ./packages/prblm-builder

# settings.py
INSTALLED_APPS = [
    # …
    "prblm_builder",
]

# optional — point previews at your front-end assets so sections look like production
PRBLM_BUILDER_PREVIEW_CSS = ["css/your-site.css"]     # static paths or URLs
PRBLM_BUILDER_PREVIEW_JS = ["js/your-site.js"]
PRBLM_BUILDER_PREVIEW_BODY_CLASS = ""                 # class on the preview <body>
PRBLM_BUILDER_HEADER_TEMPLATE = ""                    # optional: site header shown on the canvas
PRBLM_BUILDER_FOOTER_TEMPLATE = ""                    # optional: site footer shown on the canvas
PRBLM_BUILDER_FIELD_NAMES = ["body"]                  # which StreamField to build (priority order)
PRBLM_BUILDER_PAGE_MODELS = None                      # None = auto-detect; or ["app.Model"]
PRBLM_BUILDER_DEMO = True                             # the admin-only Block library
PRBLM_BUILDER_EXCLUDE_TEMPLATE_PREFIXES = ()          # block templates to hide (e.g. email blocks)
PRBLM_BUILDER_INDEX_SCAN_LIMIT = 500                  # pages/model scanned for real demo content
```

With nothing configured, it enables any page model that has a StreamField named `body`
and renders previews unstyled. No per-model code is needed — the plugin inserts the
**Layout** tab and the save wiring from its app `ready()`.

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
  the site (real images + copy), falling back to deterministic synthesis.

Requires Wagtail ≥ 7.0. Some editor-chrome niceties (full-width canvas, the header link)
rely on Wagtail admin classes and degrade gracefully on other versions.
