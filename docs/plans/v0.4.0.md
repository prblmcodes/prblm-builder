# Plan — v0.4.0: editor feedback round

Branch: `feature/v0.4.0` · Status: **released as v0.4.0** · Started 2026-11-09
Previous plan (v0.3.0, built-in blocks): `docs/plans/v0.3.0.md`.

Feedback from using 0.3.0 in a real project, and what we agreed to do about it.

---

## 1. Decisions (agreed)

| # | Problem seen | Decision |
|---|---|---|
| 1 | On a **new page**, sections added in the Layout tab don't appear in the Content tab until the page is saved — and a save that fails (e.g. empty title) **loses the arrangement**. | After any layout change, a clear **banner** in the Layout tab: "Save to edit these sections in the Content tab — **[Save draft now]**". If the title is empty the button fills a placeholder (**"Untitled page 23"**) first, then saves. A failed save **keeps the arrangement** on the canvas. |
| 2 | The **Builder page** can only be added at the root, not under the home page. | Cause: the site's own page types restrict their child types (`subpage_types`). New setting **`PRBLM_BUILDER_PAGE_PARENTS = ["home.HomePage", …]`** — the plugin allows Builder pages under those types. Documented in the README. |
| 3 | Site pages can't use built-in blocks; the Builder page can't use the site's blocks. | Admin switches can't work (block lists are fixed at startup). **`PRBLM_BUILDER_PAGE_EXTRA_BLOCKS`** adds the site's blocks to the Builder page (no migration inside the plugin). Site pages keep using the one-line `builder_blocks()` helper. |
| 4 | Header & footer are one page that can hold several of each — confusing. | **Headers** and **Footers** become separate lists under Page builder (like snippets): create many, click one to edit, each holds exactly one. A **"Use as site default"** checkbox (one default each). Each **Builder page chooses** its header and its footer: *site default* / *a specific one* / *the site's own template* / *none*. Existing 0.3 content is **migrated automatically**. |
| 5 | Long block lists are hard to scan. | **Collapsible groups** in the Block library and the Layout sidebar: the two big groups (Built-in / Your site's blocks) and the smaller groups inside. Folding in the sidebar also hides the group in the preview area. Folded state **remembered per browser**. |
| 6 | Canvas header/footer on the site's *own* page types. | The site's `PRBLM_BUILDER_HEADER/FOOTER_TEMPLATE` if set, else the plugin's **site-default** header/footer, else nothing. |

Ships as **v0.4.0** (Header & footer storage changes).

## 2. Technical approach

### 2.1 Save flow (core, `layout_panel.html` + `builder.js`)
- The builder already knows when the layout changed (`dirtied`). It tells the parent
  page (same origin) to show the banner, which sits **in the Layout tab, above the
  canvas** (part of `layout_panel.html`, so it's visible without scrolling the iframe).
- **[Save draft now]**: if the edit form's title is empty, fill `Untitled page N` (N
  supplied by the server: number of pages + 1) and let Wagtail auto-fill the slug; then
  click Wagtail's own *Save draft* button (so all normal validation/hooks run).
- **Failed save keeps the layout**: when the edit form is re-shown after an error, the
  panel passes the submitted `_pb_layout` back to the builder iframe, which restores the
  arrangement (new sections included) instead of starting empty.

### 2.2 Collapsible groups (core, `demo.html`, `builder.html`, `builder.js`)
- Each kind (Built-in / Your site's) and each group gets a toggle button (chevron) right of
  its title, with `aria-expanded`.
- Block library: folding a kind or group in the left sidebar also hides its cards in the
  preview column, and vice versa — one shared state per key.
- Layout sidebar: same toggles for its groups (and kinds, when both exist).
- State in `localStorage` (`prblm-builder:folded`), wrapped in try/except — the page works
  without it.

### 2.3 Headers & Footers (blocks app)
- Models **`SiteHeader`** and **`SiteFooter`** (snippet-style): `name`, `is_default`,
  `content` = StreamField with exactly one Header / Footer block (`min_num=1, max_num=1`).
  Saving one as default clears the flag on the others (per kind).
- Admin: registered as snippets with their own listing/edit views, shown under
  **Page builder → Headers / Footers** (not in the Snippets menu).
- **Data migration**: each site's 0.3 `SiteChrome` header/footer becomes a `SiteHeader` /
  `SiteFooter` named after the site, marked default; then `SiteChrome` is removed. Uses
  historical models (`apps.get_model`) — see the lessons in the history doc.
- **Builder page** gets `header_choice` / `footer_choice` (`default` / `custom` / `site` /
  `none`) + `header` / `footer` foreign keys (used with `custom`); `site` renders the
  site's `PRBLM_BUILDER_HEADER/FOOTER_TEMPLATE`.
- Template tags: `{% prblm_header %}` / `{% prblm_footer %}` render the site default (as in
  0.3); on a Builder page they follow the page's choice. Optional argument to name one:
  `{% prblm_header "Main header" %}`.
- Canvas: the `prblm_builder_chrome` hook returns, for a Builder page, its own choice; for
  other pages the site default (after the template settings, which win — §1 #6).

### 2.4 Builder page placement + extra blocks (blocks app)
- **`PRBLM_BUILDER_PAGE_PARENTS`**: at startup, for each listed page type that restricts
  its children, add `prblm_builder_blocks.BuilderPage` to its allowed child types (and
  clear Wagtail's cached list). Unknown names → a system-check warning, never a crash.
- **`PRBLM_BUILDER_PAGE_EXTRA_BLOCKS`**: list of `("name", "dotted.path.BlockClass")` (or a
  dotted path to a function returning `[(name, block)]`). The Builder page's body uses a
  small `StreamField` subclass whose *runtime* block list = built-ins + extras, but whose
  migration description stays the built-ins only — so the extras never trigger a
  migration inside the installed package. Clashing names / bad paths → `ImproperlyConfigured`
  at startup with a clear message (a broken block list can't be left for later).

## 3. Phases (checklist)

- [x] **Phase 1 — Save flow**: banner + Save draft now + placeholder title; keep arrangement
      after a failed save. Tests.
- [x] **Phase 2 — Collapsible groups**: Block library (kinds + groups, sidebar ↔ preview
      sync) and Layout sidebar; remembered per browser. Tests + visual check.
- [x] **Phase 3 — Headers & Footers**: models, admin lists under Page builder, default
      checkbox, data migration from 0.3, Builder page choices, template tags, canvas. Tests.
- [x] **Phase 4 — Builder page placement + extra blocks**: the two settings, system checks.
      Tests.
- [x] **Phase 5 — Release**
  - [x] README (incl. "Builder page only at root?"), CHANGELOG, history doc, CLAUDE.md,
        version 0.4.0, CI wheel checks
  - [x] Real upgrade test: 0.3.0 install with Header & footer content → install 0.4.0 wheel →
        `migrate` → content is a default Header, Builder page shows it
  - [x] Merge to `main`, tag `v0.4.0` (GitHub release by the owner)
  - [ ] Owner tests the release in a real project

## 4. Progress log

- 2026-11-09 — Feedback interview done; plan written. v0.3 plan archived in `docs/plans/`.
- 2026-11-09 — Phase 1 done (98 tests) and checked end-to-end in a real browser (Playwright
  + system Chrome against a dev server): new page → add 2 blocks in Layout → banner shows →
  "Save draft now" → saved as "Untitled page 3" with both blocks in the Content tab. The
  Layout iframe stays lazy-loaded (so an unopened Layout tab never overrides Content-tab
  reordering); after a failed save the arrangement is also re-submitted via hidden inputs.
- 2026-11-09 — Phase 2 done (100 tests; browser-checked: folding in the library sidebar hides
  the preview cards and vice versa, survives reload, search still finds folded blocks).
  Shared `fold.js`; the Layout sidebar now also splits Built-in / Your site's blocks. Also
  fixed the canvas empty-state text (it mentioned a pencil button the Layout tab doesn't have).
- 2026-11-09 — Phase 3 done (105 tests incl. a migration test that starts from a real 0.3
  database; browser-checked: create a Header in the admin → it opens pre-filled → mark as
  default → a new Builder page shows it → choosing "None" removes it). Core canvas logic
  moved to `prblm_builder/chrome.py` with a new `prblm_builder_chrome_for_page` hook so a
  Builder page's own choice beats the template setting. Lesson: Wagtail's add view builds
  forms without an instance, so a callable StreamField default reaches the widget raw — the
  Header/Footer form seeds `initial` from a fresh instance. Registering them as snippets
  also makes Wagtail's general "Snippets" menu appear (harmless; documented).
- 2026-11-09 — Phase 4 done (113 tests). With an extra block configured,
  `makemigrations prblm_builder_blocks --check` still reports no changes. Lesson: Wagtail
  caches allowed child types in `cls._clean_subpage_models`, set to `None` on every page
  class — reset it to `None`, don't delete it (deleting falls back to the base class's cache).
- 2026-11-09 — Phase 5 docs + version done; 113 tests; real 0.3 → 0.4 upgrade verified.
  Waiting for the owner's test before merging and tagging.
- 2026-11-09 — Merged to `main` and tagged `v0.4.0`.
- 2026-11-09 — v0.4.1 patch: sidebar titles (Block library + Layout tab) lose their side
  margins so they align with the search box (measured in the browser: all at the box edge).
