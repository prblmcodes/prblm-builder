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
- `all_blocks()` / `grouped_all_blocks()` / `find_block(name)` — the Block library's
  catalogue. Scope is `PRBLM_BUILDER_LIBRARY_SCOPE`: `"builder"` (default, since 0.2) =
  the top-level blocks of the builder-enabled page fields, i.e. exactly the palette;
  `"all"` = top-level blocks of every StreamField in the project.
- `hidden(name, block)` — the project asked to keep a block out: its own
  `Meta: builder = False`, or `PRBLM_BUILDER_EXCLUDE_BLOCKS` (name, or dotted class path
  matched with `isinstance`; a path that doesn't import is ignored).
- `previewable(name, block)` — has its own template, isn't `hidden`, and isn't under
  `PRBLM_BUILDER_EXCLUDE_TEMPLATE_PREFIXES` (e.g. email-only blocks). Applies to both the
  palette and the library.

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
  - new blocks get `layout.new_block_value()` — demo content. (0.2 had a setting to
    start them empty; removed in 0.3 — see the journey.) The canvas flags sections whose
    stored value still equals their demo content as **"Not edited yet"**
    (`previews.is_unedited`);
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
  `?block=<name>` (unscoped) = demo content; `&fresh=1` = a section just added on the
  canvas (shows the empty value + a "New …" placeholder when seeding is off);
  `?chrome=header|footer` = the site header/footer, rendered with `page`/`self` when a
  `?page=` is given. Any `?page=` requires edit permission on that page; malformed
  `?page=` / `?model=` return 404.
- It's decorated `@xframe_options_sameorigin` because admin responses default to
  `X-Frame-Options: DENY`, which would blank the iframes.
- `previews.frame()` wraps the block HTML in a minimal document that loads the host's
  front-end CSS/JS (`PRBLM_BUILDER_PREVIEW_CSS/JS`) and **strips `loading="lazy"`** from
  images (see bug notes — lazy images never enter a scaled/offscreen frame).
- `builder.js` renders each section iframe at a **desktop width** (`PRBLM_BUILDER_CANVAS_WIDTH`,
  default 1280, passed as `data-canvas-width`; palette thumbnails use it too) and scales it
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
An admin-only page (`/admin/page-builder/demo/`) listing every previewable block grouped,
each with a live demo preview (same engine as the builder). Reachable from Settings →
*Block library* and a link injected into the editor header's top-right strip (that link
is an admin tweak — off with `PRBLM_BUILDER_ADMIN_TWEAKS = False`). Gated by
`PRBLM_BUILDER_DEMO`.

Since 0.2 the view test-renders each block server-side (`views._preview_problem`); blocks
that raise or render no text/media (`_is_blank`) are listed in a collapsed
"Couldn't preview" section with the reason instead of as an empty/red card. They stay in
the palette.

### Admin section — `wagtail_hooks.py`
A **Page builder** sidebar section (`SubmenuMenuItem`) whose items come from the
`register_prblm_builder_menu_item` hook: the core adds *Block library*; the blocks app
adds *Theme* and *Header & footer*. Items that depend on a setting use a `MenuItem`
subclass with `is_shown()` — Wagtail builds menus once, so returning `None` from the hook
would be cached forever.

### Built-in blocks — `prblm_builder/blocks/` (optional app, 0.3)
- **Opt-in app** `prblm_builder.blocks` (label `prblm_builder_blocks`); system checks
  require `wagtail.contrib.settings` and `prblm_builder`. The core never imports it.
- **21 blocks** in `sections/` (site, heroes, content, conversion, media, utility), sharing
  `sections/base.py`: `LinkBlock` (label + page *or* typed address, `.href`),
  `BackgroundBlock` (light/muted/dark/brand), `AnchorBlock`, `IconChoiceBlock`.
  `builder_blocks(exclude, only)` returns `[(name, block)]` for a StreamField.
- **Explanatory defaults** live in the blocks' own field defaults, so they appear when a
  block is added from the Layout tab *or* the Content tab. `previews.demo_value` returns
  `block.get_default()` for built-ins (never real-site content or synthesis).
- **Self-contained assets.** Every block template calls `{% prblm_assets %}`, which emits
  the stylesheet, the Theme's CSS variables and the small script **once per request**
  (flag on the request). `blocks.css` is scoped to `.pbk*` classes; colours/shape are
  `--pbk-*` variables. Font: `font-family: var(--pbk-font, inherit)` plus a
  zero-specificity `:where(html)` system-font fallback, so any site font wins.
- **Theme** (`ThemeSettings`, a Wagtail site setting) → `theme.css()` → `:root{--pbk-…}`;
  values are validated (hex colours, font lists stripped of `;{}<>\`).
- **Headers & Footers** (0.4; 0.3 had a single per-site `SiteChrome`): `SiteHeader` /
  `SiteFooter` snippet models (name, `is_default`, one block each, pre-filled), listed under
  Page builder. Canvas resolution lives in core `prblm_builder/chrome.py`:
  `prblm_builder_chrome_for_page` hooks first (the blocks app answers for Builder pages
  from the page's `header_choice`/`footer_choice`: default / custom / site template /
  none), then the template setting, then `prblm_builder_chrome` hooks (site default).
  `{% prblm_header %}` / `{% prblm_footer %}` follow the same rules; an optional name picks one.
- **Builder page extras** (0.4): `PRBLM_BUILDER_PAGE_PARENTS` appends BuilderPage to the
  listed types' `subpage_types` at startup (resetting Wagtail's `_clean_subpage_models`
  cache to `None`). `PRBLM_BUILDER_PAGE_EXTRA_BLOCKS` is applied through
  `BuilderBodyField`, whose `deconstruct()` always reports the built-ins only — so a
  site's extra blocks never trigger a migration in the installed package.
- **Builder page** (`BuilderPage`): all 21 blocks; renders a standalone HTML document
  (`builder_page.html`: site header, sections, site footer) so it works without any site
  templates; overridable by path. `PRBLM_BUILDER_PAGE_TYPE` sets `is_creatable` at startup.
- **Settings pages live under Page builder, not Settings:** registered with Wagtail's
  settings registry (edit view, per-site values, permissions) with names prefixed
  `prblm-builder-`; a `construct_settings_menu` hook removes them from Settings.
- **Images / icons:** `{% pbk_image %}` renders a rendition, or an inline SVG placeholder
  labelled with purpose and size; icons are inline SVG from `icons.py` (drawn for the
  plugin, no third-party licence).
- **Name clashes:** a site block and a built-in block can share a name (`hero`). The
  Block library and the real-content index key blocks by *(name, is_builtin)*; library
  previews of built-ins pass `&builtin=1`.

### Settings — `settings.py`
One small reader function per `PRBLM_BUILDER_*` setting, each with its default; the rest
of the code only calls these (never `django.conf.settings` directly). See §6.

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
10. **0.3 (see `plan.md` for the full plan + log)** — removed SEED_NEW_BLOCKS again (saving empty
    blocks made no sense; demo content + a "Not edited yet" badge is safer); added the
    "Page builder" admin section; built-in blocks app. Lesson: Wagtail builds admin
    menus once — a menu hook that returns `None` based on a setting is cached forever;
    use a `MenuItem` subclass with `is_shown()`.
11. **0.4 (plan in `plan.md`)** — feedback from a real project: save banner + "Save draft
    now" with a placeholder title, arrangement kept after a failed save; foldable groups;
    reusable Headers/Footers with per-Builder-page choice (data migration from 0.3);
    Builder page placement + extra blocks settings. Lessons: Wagtail's snippet add view
    builds forms without an instance, so a callable StreamField default reaches the widget
    raw (seed `form.initial` from a fresh instance); reset `_clean_subpage_models` to `None`,
    never delete it; browser-test JS flows with Playwright + system Chrome
    (`channel="chrome"`) against a throwaway dev server.
12. **0.5 (plan in `plan.md`)** — easier editing in the Layout tab: Wagtail `preview_value` /
    `description`; built-in links with a *Link to* switch (telepath `StructBlockDefinition`
    subclass, `link-block.js`); ⚙ section settings (`Meta.builder_settings`, core
    `BuilderSettingsMixin` → Wagtail 8.1 `form_layout` settings area; popover; `?settings=`
    preview override; only changed keys sent; validated per field in `reconcile`);
    same-page copy/paste + right-click menu; sidebar Sections | Page tabs
    (`prblm_builder_page_options` hook, `builder_layout_panels` hidden fields). Bugs found:
    the Layout tab used the **published row, not the latest draft** (the long-open question —
    fixed with `get_latest_revision_as_object()` everywhere); "Not edited yet" broke after a
    form save (`""` vs `None`, `data-block-key`). Lessons: block **default values are part
    of the migration description** (changing defaults needs a migration, unlike adding child
    fields to a StructBlock subclass); Wagtail 8.1 **auto-saves drafts** on form changes —
    Layout changes trigger it; hide a StructBlock child via its `data-contentpath` element.

---

## 4. Key decisions (and why)

- **Ride-along save over StreamField-JS editing.** Driving Wagtail's StreamField widget
  from the Layout tab would be fragile across versions. Instead the tab writes intent to
  hidden fields and the form reconciles on save — robust, and the Content tab stays the
  native editor. Trade-off: `body` is touched in two places, reconciled by id + the
  `_pb_initial` set.
- **Scaled iframes over a real-width canvas.** The editor column is far narrower than a
  page, so sections rendered their mobile layout. Rendering at desktop width (1280px by default, `PRBLM_BUILDER_CANVAS_WIDTH`) and CSS-scaling shows
  the true desktop layout in the available space. Wagtail's own Preview remains the
  full-size preview.
- **Real content first, synth as fallback.** A real instance carries real images + copy and
  its page context, which fixes empty hero bands and missing images in one move. Synthesis
  covers blocks used nowhere yet.
- **Auto-attach from `ready()` over a mixin.** Host projects shouldn't have to edit each
  page model. Defensive so it can never break the admin.
- **Select blocks by how they're used, not by where their files live (0.2).** Every
  Wagtail project shares one structure: a page's StreamField lists the top-level
  sections; fragments (links, buttons) live inside them. So "a section" = a top-level
  block of a builder-enabled page field. Path-based rules (template prefixes) are too
  project-specific; the opt-out lives on the block (`Meta: builder = False`) or by class.
- **Built-in blocks as an opt-in app, not part of the core (0.3).** The plugin's main
  value is working with a site's *own* blocks; the starter blocks are a convenience for
  new sites and demos. Keeping them in a separate app means sites that don't want them
  get no extra tables, menus or page types.
- **Self-contained styling over Tailwind/Bootstrap (0.3).** Built-ins must look right on
  any site without a build step and without fighting the site's CSS: prefixed classes,
  CSS variables, assets emitted by the blocks themselves.
- **Site-wide header/footer via a hook (0.3).** The core shows a canvas header/footer but
  can't know about the blocks app; a hook keeps the dependency one-way.
- **No settings for where models/templates/static live.** Django's app registry,
  template loaders and staticfiles finders already find them uniformly; settings for
  paths would only add ways to misconfigure. Settings cover *which* and *how*, not *where*.

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
- **Empty block showed "None"** (0.2) — `block.get_default()` for a CharBlock is `None`,
  which a template renders as the text "None". An empty new block must use what
  Wagtail's editor saves for a blank field: `field.to_python("")` → `""`, recursing into
  nested StructBlocks (a nested struct's default is a StructValue full of `None`s).

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
| ~~`PRBLM_BUILDER_SEED_NEW_BLOCKS`~~ | — | Removed in 0.3 (startup warning W001 if still set) |
| `PRBLM_BUILDER_PAGE_TYPE` | `True` | Built-in "Builder page" creatable (0.3, blocks app only) |
| `PRBLM_BUILDER_PAGE_PARENTS` | `[]` | Page types allowed to hold Builder pages (0.4) |
| `PRBLM_BUILDER_PAGE_EXTRA_BLOCKS` | `None` | Site blocks on the Builder page, no migration (0.4) |

Block-level options (not settings): `Meta.builder = False` (hide), `Meta.builder_settings =
[...]` (⚙ panel, 0.5), Wagtail's `preview_value` / `description` (0.5). Model attribute:
`builder_layout_panels` (hidden Layout-tab fields for the Page tab, 0.5).
| `PRBLM_BUILDER_CANVAS_WIDTH` | `1280` | Desktop width sections render at on the canvas (0.2) |
| `PRBLM_BUILDER_PLACEHOLDER_IMAGES` | `True` | Allow creating placeholder images (0.2) |
| `PRBLM_BUILDER_ADMIN_TWEAKS` | `True` | Full-width tab + header link (Wagtail internals) (0.2) |

A block can also opt out itself: `class Meta: builder = False`.

---

## 7. Known limitations / version coupling

- Some editor-chrome niceties hook into **Wagtail admin internals** and are the most likely
  to need attention on a new Wagtail version (they all degrade gracefully — the feature just
  doesn't activate). All present in Wagtail 8.1:
  - full-width canvas: `.w-form-width`, `.editor-view.side-panel-open` *(admin tweak)*;
  - header "Block library" link: `[data-side-panel-toggle]` *(admin tweak)*;
  - ride-along save's hidden-field injection: `form[data-edit-form]` *(essential — not
    switchable)*.
  The two admin tweaks can be turned off with `PRBLM_BUILDER_ADMIN_TWEAKS = False`.
- Built against Wagtail 7 / Django 5.2; from v0.1.0 it targets **Wagtail 8.1+ / Django 6.1+ /
  Python 3.12+** (CI covers Python 3.12–3.14).
- Tests: `prblm_builder/tests/test_builder.py` (generic, shipped — runs in the bundled
  test project or inside a host project via `manage.py test prblm_builder`) and
  `tests/test_options.py` (settings + Block-library rules; needs the edge-case blocks in
  `tests/testapp`, so it only runs in this repo). `python runtests.py` runs both.
- "Not edited yet" can miss a section seeded from real site content that has since
  changed (shows as edited); it never flags a section an editor actually changed.
- ~~The Layout tab read the published row instead of the latest draft~~ — confirmed and
  fixed in 0.5 (it now works on the latest revision, like Wagtail's editor).

---

## 8. File map

```
prblm_builder/                the installable app (what the wheel ships)
  apps.py            AppConfig.ready() → integration.autoenable()
  integration.py     auto-attach the Layout tab + base_form_class to enabled models
  panels.py          LayoutBuilderPanel (embeds the builder in the Layout tab)
  forms.py           LayoutBuilderForm (reconciles the arrangement on save)
  layout.py          reconcile(…), new_block_value(), empty_value()
  registry.py        block/model introspection; hidden(), previewable(), library scope
  views.py           builder, builder_new, preview, demo, save, page_preview
  previews.py        demo content engine: real_instance_for, synth_value, trim_for_demo, frame
  settings.py        PRBLM_BUILDER_* readers (all optional)
  wagtail_hooks.py   admin URLs + "Block library" Settings menu item
  templates/prblm_builder/  builder.html, layout_panel.html, demo.html
  static/prblm_builder/     builder.css, builder.js, vendor/sortable.min.js
  tests/test_builder.py     generic integration + reconcile tests
tests/                        test project (repo only, not shipped)
  settings.py, urls.py      minimal Wagtail settings
  testapp/                  StandardPage (+ opted-out, broken, empty and link blocks),
                            FooterSettings (a non-page StreamField)
  test_options.py           settings + Block-library rule tests
runtests.py                   test runner (also `runtests.py makemigrations`)
.github/workflows/test.yml    CI: Python 3.12–3.14 + wheel build check
README.md                     user docs: install, settings reference, troubleshooting
CHANGELOG.md                  per-release changes
LICENSE                       MIT
plan.md                       the v0.3.0 plan + progress log

prblm_builder/blocks/         optional built-in blocks app (0.3)
  __init__.py        builder_blocks()
  apps.py, checks.py app config; requires wagtail.contrib.settings
  sections/          base.py (shared blocks) + site, heroes, content, conversion, media, utility
  models.py          ThemeSettings, SiteChrome, BuilderPage (+ migrations/0001_initial.py)
  theme.py, chrome.py, icons.py
  templatetags/prblm_blocks.py   prblm_assets, prblm_header/footer, pbk_icon/image/placeholder
  templates/prblm_builder/blocks/  section.html base, _link/_heading partials, one per block,
                                   builder_page.html
  static/prblm_builder/blocks/     blocks.css, blocks.js
  wagtail_hooks.py   menu items, hide from Settings, prblm_builder_chrome provider
tests/test_blocks_foundation.py, test_blocks.py, test_site_chrome.py, test_builder_page.py
```

**Checking the look.** Tests can't see layout, so CSS was checked by rendering every
block's default content into one HTML file and screenshotting it with headless Chrome at
1280px and 390px (`google-chrome --headless=new --screenshot … --window-size=1280,7600`).

---

## 9. Roadmap / next steps

1. ~~**Demo project + CI**~~ — done in v0.1.0 (`tests/`, `runtests.py`, GitHub Actions).
2. ~~**LICENSE**~~ — MIT, v0.1.0.
3. **Version-proof the admin-chrome features** — ~~setting to disable the DOM-injection
   bits~~ (`PRBLM_BUILDER_ADMIN_TWEAKS`, 0.2). Still to do: feature-detect the internals
   instead of relying on them silently failing.
4. **HTTP-level test** for the ride-along save (hidden field → form `clean`), not just the
   `reconcile` unit tests.
5. **Optional default-content editor** — an admin UI to override each block's demo/default
   content (synthesis stays the fallback). This was scoped but deferred.
6. **Publish to PyPI** so other projects `pip install prblm-builder`.
7. ~~**Install into another Wagtail project**~~ — done after 0.1.0; led to the 0.2 changes.
   Still to verify there: whether the Layout tab shows a page's unpublished draft
   sections (it reads the live row — see §7).
8. ~~**Optional built-in blocks**~~ — done in 0.3 (21 blocks, Theme, Header & footer,
   Builder page). Possible next: more blocks (contact form needs storage + spam
   protection), a theme preview on the Theme page, dark-mode aware defaults.
