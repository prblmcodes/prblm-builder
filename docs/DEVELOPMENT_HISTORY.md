# prblm-builder — development history & design notes

This document is the curated record of how **prblm-builder** was built, the decisions
behind it, the bugs that shaped it, and what's left to do. It was written so that anyone
(human or an AI assistant in a fresh session) can get fully up to speed without the
original chat transcript.

The plugin was developed *inside* a real Wagtail site ("bemore") as a local editable
package under `packages/prblm-builder/`, then extracted to this standalone repo. Nothing
in this doc depends on that host site; it works on any Wagtail project.

---

## 1. What it is

A visual **drag-and-drop page builder** for Wagtail. It adds a **Layout** tab to the page
editor where you compose a page by dragging the site's *own* StreamField blocks onto a
canvas — reorder, duplicate, delete, with live desktop-scaled previews. You arrange in the
Layout tab; you edit each block's words/images in the normal **Content** tab; your
arrangement saves with the page's own **Save draft / Publish** (nothing extra to save).

Design pillars:

- **No block list to maintain.** It discovers blocks by introspecting each page model's
  StreamField(s).
- **Zero per-model wiring.** It attaches the Layout tab + save logic to every block-based
  page model automatically, from the app's `ready()`.
- **Ride-along save.** The arrangement is written into hidden fields on the edit form and
  reconciled on the page's own save — no separate save step, no fragile StreamField JS.
- **Realistic previews.** Demo content prefers a *real* instance of each block used
  elsewhere on the site (real images + copy), falling back to deterministic synthesis.

---

## 2. Architecture

### Block discovery — `registry.py`
Pure introspection, no site-specific code.
- `target_field_name(model)` — the StreamField to build on a model: the first configured
  name (`PRBLM_BUILDER_FIELD_NAMES`, default `["body"]`) the model actually has.
- `enabled_page_models()` — every `Page` subclass with a target StreamField (or the
  explicit `PRBLM_BUILDER_PAGE_MODELS` list).
- `stream_block_for(model)` → `(field_name, stream_block)`.
- `grouped_blocks(stream_block)` — palette groups for one field.
- `all_blocks()` / `grouped_all_blocks()` / `find_block(name)` — project-wide block
  catalogue (for the Block library / demo page).
- `previewable(name, block)` — a block with its own template, not under
  `PRBLM_BUILDER_EXCLUDE_TEMPLATE_PREFIXES` (e.g. email-only blocks).

### The Layout tab — `panels.py` + `integration.py`
- `LayoutBuilderPanel` is a Wagtail `Panel` whose bound template (`layout_panel.html`)
  embeds the builder in an **iframe** (`?embed=1`). For a saved page it points at the
  page-scoped builder; for a brand-new unsaved page it points at the model-scoped
  `builder_new` so you can lay out before the first save.
- `integration.autoenable()` (run from `apps.PrblmBuilderConfig.ready()`) inserts the
  Layout tab into every enabled model's `edit_handler` (after the Content tab) and composes
  `LayoutBuilderForm` onto the model's `base_form_class`. It's defensive — any failure for
  a model just means that model has no tab, never a broken admin. This is why host models
  need no manual wiring.

### Ride-along save — `forms.py` + `layout.py` + `builder.js`
- In the Layout tab, `builder.js` writes two hidden inputs onto the parent edit form:
  `_pb_layout` (the desired sections in order: `[{type, id, new?, copy_from?}]`) and
  `_pb_initial` (the ids known when the tab loaded).
- `LayoutBuilderForm.clean()` reads those, and `layout.reconcile()` rebuilds the target
  StreamField from the submitted content in the Layout tab's order:
  - existing blocks keep their stored content (matched by id);
  - new blocks are seeded with demo content;
  - a duplicate copies its source's content;
  - `_pb_initial` disambiguates a *Layout-tab delete* (a known id now dropped → drop) from
    a *block added in the Content tab* the Layout tab never saw (unknown id → keep), so it
    never resurrects a natively-deleted block or drops a natively-added one.
- If `_pb_layout` is absent (the editor never opened the Layout tab), nothing changes — the
  native body saves exactly as submitted.
- The standalone (non-embed) builder still has its own Save endpoint (`views.save`), which
  reuses the same `reconcile`.

### Previews — `views.py` (`preview`) + `previews.py` + `builder.js`
- `preview` renders a single block into an iframe document. Modes:
  `?page=<id>&section=<uuid>` = the real stored block; `?page=<id>&block=<name>&demo=1` or
  `?block=<name>` (unscoped) = demo content; `?chrome=header|footer` = the site header/footer.
- It's decorated `@xframe_options_sameorigin` because admin responses default to
  `X-Frame-Options: DENY`, which would blank the iframes.
- `previews.frame()` wraps the block HTML in a minimal document that loads the host's
  front-end CSS/JS (`PRBLM_BUILDER_PREVIEW_CSS/JS`) and **strips `loading="lazy"`** from
  images (see bug notes — lazy images never enter a scaled/offscreen frame).
- `builder.js` renders each section iframe at a fixed **1280px desktop width** and scales it
  to fit the canvas column (`scaleFit`), so the editor column's narrow width doesn't force
  the mobile layout. It sets the iframe's **own height** and the host's height from
  `body.scrollHeight`.

### Demo content engine — `previews.py`
Three layers, best-first:
1. **Real instance** — `real_instance_for(name)` returns the most-filled real instance of a
   block used anywhere on the site, plus the page it lives on (so hero-style blocks that
   read page fields render fully). Built once into a cached index
   (`instance_index`, ~60s), capped at `PRBLM_BUILDER_INDEX_SCAN_LIMIT` pages/model.
2. **Synthesis** — `synth_value(block, …)` builds a deterministic value from the block's
   structure using realistic copy pools; links fill exactly one destination so
   `LinkBlock.clean()` passes.
3. **Trim for display** — `trim_for_demo()` shortens long rich-text (~80 words) and long
   text (~360 chars) with an ellipsis so the Block library / canvas stay elegant. Display
   only — never alters stored/seeded content.

### Block library (demo page) — `views.demo` + `demo.html`
An admin-only page listing every previewable block grouped, each with a live demo preview
(same engine as the builder). Reachable from Settings → *Block library* and a link injected
into the editor header's top-right strip. Gated by `PRBLM_BUILDER_DEMO`.

---

## 3. The journey (chronological)

1. **MVP** — a standalone full-screen builder: palette of discovered blocks, SortableJS
   drag canvas, per-section preview iframes, its own Save → draft revision. Reached from an
   admin menu item + "Edit layout" buttons on pages.
2. **Phase 2 — integration & refactor (in the host site):**
   - Moved the demo/Block library into the plugin so the builder and demo share one content
     engine.
   - Added the builder as a **Layout tab** in the normal editor.
   - In the host site, removed a `page_style` select in favour of real blocks (a data
     migration converted existing pages — see the migration bug below).
3. **Layout-tab refinements:**
   - Removed the standalone entry points (menu item, Edit-layout buttons) — layout lives in
     the tab.
   - Removed *all* in-tab chrome (Preview / New-tab / Edit-content / Save buttons) and wired
     **ride-along save** so the page's own Save/Publish saves the arrangement.
   - Auto-attach the tab to every block-based page model (`integration.py`); dropped the
     host model's manual wiring.
   - Support the Layout tab on **brand-new unsaved pages** (model-scoped `builder_new`).
   - Render the canvas at **desktop width scaled to fit** (was showing the mobile layout);
     "Wider preview" toggle, draggable palette/canvas divider.
   - Made the tab use the **full editor width** (un-cap Wagtail's `.w-form-width`) but only
     when no side panel is open, so the native Preview panel sits beside it instead of being
     overlaid.
   - **Undo/redo** (Ctrl/⌘+Z, Ctrl/⌘+Shift+Z) over add/move/delete/duplicate.
4. **Block library polish:** full-width previews; real site content instead of filler;
   display-only text trimming; device toggle resizes the whole card and centres it; group
   titles follow the card width.
5. **Canvas rendering fixes** (the long tail — see bug notes): X-Frame-Options, lazy images,
   iframe default height, `documentElement.scrollHeight` inflation.
6. **Cleanup + portability:** removed dead code (`new_page`, `is_enabled`), capped the demo
   scan, rewrote the README.
7. **Extraction** to this standalone repo.
8. **v0.1.0 release** — moved to Wagtail 8.1 / Django 6.1, bundled test project + CI, MIT
   license, preview view hardened (bad params → 404, stored sections need edit permission).
9. **v0.2.0** — first install in a second project showed a reusable *link* block in the
   Block library with no preview. Fixed generically rather than by path: the library now
   lists only the palette's blocks (top-level blocks of builder-enabled page fields);
   blocks can opt out with `Meta: builder = False` or `PRBLM_BUILDER_EXCLUDE_BLOCKS`
   (name or class); unpreviewable blocks go to a collapsed "Couldn't preview" list. Added
   settings: SEED_NEW_BLOCKS, CANVAS_WIDTH, PLACEHOLDER_IMAGES, LIBRARY_SCOPE,
   ADMIN_TWEAKS; header/footer get the page. Lesson: an "empty" new block must use `""`
   for text fields — Wagtail's `get_default()` is `None`, which renders as "None".

---

## 4. Key decisions (and why)

- **Ride-along save over StreamField-JS editing.** Driving Wagtail's StreamField widget
  from the Layout tab would be fragile across versions. Instead the tab writes intent to
  hidden fields and the form reconciles on save — robust, and the Content tab stays the
  native editor. Trade-off: `body` is touched in two places, reconciled by id + the
  `_pb_initial` set.
- **Scaled iframes over a real-width canvas.** The editor column is far narrower than a
  page, so sections rendered their mobile layout. Rendering at 1280px and CSS-scaling shows
  the true desktop layout in the available space. Wagtail's own Preview remains the
  full-size preview.
- **Real content first, synth as fallback.** A real instance carries real images + copy and
  its page context, which fixes empty hero bands and missing images in one move. Synthesis
  covers blocks used nowhere yet.
- **Auto-attach from `ready()` over a mixin.** Host projects shouldn't have to edit each
  page model. Defensive so it can never break the admin.

---

## 5. Bugs fixed & lessons (the valuable part)

- **`X-Frame-Options: DENY`** blanks admin iframes → decorate framed views with
  `@xframe_options_sameorigin`.
- **SortableJS native HTML5 DnD is unreliable** (and hard to test) → `forceFallback: true,
  fallbackOnBody: true`.
- **Django `{# … #}` comments only work on ONE line.** A multi-line `{# #}` renders as
  visible text. Use `{% comment %}…{% endcomment %}`. (Hit twice.)
- **Data migrations must read soon-to-be-removed fields via the HISTORICAL model**
  (`apps.get_model`), not `from app.models import Model`. The live model no longer has those
  fields, so `getattr(p, "field", default)` silently returns the default and the migration
  converts nothing — then a later migration drops the columns and the data is gone. It can
  appear to work the first run only because the model still had the fields at that moment.
  If you also need Wagtail Page methods (`save_revision`/`publish`) the historical model
  lacks, read old fields via `apps.get_model` but load the same pk through the real model to
  write + publish. Always test a data migration from the *pre-migration* DB state.
- **Wagtail migration ↔ revision sync.** A data migration that sets a page field must also
  `save_revision()` and (if live) `publish()`, or the admin shows empty/stale content and
  the next publish reverts it.
- **Preview iframe height, three separate bugs:**
  1. *Lazy images* never enter a scaled/offscreen frame's viewport, so the frame loads
     before them and measures too short → strip `loading="lazy"` server-side.
  2. The iframe *element* kept the browser default **150px** height and clipped everything
     below it → set `frame.style.height` to the content height before scaling.
  3. `documentElement.scrollHeight` is inflated by decorative/absolute elements overflowing
     `<html>` (e.g. 1597 vs 1087 real) → measure `body.scrollHeight` for sections (chrome
     keeps measuring its single element to avoid its hidden mobile menu inflating height).
- **Placeholder image generation** — a custom Wagtail image model has `width` NOT NULL; set
  `img.width/height/file_size` after `file.save(…, save=False)`.
- **LinkBlock over-fill** — synth filled every destination (page + url + document +
  relative), which fails `LinkBlock.clean()`; fill exactly one (a relative path) + label.

---

## 6. Settings reference

All optional. With nothing set it enables any model with a `body` StreamField and renders
previews unstyled.

| Setting | Default | Purpose |
|---|---|---|
| `PRBLM_BUILDER_PREVIEW_CSS` | `[]` | Front-end CSS loaded in preview frames (static paths or URLs) |
| `PRBLM_BUILDER_PREVIEW_JS` | `[]` | Front-end JS loaded in preview frames |
| `PRBLM_BUILDER_PREVIEW_BODY_CLASS` | `""` | Class on the preview `<body>` |
| `PRBLM_BUILDER_HEADER_TEMPLATE` | `""` | Site header template shown atop the canvas |
| `PRBLM_BUILDER_FOOTER_TEMPLATE` | `""` | Site footer template shown below the canvas |
| `PRBLM_BUILDER_FIELD_NAMES` | `("body",)` | StreamField name(s) to build, priority order |
| `PRBLM_BUILDER_PAGE_MODELS` | `None` | `None` = auto-detect; or `["app.Model", …]` |
| `PRBLM_BUILDER_DEMO` | `True` | The admin-only Block library |
| `PRBLM_BUILDER_EXCLUDE_TEMPLATE_PREFIXES` | `()` | Block template prefixes to hide |
| `PRBLM_BUILDER_INDEX_SCAN_LIMIT` | `500` | Pages/model scanned for real demo content |
| `PRBLM_BUILDER_EXCLUDE_BLOCKS` | `()` | Hide blocks by name or dotted class path (0.2) |
| `PRBLM_BUILDER_LIBRARY_SCOPE` | `"builder"` | Block library = palette blocks, or `"all"` StreamFields (0.2) |
| `PRBLM_BUILDER_SEED_NEW_BLOCKS` | `True` | `False` = new blocks start empty (0.2) |
| `PRBLM_BUILDER_CANVAS_WIDTH` | `1280` | Desktop width sections render at on the canvas (0.2) |
| `PRBLM_BUILDER_PLACEHOLDER_IMAGES` | `True` | Allow creating placeholder images (0.2) |
| `PRBLM_BUILDER_ADMIN_TWEAKS` | `True` | Full-width tab + header link (Wagtail internals) (0.2) |

A block can also opt out itself: `class Meta: builder = False`.

---

## 7. Known limitations / version coupling

- Some editor-chrome niceties hook into **Wagtail admin internals** and are the most likely
  to need attention on a new Wagtail version (they all degrade gracefully — the feature just
  doesn't activate):
  - full-width canvas: `.w-form-width`, `.editor-view.side-panel-open`;
  - header "Block library" link: `[data-side-panel-toggle]`;
  - ride-along save's hidden-field injection: `form[data-edit-form]`.
- Built against Wagtail 7 / Django 5.2; from v0.1.0 it targets **Wagtail 8.1+ / Django 6.1+ /
  Python 3.12+** (CI covers Python 3.12–3.14).
- The test suite (`prblm_builder/tests/test_builder.py`) runs against the bundled test
  project (`python runtests.py`) or inside a host project (`manage.py test prblm_builder`).
- The Layout tab reads sections from the page's stored (live) row, not the latest draft
  revision — unverified whether a page with unpublished draft changes shows stale
  sections on the canvas. Check when testing in a second project.

---

## 8. File map

```
prblm_builder/
  apps.py            AppConfig.ready() → integration.autoenable()
  integration.py     auto-attach the Layout tab + base_form_class to enabled models
  panels.py          LayoutBuilderPanel (embeds the builder in the Layout tab)
  forms.py           LayoutBuilderForm (reconciles the arrangement on save)
  layout.py          reconcile(stream_block, current_raw, layout, initial_ids)
  registry.py        block/model introspection
  views.py           builder, builder_new, preview, demo, save, page_preview
  previews.py        demo content engine: real_instance_for, synth_value, trim_for_demo, frame
  settings.py        PRBLM_BUILDER_* readers (all optional)
  wagtail_hooks.py   admin URLs, Settings menu item, page-header buttons
  templates/prblm_builder/  builder.html, layout_panel.html, demo.html
  static/prblm_builder/     builder.css, builder.js, vendor/sortable.min.js
  tests/test_builder.py     integration + reconcile unit tests
```

---

## 9. Roadmap / next steps

1. ~~**Demo project + CI**~~ — done in v0.1.0 (`tests/`, `runtests.py`, GitHub Actions).
2. ~~**LICENSE**~~ — MIT, v0.1.0.
3. **Version-proof the admin-chrome features** — feature-detect the Wagtail internals above
   and add a setting to disable the DOM-injection bits; document supported versions.
4. **HTTP-level test** for the ride-along save (hidden field → form `clean`), not just the
   `reconcile` unit tests.
5. **Optional default-content editor** — an admin UI to override each block's demo/default
   content (synthesis stays the fallback). This was scoped but deferred.
6. **Publish to PyPI** so other projects `pip install prblm-builder`.
7. **Install into another Wagtail project** to shake out the version-specific chrome bits.
