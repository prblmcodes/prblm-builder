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
- There is no other save path: the standalone (non-embed) builder and its `views.save`
  endpoint were removed in 0.9 (the address redirects to the page editor).

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
- `previews.frame(html, request, page=None, site=None)` wraps the block HTML in a page:
  either the site's own **preview template** (`PRBLM_BUILDER_PREVIEW_TEMPLATE` / the site's
  `template`, section inserted as `{{ prblm_section }}` between
  `<template data-prblm-start/end>` markers) or a minimal shell with the configured CSS / JS
  (`css_tags` / `js_tags`: strings or dicts with `defer`, `type`, `integrity`, inline code,
  import maps) and body class. The shell forces `html,body{height:auto}`. It **strips
  `loading="lazy"`** (lazy images never enter a scaled/offscreen frame). Static paths are
  root-relative (`/static/…`): Wagtail's own preview uses a fake request with the Site's
  host. Which CSS / template applies comes from `sites.config(page, request, site)`
  (global settings, overridden per Wagtail Site by `PRBLM_BUILDER_PREVIEW_SITES`).
- `frames.js` (`prblmFrames.measure(doc, chrome)`) measures the visible, in-flow elements
  of a frame (or those between the markers), margins included; skips `link`/`style`/
  `script`, hidden and absolutely positioned elements; counts a **fixed** element only for
  a header/footer at the top of the frame; looks inside zero-size wrappers. Returns
  `{top, height, mt, mb, collapse}`: `mt` / `mb` are the section's outer margins as the
  page sees them (`edgeMargin` follows first / last children whose margins collapse
  through the section's edge), `collapse` whether its container lets them merge (not a
  flex / grid wrapper). `builder.js` `applyGaps()` overlaps each host (header → sections →
  footer) with the previous by `min(prev.mb, mt)` × scale (0.8). Since 0.9 margins merge the
  CSS way (`edgeMargins`: largest positive + most negative), and `measure` also returns
  `above` / `below` (how far in-flow content — negative margins, nested "pokes" found by
  `pokes()`, skipping absolute/fixed and overflow-clipped things — reaches over the previous /
  next section), `rawTop` (content above the document's top; `measureFrame` pads `<html>` so
  it's never cut off) and, for headers, `overlay` (a fixed/absolute header with no
  background of its own or of a full-width bar inside it). With
  `PRBLM_BUILDER_CANVAS_OVERLAP` (per site: `canvas_overlap`), `applyGaps` pulls a host up by
  `prev.below + this.above` (a transparent header: by its whole height, over the first
  section), and `setClear` makes the frame see-through (its `html,body` background moves to
  the host as a gradient that is transparent over the overlapping strips); a host reaching
  down gets `z-index:2` (`pb-pokes-down`), below the toolbars (3). Every preview `<html>` has
  `prblm-canvas` (shell: attribute; template mode: an inline script at the start of
  `prblm_section`), plus the reduce-motion `<style>` when `PRBLM_BUILDER_REDUCE_MOTION`.
- `builder.js` renders each frame at a **desktop width** (`PRBLM_BUILDER_CANVAS_WIDTH`) and a
  viewport at least `PRBLM_BUILDER_CANVAS_HEIGHT` tall (so `vh` resolves like a real screen),
  scales it to the column (`fitFrame`), shifts it by `top` and sets the host's height to the
  measured part. It re-fits until stable, and on size changes, image loads, web fonts and
  DOM mutations (throttled). An empty header/footer frame collapses (`pb-chrome-empty`).
  The Block library uses the same measuring.

### Demo content engine — `demo.py` (0.7)
`demo.build(block, name, real=True) -> (value, page)`, used for new sections
(`layout.new_block_value`), canvas / thumbnail / library previews and the ⚙ defaults.
Built-in blocks keep their own explanatory `default`. For every other block, **per field**
(`_pick`, recursing through Struct / List / Stream blocks):
1. **`preview_value`** as the developer wrote it (`block.meta.preview_value`, may be partial).
2. **Real content** — `real_instance(name, block)`: the best-filled instance of the same
   block (`registry.block_key`: the class path; Wagtail's generic classes fall back to the
   name) on **live** pages, skipping sections the plugin seeded and nobody changed, and
   only if it passes `clean()`. Also returns its page (context for blocks reading page
   fields). The index (`_index`, `PRBLM_BUILDER_INDEX_SCAN_LIMIT` pages/model; 0.7–0.9 cached it
   60s, since 0.10 `_cached(key, fn, depends=…)` rebuilds only when a stamp changes — live
   page count + newest `last_published_at`, SeededSection / image / document count + max
   id, each checked at most every `STAMP_EVERY` = 2s per process)
   also gives `usage(name, block)` for the Block library. Empty fields fall through.
3. **The field's default** (a `ListBlock`'s made-up default of empty items doesn't count).
4. **Generated** (`generate`): neutral text from help text (when it's a short name for the
   field) or label, sized by block type / `max_length`, numbered in lists; images by role
   (`_image_role`: wide / square / photo) and shape from the library (`_image_catalog`:
   size, SVG, transparency), else a role-shaped placeholder in the "Builder placeholders"
   collection; link-like structs (`_link_choice`: a ChoiceBlock whose choices name sibling
   destination fields) get one type + its value (a live page, else `/`); lists 3 items or
   `min_num`, ≤ `max_num`; required documents a PDF / any / an example file.
Then `validated()` runs `clean()`; failing fields fall back (generated → a common shape
that passes a pattern, `PATTERN_CANDIDATES` via `_pattern_value` (0.9) → empty → the
struct's dropdowns reset). Real instances are ranked by `_score` = (filled fields incl.
nested, images, stored length) (0.9; was length only). `problem()` names the failing field for the Block library.

**Seeded sections.** (0.9.1: `cleanup.py` — a page's `pre_delete` collects its section ids
from content and all revisions and, on commit, removes the records no other page or revision
still contains (`icontains` on StreamFields and `Revision.content`; a copied page keeps the
ids); `manage.py prblm_builder_cleanup` does it for all records.) `layout.reconcile` records each seeded section (and copies of untouched
ones) in `SeededSection(section_id, value_hash)` — `content_hash` ignores ⚙ settings, ids and
rich-text keys. `previews.is_unedited` compares against the recorded hash; sections seeded
before 0.7 fall back to `legacy_unedited` (default / preview value / 0.6's generator, kept in
`previews.py` only for this).

**Trim for display** — `previews.trim_for_demo()` shortens long rich text (~80 words) and
text (~360 chars) for the Block library and palette thumbnails (`&trim=1`). The canvas shows
a new section untrimmed — exactly what's saved.

### Block library (demo page) — `views.demo` + `demo.html`
An admin-only page (`/admin/page-builder/demo/`) listing every previewable block grouped,
each with a live demo preview (same engine as the builder). Reachable from Settings →
*Block library* and a link injected into the editor header's top-right strip (that link
is an admin tweak — off with `PRBLM_BUILDER_ADMIN_TWEAKS = False`). Gated by
`PRBLM_BUILDER_DEMO`.

Since 0.2 the view test-renders each block server-side (`views._preview_problem`); blocks
that raise, render no text/media (`_is_blank`) or whose demo content fails their own
validation (0.7) are listed in a collapsed "Couldn't preview" section with the reason
instead of as an empty/red card. They stay in the palette. Since 0.7 each card shows
"Used on N pages" (live pages, `demo.usage`) with an All / Used / Not used filter; search
covers descriptions; with several Wagtail Sites (0.9: only then) the **Preview as** tabs
(`sites.library_choices()`, a dropdown above `SITE_TABS_MAX` = 5) add `&site=<hostname>` to
the previews and scope usage. Blocks and groups are ordered by usage (`registry.order_by_usage`,
`PRBLM_BUILDER_BLOCK_ORDER`), also in the Layout sidebar (`views._palette(stream_block, site)`,
the page's site on multi-site projects).

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
10. **0.3 (plan in `docs/plans/v0.3.0.md`)** — removed SEED_NEW_BLOCKS again (saving empty
    blocks made no sense; demo content + a "Not edited yet" badge is safer); added the
    "Page builder" admin section; built-in blocks app. Lesson: Wagtail builds admin
    menus once — a menu hook that returns `None` based on a setting is cached forever;
    use a `MenuItem` subclass with `is_shown()`.
11. **0.4 (plan in `docs/plans/v0.4.0.md`)** — feedback from a real project: save banner + "Save draft
    now" with a placeholder title, arrangement kept after a failed save; foldable groups;
    reusable Headers/Footers with per-Builder-page choice (data migration from 0.3);
    Builder page placement + extra blocks settings. Lessons: Wagtail's snippet add view
    builds forms without an instance, so a callable StreamField default reaches the widget
    raw (seed `form.initial` from a fresh instance); reset `_clean_subpage_models` to `None`,
    never delete it; browser-test JS flows with Playwright + system Chrome
    (`channel="chrome"`) against a throwaway dev server.
12. **0.5 (plan in `docs/plans/v0.5.0.md`)** — easier editing in the Layout tab: Wagtail `preview_value` /
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

13. **0.6 (plan in `docs/plans/v0.6.0.md`) — Layout first, tabs in sync, two-column forms, examples.** The Layout tab
    is inserted first. Tab sync: ⚙ ↔ Content-tab inputs via `<field>-N-id` /
    `<field>-N-value-<name>`; after structure changes on a saved page, opening Content waits
    for `w-autosave:success` and reloads onto `#tab-content`; opening Layout after Content
    edits refreshes the previews. `form-columns.js/.css` (global admin hooks) lay out forms
    marked `pbk-form` (built-in blocks' `form_classname`, Theme `MultiFieldPanel`
    classname). `docs/EXAMPLES.md` mirrors `tests/examples/`. Lessons: with Layout first the
    iframe loaded at once and wrote hidden fields → an auto-saved draft on every open (now
    only after a real change); the panel script ran before the Content tab was parsed (wait
    for DOMContentLoaded); `form_classname` **replaces** `struct-block`; `.w-field` is
    inline-block (stretch it); an empty ListBlock has no `[data-contentpath]` children;
    model-form field panels contain their own `[data-contentpath]`.
    Feedback round before release: the two-column layout moved to **CSS** (`:has()` for
    long / grouped fields, container queries for narrow forms) because the JS version
    flickered (one field per row for ~100 ms on each new block); JS only marks unpaired
    fields, straight from a MutationObserver + ResizeObserver (a window `resize` fires
    while Wagtail's sidebar is still animating). The setting became the boolean
    `PRBLM_BUILDER_SITE_BLOCK_COLUMNS` (`True` used to mean "builtin" — confusing). The
    sidebar stopped remembering the Page tab. **CSS isolation:** blocks.css was already
    scoped to `.pbk…`; the other direction is a shield — `.pbk :where(*:not(svg, svg *))
    {all:revert}` (+ `.pbk:where(*)` for the root) at one class of specificity *before* the
    block rules — checked by screenshotting all 21 blocks with and without a hostile site
    stylesheet (Tailwind preflight + global element rules): identical, and identical to
    before. SVG is excluded because `revert` drops presentation attributes. Builder pages
    load the site's CSS/JS only when needed (`chrome.needs_site_assets`). Canvas assets got
    `?v=<version>` (`{% prblm_static %}`).
    **Fixes from testing on a real site** (plan `docs/plans/v0.6.0-fixes.md`): the site's
    CSS/JS were linked with `build_absolute_uri`, and Wagtail's preview request carries the
    Site record's host (`localhost:80`) → unstyled header/blocks in the preview panel; now
    root-relative (`previews.asset_urls`). The canvas trimmed a new section's text while the
    full text was saved → trim only with `&trim=1` (library, thumbnails). Header frames were
    sized from `body.firstElementChild` = the built-in header's `<link>` (0px → 150px
    default) → `chromeHeight()`. Blocks were keyed by **name** everywhere (real-content
    index, library dedupe) — a site block added to the Builder page as `hero1` (vs
    `hero_section_home` on HomePage) got generated demos, empty snippets, no thumbnail and a
    duplicate library entry → `registry.block_key` (class path; Wagtail's generic classes
    fall back to the name). Generated demos failed third-party validation
    (wagtail-link-block's hidden `custom_url` has a URL validator: no visible error, page
    didn't save) → `synth_demo` validates and empties failing fields; URL/phone/anchor
    fields and snippet choosers get sensible values. Reproduced on a sandbox copy of the
    host site's DB (never the real one).

14. **0.7 (plan in `docs/plans/v0.7.0.md`) — safe demo content, previews that match the
    site, editor polish.** From testing 0.6 in a multi-site project (Tailwind + Alpine, fixed
    header, ~30 StructBlocks, wagtail-link-block). **Demo content** moved to `demo.py` and
    is chosen **per field**: partial `preview_value` → real content of the same block class
    from **live** pages (skipping the plugin's own untouched demo sections, validated) →
    field default → neutral generated text sized by field type / `max_length`, role-based
    images (wide raster for banners, square / SVG / transparent for logos; placeholders of
    the right shape in a "Builder placeholders" collection), one consistent link per
    link-like struct (a ChoiceBlock whose choices name sibling fields), list sizes from
    `min_num` / `max_num`; then `clean()` with per-field fallback. **`SeededSection`** (the
    core app's first model) records each seeded section's content hash: "Not edited yet"
    and the no-self-borrowing rule use it; 0.6 seeds fall back to comparing with 0.6's
    generator (kept in `previews.py` for that only). **Previews:** shared `frames.js`
    measures visible in-flow children (fixed elements count for chrome at the top; zero-size
    wrappers are looked into), frames keep a `PRBLM_BUILDER_CANVAS_HEIGHT` viewport (vh) and
    the host clips to the measured part (translateY when a preview template adds space
    around the section — `<template data-prblm-start/end>` markers); empty chrome hides; refit
    on images / fonts / DOM changes. `sites.py` = per-site settings; `PREVIEW_TEMPLATE`
    renders sections inside the site's own base template; dict entries for CSS/JS. Builder
    pages pad `<main>` by a fixed header's height. **Editor:** drop-in-place isn't a change;
    ⚙ number inputs + as-you-type checks (`check-setting/` endpoint); no empty choice with a
    default; publish warning for "Untitled page N"; Block library used / not-used filter and
    "Used on N pages"; forms one column below 720px. Lessons: Wagtail gives a `ListBlock` a
    made-up default (one item of empty fields) — treat an all-blank default as none; a site
    rule `html,body{height:100%}` made every section as tall as the frame once frames kept a
    tall viewport (the plain shell forces `height:auto`); a built-in header frame starts
    with its `<link>` (measure visible children, not the first one).

15. **0.8 (plan in `docs/plans/v0.8.0.md`) — follow-up from the same multi-site project.**
    0.7 worked there with settings + preview templates + the chrome hook alone. Added:
    margin merging between canvas sections (the last visible difference: margins added up
    instead of collapsing — `edgeMargin` + `applyGaps`, skipped inside flex/grid wrappers);
    the `prblm-canvas` marker and `PRBLM_BUILDER_REDUCE_MOTION` (scroll-reveal never fires in
    a scaled, unscrolled frame); `body_attrs` / `html_attrs` (global + per profile, also on
    Builder pages; ignored in template mode); `PREVIEW_SITES` keys by site name and wildcard
    with a fallback warning (hostnames differ per environment); a release workflow that
    attaches the wheel to the GitHub release; `docs/PREVIEWS.md`, the setup walkthrough the
    tester had to work out alone. Second round before release: previews make links / forms
    inert (`INERT_LINKS_JS`, default action only — script handlers still run); the
    selected section shows its margins as bands (`drawSpace`); kind pills (All · Built-in ·
    Your site's) in both sidebars, search ignores them; Block library card header grey with
    usage top-right; the Site switcher appears with any multi-Site project and scopes
    `demo.usage(…, site)` (+ "All sites"); `chrome.source()` tells the Page tab where the
    canvas's header/footer really comes from — it used to name the template setting even
    when a page type's `prblm_builder_chrome_for_page` hook decided (a landing page with
    its own header), sending editors to the wrong file.

16. **0.9 (plan in `docs/plans/v0.9.0.md`) — installed on an existing Wagtail 7.0 / Django
    5.2 site.** It needed four patches there: a Wagtail 8.1-only import (`BlockGroup`), the
    telepath module path, and a migration depending on Wagtail 8's `0098_apitoken` and
    reading `settings.WAGTAIL_PAGE_MODEL`. The package pinned `wagtail>=8.1` and
    `Django>=6.1` because those were the latest versions, not because the code needed them
    — the test suite passed on 7.0 with the patches (and on 6.3 except description /
    preview_value). Now: `compat.py`, migrations on `0094_alter_page_locale`, `wagtail>=7.0,<9`
    only, CI on 7.0, a test guarding migration dependencies. Lesson: **pin the oldest
    version you test, not the newest you have**, and lower `makemigrations`' wagtailcore
    dependency by hand. Canvas: transparent headers and negative-margin overlaps (above) —
    the real site's white header text vanished on the canvas strip and "pull-up" boxes lost
    their headings; the root bug was `edgeMargin` merging with `max()`, which drops a
    negative margin. Also: usage order, Preview-as tabs only with 2+ Sites, `"all"` scope = page types only,
    `request.is_prblm_preview` for analytics tags, pattern-shaped demo values. Removed the
    leftover standalone builder (own Save + "new tab" view, unlinked since 0.2) — one save
    path only. A "refresh demo content" action for untouched sections was built and dropped
    before release: sections already on a page may hold real content, so nothing refills
    them. Lesson from the same round: renaming `measure` → `measureFrame` in `builder.js`
    missed the thumbnail code, whose `try/catch` hid the ReferenceError — a test now checks
    the name.

17. **0.10 (plan in `docs/plans/v0.10.0.md`).** Publishing an "Untitled page N" "did
    nothing": the check used `window.confirm()`, which browsers answer "Cancel" silently once
    "don't allow more dialogs" is ticked — now an in-page question (Rename it / Publish
    anyway). Layout being the first tab meant every save reopened Layout: the current tab
    is stored at submit (sessionStorage) and set as the URL hash by an inline script in the
    Layout panel *before* Wagtail's tabs start (no flash). The Content tab is covered
    ("Loading the new sections…") from the moment it's shown until the reload, instead of
    showing stale sections. Canvas: padding bands (`measure().pad`, green) next to the
    margin bands; a "N sections still have demo text — Fill them in" bar. Decided to keep
    demo content to published pages only (drafts can be unfinished / private). The
    60-second cache of real content (rebuilt by the next request after a minute, per
    process, even when nothing changed) became change-based: a cheap stamp query (≤ every
    2s) and a rebuild only after a publish / unpublish / delete — new content shows at
    once, quiet sites never rescan. A stored per-page index (updated on publish) was
    considered for very large sites and left for later. Content → Layout sync only reloaded
    existing frames (sections added / deleted in the Content tab never appeared) and did
    nothing without auto-save: now a fingerprint of the stream's form fields detects any
    Content-tab change; with auto-save the canvas waits for an auto-save that finished after
    the last edit (an earlier one — e.g. of a deleted block — can miss a later text edit),
    clears the form's `_pb_layout` (so an old order can't override the Content tab) and
    reloads; without auto-save a bar asks to save.

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
     `<html>` (e.g. 1597 vs 1087 real) → measure `body.scrollHeight` for sections.
  4. Header/footer frames: measuring `body.firstElementChild` hit the built-in headers'
     leading `<link>` (height 0) and fell back to the 150px default — a gap under the
     header. `chromeHeight()` takes the bottom of the visible, in-flow children (skipping
     `link`/`style`/`script` and absolute/fixed elements such as a mobile-menu panel).
- **Wagtail's preview uses a fake request** with the Site record's hostname / port
  (`make_preview_request`), not the browser's address. Anything built with
  `request.build_absolute_uri` (we did for the site's CSS / JS) points at the wrong server
  there → link static files root-relative (`previews.asset_urls`).
- **Blocks are identified by class, not name** — sites reuse one block under several names
  (HomePage `hero_section_home`, Builder page `hero1`); keying demo content and the Block
  library by name gave different demos, empty snippets, missing thumbnails and duplicates.
- **Third-party blocks validate things we can't see** (wagtail-link-block's hidden
  `custom_url` has a URL validator) → synthesised demo values go through the block's own
  `clean()` and failing fields are emptied; otherwise the page silently fails to save on a
  field that block's own JS hides.
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
| `PRBLM_BUILDER_LIBRARY_SCOPE` | `"builder"` | Block library = palette blocks, or `"all"` page types' StreamFields (0.2; page types only 0.9) |
| ~~`PRBLM_BUILDER_SEED_NEW_BLOCKS`~~ | — | Removed in 0.3 (startup warning W001 if still set) |
| `PRBLM_BUILDER_PAGE_TYPE` | `True` | Built-in "Builder page" creatable (0.3, blocks app only) |
| `PRBLM_BUILDER_PAGE_PARENTS` | `[]` | Page types allowed to hold Builder pages (0.4) |
| `PRBLM_BUILDER_PAGE_EXTRA_BLOCKS` | `None` | Site blocks on the Builder page, no migration (0.4) |
| `PRBLM_BUILDER_CANVAS_WIDTH` | `1280` | Desktop width sections render at on the canvas (0.2) |
| `PRBLM_BUILDER_PLACEHOLDER_IMAGES` | `True` | Allow creating placeholder images (0.2; role-shaped, own collection 0.7) |
| `PRBLM_BUILDER_ADMIN_TWEAKS` | `True` | Full-width tab + header link (Wagtail internals) (0.2) |
| `PRBLM_BUILDER_SITE_BLOCK_COLUMNS` | `False` | Two-column forms for the site's own blocks too (0.6; built-ins always) |
| `PRBLM_BUILDER_CANVAS_HEIGHT` | `900` | Viewport height preview frames keep at least, for `vh` sizes (0.7) |
| `PRBLM_BUILDER_PREVIEW_TEMPLATE` | `""` | Site template previews render sections inside (`{{ prblm_section }}`) (0.7) |
| `PRBLM_BUILDER_PREVIEW_SITES` | `{}` | Per-Site overrides (css, js, body_class, body/html_attrs, header/footer_template, template); keys: host:port, host, site name, wildcard (0.7; matching 0.8) |
| `PRBLM_BUILDER_PREVIEW_BODY_ATTRS` | `{}` | Extra `<body>` attributes in the plain preview shell + Builder pages (0.8) |
| `PRBLM_BUILDER_PREVIEW_HTML_ATTRS` | `{}` | Extra `<html>` attributes (0.8) |
| `PRBLM_BUILDER_REDUCE_MOTION` | `True` | Animations / transitions instant under `.prblm-canvas` (0.8) |
| `PRBLM_BUILDER_CANVAS_OVERLAP` | `True` | Transparent header over the first section; negative-margin overlaps (0.9; per site `canvas_overlap`) |
| `PRBLM_BUILDER_BLOCK_ORDER` | `"usage"` | Sidebar + library order: most used first, or `"alpha"` (0.9) |

Block-level options (not settings): `Meta.builder = False` (hide), `Meta.builder_settings =
[...]` (⚙ panel, 0.5), Wagtail's `preview_value` / `description` (0.5). Model attribute:
`builder_layout_panels` (hidden Layout-tab fields for the Page tab, 0.5).

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
- Built against Wagtail 7 / Django 5.2; 0.1–0.8 required Wagtail 8.1+ / Django 6.1+. Since
  0.9: **Wagtail 7.0+ (<9), Django from Wagtail, Python 3.12+** (CI: Python 3.12–3.14 on the
  latest Wagtail, and Wagtail 7.0 / Django 5.2). Version-dependent imports live in
  `compat.py`; `BuilderSettingsMixin` needs 8.1's `form_layout` (no-op before); block
  `description` / `preview_value` need 6.4. New migrations must depend on
  `wagtailcore.0094` at most (`tests/test_v09.py` checks).
- Tests: `prblm_builder/tests/test_builder.py` (generic, shipped — runs in the bundled
  test project or inside a host project via `manage.py test prblm_builder`) and
  `tests/test_options.py` (settings + Block-library rules; needs the edge-case blocks in
  `tests/testapp`, so it only runs in this repo). `python runtests.py` runs both.
- "Not edited yet": exact for sections seeded by 0.7+ (recorded hash). For older ones it
  compares with what 0.6 could have seeded, so it can miss one (shows as edited); it never
  flags a section an editor actually changed.
- The canvas can't reproduce everything a live page does: sections are separate frames,
  so CSS that relies on neighbouring sections (`section + section`) or scripts reading the
  next section, and page-level JS state, look different. Negative-margin overlaps and
  transparent headers are reproduced since 0.9 (the header in its scroll-top state). A preview
  template (`PRBLM_BUILDER_PREVIEW_TEMPLATE`) covers `<body>` attributes and head scripts.
- Auto-save conflicts (`invalid_revision`, e.g. another tab saved first) can't be fixed by
  the plugin; the save banner says a manual Save draft is needed.
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
  layout.py          reconcile(…), new_block_value(); records seeded sections
  registry.py        block/model introspection; block_key; hidden(), previewable(),
                     library scope + origins; ⚙ settings schema + check_setting
  views.py           builder (Layout tab canvas; alone → redirect), builder_new, preview, demo, check_setting
  demo.py            demo content field by field; real-content index + usage; placeholders
  previews.py        frame (shell or preview template), css/js tags, trim, is_unedited,
                     0.6's generator (legacy "Not edited yet" only)
  sites.py           per-site preview settings (PRBLM_BUILDER_PREVIEW_SITES), Preview-as tabs
  compat.py          imports that differ between Wagtail versions (0.9)
  models.py          SeededSection (+ migrations/0001_seeded_sections.py)
  chrome.py          header/footer around the canvas (hooks → site template → default)
  mixins.py          BuilderSettingsMixin
  assets.py          installed version for ?v= on static URLs
  settings.py        PRBLM_BUILDER_* readers (all optional)
  wagtail_hooks.py   admin URLs, Page builder menu, form-columns assets, publish warning
  templates/prblm_builder/  builder.html, layout_panel.html, demo.html
  static/prblm_builder/     builder.css, builder.js, frames.js, fold.js, form-columns.*,
                            vendor/sortable.min.js
  tests/test_builder.py     generic integration + reconcile tests
tests/                        test project (repo only, not shipped)
  settings.py, urls.py      minimal Wagtail settings
  testapp/                  StandardPage (+ opted-out, broken, empty and link blocks),
                            FooterSettings (a non-page StreamField)
  test_options.py           settings + Block-library rule tests
  test_v05.py … test_v08.py   per-release behaviour (v07: demo chain, sites, template, ⚙;
                            v08: marker, attributes, site matching, release workflow)
  examples/, test_examples.py the code from docs/EXAMPLES.md
runtests.py                   test runner (also `runtests.py makemigrations`)
.github/workflows/test.yml    CI: Python 3.12–3.14 + Wagtail 7.0 + wheel build check
.github/workflows/release.yml on a v* tag: test, check version, attach wheel + sdist to the release
README.md                     what it is + quick start; user docs in docs/ (0.9 split):
                              GUIDE (features), SETTINGS, TROUBLESHOOTING, UPGRADING, DEVELOPMENT
CHANGELOG.md                  per-release changes
LICENSE                       MIT
docs/plans/               each release's plan + progress log
docs/EXAMPLES.md          copy-paste models / blocks (code mirrored in tests/examples/)
docs/PREVIEWS.md          user guide: make previews match your site (0.8)

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
   content (synthesis stays the fallback). Scoped again for 0.7 ("Use as demo content" on a
   real section) and deferred by choice.
6. **Publish to PyPI** so other projects `pip install prblm-builder`. (0.8: the release
   workflow attaches the wheel to each GitHub release, which covers servers without
   GitHub access; PyPI would make the package public — the owner's call.)
7. ~~**Install into another Wagtail project**~~ — done after 0.1.0; led to the 0.2 changes.
   Still to verify there: whether the Layout tab shows a page's unpublished draft
   sections (it reads the live row — see §7).
8. ~~**Optional built-in blocks**~~ — done in 0.3 (21 blocks, Theme, Header & footer,
   Builder page). Possible next: more blocks (contact form needs storage + spam
   protection), a theme preview on the Theme page, dark-mode aware defaults.
9. **Single-frame canvas** — render the whole page in one frame (sections as positioned
   regions) so CSS / scripts that read neighbouring sections (`section + section`, a wave
   coloured by the next section) work too. Big rewrite; noted in 0.9, not planned.
10. **Dark mode** for the builder UI and Block library (they use fixed light colours).
