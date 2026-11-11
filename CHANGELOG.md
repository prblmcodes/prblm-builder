# Changelog

## 0.8.0 — 2026-11-11

From testing 0.7 in a multi-site project (two Tailwind builds, Alpine, scroll-reveal
animations, per-page headers).

**Added**
- **Gaps between sections on the canvas match the page**: neighbouring sections' margins
  merge (the gap is the larger margin, not both added up), also between the header and the
  first section — except inside a flex / grid wrapper in your preview template, where they
  don't merge on the page either.
- **`class="prblm-canvas"`** on every preview's `<html>` (also with a preview template, which
  also gets `prblm_preview`), so you can show scroll-reveal / animated elements in previews
  with one CSS rule.
- **`PRBLM_BUILDER_REDUCE_MOTION`** (default `True`): animations and transitions finish
  instantly in previews.
- **`PRBLM_BUILDER_PREVIEW_BODY_ATTRS` / `_HTML_ATTRS`** (and `body_attrs` / `html_attrs` per
  site profile): attributes such as Alpine's `x-data` or `data-theme` on the preview's
  `<body>` / `<html>`, and on Builder pages that use your assets. Ignored with a preview
  template.
- **`PRBLM_BUILDER_PREVIEW_SITES` matching**: keys may also be the Site's name or a wildcard
  (`landing.*`), so one entry covers every environment. A site that matches nothing is marked
  in the Block library's Site switcher and logged once.
- **Release files** (`.github/workflows/release.yml`): pushing a `v*` tag runs the tests,
  checks the tag matches the package version, builds the wheel and source archive, and
  attaches them to the GitHub release (a draft is created if needed).
- **[docs/PREVIEWS.md](docs/PREVIEWS.md)**: step by step, make previews match your site. README:
  "Installing on servers".

- **Previews don't navigate**: clicking a link (or submitting a form) inside a preview —
  canvas, thumbnails, Block library — does nothing; script buttons still work.
- **Spacing on the canvas**: the selected section shows its margins as striped bands
  ("Space · 112px").
- **Kind filter** pills (All · Built-in · Your site's) in the Block library and the Layout
  sidebar; search always covers every kind.
- **Block library**: "Used on N pages" sits top right in a grey header strip that can't be
  mistaken for the section; with several sites, the Site switcher (shown whenever there's
  more than one Site) also counts usage per site, with an "All sites" choice.
- **Page tab** explains where this page's header / footer really come from — the page
  type's own code, the site's shared template (file name as a developer hint), a Headers /
  Footers entry, or none — instead of always naming the template setting.
- README: how block **groups** work (Wagtail's `group` option; "Other" without one).

**Upgrade notes**
- No migrations. See README → Upgrading → 0.7 → 0.8.

## 0.7.0 — 2026-11-11

**Demo content**
- Chosen **field by field**: the block's `preview_value` (it may now leave fields out — e.g.
  images, which can't be portable), real content of the same block, the field's default,
  then generated content. The result always passes the block's own validation, so a new
  section can always be saved.
- Real content is borrowed only from **published** pages, only from sections someone
  edited (never the plugin's own untouched demo sections), and only if it validates.
- Generated text is **neutral and labelled** ("Section heading", "Button label",
  "Short description … — replace this with one or two sentences of your own"), sized to
  the field (headings a few words, text a sentence, rich text a paragraph; `max_length`
  respected), numbered in lists, never repeated within a section.
- **Images fit the field**: wide photos for banners / heroes / backgrounds (never SVG or
  transparent images), square / SVG / transparent ones for logos and icons, taking turns
  in lists. When nothing fits, a labelled placeholder of the right shape is created once
  in a **Builder placeholders** collection.
- **Links**: one consistent link (its type and only that field), to a real page — works for
  the built-in link block and third-party ones such as wagtail-link-block.
- Lists use 3 items, or `min_num` if more, capped at `max_num`; a developer-set `default`
  is used. Documents stay empty unless required.

**Previews**
- `PRBLM_BUILDER_CANVAS_HEIGHT` (default 900): sections sized in `vh` look as on a real
  screen.
- A **fixed site header** is measured correctly on the canvas; published **Builder pages**
  start their sections below it (overridable with `--prblm-header-offset`).
- An empty header/footer takes no space on the canvas.
- Section heights are measured more robustly (collapsed margins, images, web fonts, DOM
  changes, device switching).
- `PRBLM_BUILDER_PREVIEW_TEMPLATE`: render previews inside your own base template (body
  attributes like Alpine's `x-data`, inline scripts, wrappers).
- `PRBLM_BUILDER_PREVIEW_SITES`: CSS / JS / body class / header / footer / template per
  Wagtail Site; the Block library gets a site switcher.
- `PRBLM_BUILDER_PREVIEW_CSS` / `_JS` accept dicts: `defer`, `async`, `type="module"`,
  `integrity`, `crossorigin`, `media`, inline code, import maps.

**Editor**
- Dropping a section back where it was no longer counts as a change.
- ⚙ settings: number fields get a number box with their limits; values are checked as you
  type; dropdowns with a default have no empty choice.
- Publishing a page still titled "Untitled page N" asks first (and warns after).
- When Wagtail's auto-save fails after a layout change, the banner says the layout isn't
  saved yet.
- Block library: **All / Used on pages / Not used yet** filter and "Used on N pages" with
  links; search includes descriptions; with `LIBRARY_SCOPE = "all"` each block shows where
  it comes from.
- Two-column forms switch to one column below 720px of form width.

**Docs**
- README: setup for previews (load order, preview template, several sites, `vh`, fixed
  headers, the `prblm_builder_chrome_for_page` hook), where demo content comes from, links
  that work outside GitHub.

**Upgrade notes**
- Run `python manage.py migrate` (new table `prblm_builder_seededsection`).
- See README → Upgrading → 0.6 → 0.7.

## 0.6.0 — 2026-11-10

**Added**
- The **Layout** tab is the **first tab** in the page editor, for new and existing pages.
- **Layout and Content tabs stay in sync:** ⚙ settings update the Content tab at once (and
  the other way round); on a saved page, opening the Content tab after adding / removing /
  moving sections waits for Wagtail's auto-save and reloads onto the Content tab with the
  new sections; switching back to Layout after Content edits refreshes the canvas. New
  pages, and sites with auto-save off, keep the "Save draft now" banner.
- **Two-column block forms:** short fields side by side, long text / rich text / lists /
  grouped fields full width, an unpaired field full width, everything filling its column;
  the block settings area in two columns with a divider while open; one column on narrow
  forms. Done in CSS, so it shows instantly (no flicker when a block or list item is added).
  Always on for the built-in blocks and the Theme page.
- Setting **`PRBLM_BUILDER_SITE_BLOCK_COLUMNS`** (default `False`): `True` uses the same
  layout for your own blocks.
- **Built-in blocks are shielded from the site's CSS:** inside a block every element starts
  from the browser defaults, so global site rules (Tailwind's reset, `p`, `ul`, `a`,
  `header` rules…) no longer change how built-in blocks look.
- **Builder pages load the site's CSS / JS** (`PRBLM_BUILDER_PREVIEW_CSS` / `_JS`, body
  class) when they show the site's own header / footer or contain the site's own blocks.
- `from prblm_builder.blocks import LinkBlock` — reuse the built-in link block in your own
  blocks (example in docs/EXAMPLES.md).
- **[docs/EXAMPLES.md](docs/EXAMPLES.md):** copy-paste page models and blocks for every
  feature, checked by the test suite (`tests/examples/`).

**Fixed**
- Opening a page no longer creates an auto-saved draft when nothing changed.
- After a failed save, the editor opens the tab holding the first error (it could be hidden
  behind the Layout tab).
- The Layout sidebar always opens on **Sections** (it remembered **Page** for the rest of
  the browser session).
- On a Builder page using the site's own header / footer, it showed unstyled.
- The canvas and Block library files are version-stamped, so browsers load the new ones
  after an upgrade (no hard refresh needed).
- **Wagtail's preview** of a Builder page showed the site's header / footer and own blocks
  unstyled: the site's CSS / JS were linked with the Site's hostname, which Wagtail's
  preview uses but the browser may not. They're now linked as `/static/…`.
- A **new section on the canvas** showed shortened text while the full text was saved (and
  shown by Wagtail's preview). The canvas now shows exactly what's saved; only the Block
  library and sidebar thumbnails shorten long text.
- A **gap under the header** on the canvas when the header is a plugin header.
- **The same block under different names** (e.g. `hero_section_home` on your HomePage and
  `hero1` in `PRBLM_BUILDER_PAGE_EXTRA_BLOCKS`) is now one block: it borrows the same real
  content for demos (with its snippets and pages), gets a sidebar thumbnail, and is listed
  once in the Block library. Blocks are matched by class.
- **Third-party blocks** (e.g. `wagtail-link-block`) could get demo content their own
  validation rejects, so the page didn't save — with the error on a field that block hides.
  Generated demo content is now checked against the block's validation (and link / phone
  fields get valid values).
- Generated demo content fills snippet choosers with an existing snippet.

**Upgrade notes**
- No migrations.

## 0.5.0 — 2026-11-09

**Added**
- **Section settings (⚙):** fields listed in a block's `Meta.builder_settings` get a ⚙ button
  on the section in the Layout tab — a small panel (choices, colour swatches for
  backgrounds, on/off, short text); the canvas updates live; saved with the page.
  `prblm_builder.mixins.BuilderSettingsMixin` moves those fields into Wagtail's collapsed
  settings area in the Content tab. Built-in blocks use it for background + anchor ID.
- The ⚙ background swatches of built-in blocks show the **site's Theme colours** (own blocks
  show the names only); the "Muted (soft grey)" option is now just "Muted".
- **Copy & paste** sections within a page: Copy from the toolbar or Ctrl/⌘+C; paste with the
  **right-click menu** (Paste above / below — it also has Duplicate, Settings, Move, Delete)
  or Ctrl/⌘+V.
- **Page tab** in the Layout sidebar (Sections | Page). Builder pages choose their header
  and footer there — one dropdown each — instead of four fields in the Content tab. On the
  site's own page types it explains where the header and footer come from.
- Wagtail block **`preview_value`** is used first for previews and new sections;
  **`description`** shows in the Block library and sidebar. All built-ins have descriptions.
- **Simpler links** in built-in blocks: Label → *Link to* (page, web address, section on this
  page, document, email, phone) → only that field. Old links keep working.
- **Tooltips** on the section toolbar buttons (instant, on hover or keyboard focus).
- Section toolbar: one set of line icons (chevrons for move up/down, a distinct duplicate
  icon), 17px icons in the same 26px buttons; it always shows the same buttons.
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
