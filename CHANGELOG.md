# Changelog

## 0.5.0 — unreleased

**Added**
- **Section settings (⚙):** fields listed in a block's `Meta.builder_settings` get a ⚙ button
  on the section in the Layout tab — a small panel (choices, colour swatches for
  backgrounds, on/off, short text); the canvas updates live; saved with the page.
  `prblm_builder.mixins.BuilderSettingsMixin` moves those fields into Wagtail's collapsed
  settings area in the Content tab. Built-in blocks use it for background + anchor ID.
- **Copy & paste** sections within a page (toolbar, Ctrl/⌘+C / V) and a **right-click menu**
  (Copy, Paste above/below, Duplicate, Settings, Move, Delete).
- **Page tab** in the Layout sidebar (Sections | Page). Builder pages choose their header
  and footer there — one dropdown each — instead of four fields in the Content tab.
- Wagtail block **`preview_value`** is used first for previews and new sections;
  **`description`** shows in the Block library and sidebar. All built-ins have descriptions.
- **Simpler links** in built-in blocks: Label → *Link to* (page, web address, section on this
  page, document, email, phone) → only that field. Old links keep working.
- **Tooltips** on the section toolbar buttons (instant, on hover or keyboard focus).
- Developers: hooks `prblm_builder_page_options`; model attribute `builder_layout_panels`.

**Fixed**
- The Layout tab showed the **published** page instead of the **latest draft**; it now works
  on the draft (canvas, previews, header/footer, standalone save), like Wagtail's editor.
- "Not edited yet" disappeared after the first normal save (Wagtail stores empty text as
  `""` and adds `data-block-key` to rich text) — now ignored.
- The "Wider preview" button covered the first section's toolbar; it's now bottom-right.

**Upgrade notes**
- `migrate` (built-in block definitions only). Projects using `builder_blocks()` should run
  `makemigrations` once (an "Alter field", no data change).

## 0.4.1 — 2026-11-09

**Fixed**
- Sidebar titles in the Block library ("Built-in blocks", "Your site's blocks" and the
  group titles) and in the Layout tab's sidebar no longer have side margins: they now line
  up with the search box, and the fold arrows with its right edge.

## 0.4.0 — 2026-11-09

**Changed**
- **Headers & Footers** replace 0.3's single *Header & footer* page: create as many as you
  like under *Page builder → Headers / Footers*, mark one of each as the **site default**.
  `migrate` moves existing content over automatically.
- **Builder page** chooses its header and footer: site default, a specific one, the site's
  own template, or none.

**Added**
- Layout tab: after any change, a banner explains that new sections appear in the Content
  tab once saved, with **Save draft now** (fills "Untitled page N" if the title is empty).
  A failed save keeps the arrangement.
- Foldable groups (built-in / site blocks and each group) in the Layout sidebar and the
  Block library, synced between the library's sidebar and previews, remembered per browser.
- `PRBLM_BUILDER_PAGE_PARENTS` — allow Builder pages under page types that restrict their
  children.
- `PRBLM_BUILDER_PAGE_EXTRA_BLOCKS` — the site's own blocks on the Builder page, without
  migrations inside the plugin.
- `{% prblm_header "Name" %}` / `{% prblm_footer "Name" %}` to pick one by name.
- Developers: `prblm_builder_chrome_for_page` hook (a page type decides its own canvas
  header/footer).

**Fixed**
- Canvas empty-state text no longer mentions a pencil button in the Layout tab.

## 0.3.0 — 2026-11-09

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
