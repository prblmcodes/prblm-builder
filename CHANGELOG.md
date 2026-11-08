# Changelog

## 0.3.0 — unreleased

**Built-in blocks (new, optional app `prblm_builder.blocks`)**
- 21 ready-made sections: Header, Footer, Hero, Page banner, Text, Text + image, Features,
  Cards, Steps, Quote, Testimonials, Logo strip, Stats, Call to action, FAQ, Pricing,
  Gallery, Video, Team, Contact info, Divider. Fully self-contained CSS/JS (loaded once
  per page by `{% prblm_assets %}`), pre-filled explanatory content, four section
  backgrounds, anchor IDs, 50 line icons, labelled image placeholders.
- **Theme** page (Page builder → Theme): colours, fonts, roundness, content width.
- **Header & footer** page: one site-wide header/footer, shown around the builder canvas
  and available on any template via `{% prblm_header %}` / `{% prblm_footer %}`.
- Ready-made **Builder page** type (hide with `PRBLM_BUILDER_PAGE_TYPE = False`) and the
  `builder_blocks(exclude=…, only=…)` helper for your own page models.

**Breaking**
- Removed `PRBLM_BUILDER_SEED_NEW_BLOCKS`: new blocks always start with content. A
  project that still sets it gets a startup warning (`prblm_builder.W001`).

**Added**
- "Not edited yet" badge on canvas sections that still hold their demo content.
- "Page builder" section in the admin sidebar; the Block library moved there from
  Settings. The Block library groups *Built-in blocks* and *Your site's blocks*.

**Fixed**
- `PRBLM_BUILDER_DEMO = False` now also hides the Block library menu item (Wagtail caches
  menus, so the old check only ran once at startup).
- A site block and a built-in block with the same name no longer collide in the Block
  library or in demo content.

**Developers**
- New hook `prblm_builder_chrome(kind, request, page)` lets an app supply the canvas
  header/footer; new hook `register_prblm_builder_menu_item` adds items to the
  Page builder menu.
- The shipped generic tests pick a page model with a `rich_text` block.

## 0.2.0 — 2026-11-08

**Block selection**
- The Block library now lists the same blocks as the Layout palette (top-level blocks of
  builder-enabled page fields). Blocks used only nested inside others, or only in
  non-page StreamFields, no longer appear. *Behaviour change* — set
  `PRBLM_BUILDER_LIBRARY_SCOPE = "all"` for the old project-wide list.
- A block can opt out with `class Meta: builder = False`.
- New `PRBLM_BUILDER_EXCLUDE_BLOCKS`: hide blocks by name or dotted class path.
- Blocks that error or render nothing are listed in a collapsed "Couldn't preview"
  section of the Block library, with the reason, instead of an empty/red card.

**New settings**
- `PRBLM_BUILDER_SEED_NEW_BLOCKS` — `False` makes new blocks start empty (text fields
  `""`, never `"None"`), with a "New …" placeholder on the canvas.
- `PRBLM_BUILDER_CANVAS_WIDTH` — desktop width sections render at (default 1280).
- `PRBLM_BUILDER_PLACEHOLDER_IMAGES` — `False` stops the plugin adding placeholder images.
- `PRBLM_BUILDER_LIBRARY_SCOPE` — `"builder"` (default) or `"all"`.
- `PRBLM_BUILDER_ADMIN_TWEAKS` — `False` turns off the parts that hook into Wagtail
  admin internals (full-width Layout tab, editor-header link).

**Other**
- Header/footer templates on the canvas now get `page` / `self` (the page being edited).

## 0.1.0 — 2026-11-08

First public release.

- **Layout tab** in the Wagtail page editor: drag the site's own StreamField blocks onto a
  canvas, reorder / duplicate / delete, undo/redo, desktop-scaled live previews.
- **Auto-attach** to every page model with a buildable StreamField (default `body`) — no
  per-model code.
- **Ride-along save**: the arrangement saves with the page's own Save draft / Publish.
- **Works on new, unsaved pages.**
- **Block library**: admin page previewing every block with realistic demo content
  (real site content where available, otherwise synthesised).
- Requires **Wagtail 8.1+**, **Django 6.1+**, **Python 3.12+**.
