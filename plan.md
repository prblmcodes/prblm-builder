# Plan — v0.5.0: easier editing in the Layout tab

Branch: `feature/v0.5.0` · Status: **in progress** · Written 2026-11-09
Previous plans: `docs/plans/v0.3.0.md` (built-in blocks), `docs/plans/v0.4.0.md` (feedback round).

---

## 1. Decisions (agreed)

| # | Topic | Decision |
|---|---|---|
| 1 | **Wagtail block preview values** | When a block defines Wagtail's own `preview_value` (Wagtail 6.4+ API), use it **everywhere**: Block library, sidebar thumbnails, and as the starting content of a new section — first choice, before real site content / generated text. Show the block's `description` as a subtitle (library) and tooltip (sidebar). |
| 2 | **Simpler link field** (built-in `LinkBlock`) | **Label**, then **Link type**, then only the matching field. Types: **Page**, **Web address** (`https://…` or `/path/`), **Section on this page** (`#anchor`), **Document**, **Email**, **Phone**. Fields shown/hidden by a small admin script. Existing links keep working (type inferred). |
| 3 | **Section settings in the Layout tab** | A **⚙ Settings** button in each section's toolbar opens a **popover next to the section** with its settings (built-ins: background swatches + anchor ID). Canvas updates live; saved with the page. In the Content tab these fields move into **Wagtail's collapsed "settings" area** of the block (Wagtail 8.1 `form_layout` settings). |
| 4 | **Settings for the site's own blocks** | **Opt-in per block**: `class Meta: builder_settings = ["background", "theme"]` makes those fields appear in the ⚙ popover. Built-ins declare theirs the same way. |
| 5 | **Copy / paste sections** | **Same page only.** Copy from the section toolbar, Ctrl/⌘+C / V on a selected section, and a **right-click menu** (Copy, Paste above, Paste below, Duplicate, Settings, Delete). The existing ⧉ Duplicate stays. |
| 6 | **Header & footer on Builder pages** | **One dropdown each** (instead of two fields each): *Site default (name)*, *None*, *My site's own* (only if the template setting exists), then every header/footer by name. They move from the Content tab to a new **"Page" tab in the Layout sidebar** (tabs: **Sections \| Page**). Canvas updates live. Database fields unchanged. |
| 7 | **Release** | **v0.5.0** on `feature/v0.5.0`, phase by phase with tests + browser checks; release after the owner tests. |

### Why there are four header/footer fields today
Each of header and footer has two: `header_choice` (*what kind*: site default / choose one /
site's own / none) and `header` (*which one*, only used with "choose one"). v0.5 shows them
as **one** dropdown each; the two stored fields stay (so no data migration).

## 2. Technical approach

### 2.1 Preview values + descriptions (core)
- `previews.explicit_preview_value(block)` → `block.get_preview_value()` **only when** the
  block sets `preview_value` (`hasattr(block.meta, "preview_value")`) — Wagtail falls back to
  `default` otherwise, which we already handle.
- Order in `previews.demo_value` and `views._demo_value`: explicit preview value → (built-ins:
  own defaults) → real site content → generated content.
- `is_unedited` also compares against the preview value.
- `registry` returns `block.get_description()` with each block; palette item `title` +
  Block-library card subtitle.

### 2.2 Link block (blocks app)
- `LinkBlock` gains `link_type` (choice), `anchor`, `document`, `email`, `phone`; keeps
  `label`, `page`, `url`. Field order: label, link type, then the type fields.
- `LinkValue.href` resolves by `link_type` (`#anchor`, document URL, `mailto:`, `tel:`…). For
  links saved before 0.5 (no `link_type`): **inferred** — page set → page; `url` starting
  `#` → section; otherwise web address. No data migration.
- `clean()`: when a label is set, the chosen type's field is required (clear message).
- Admin JS: a `StructBlockDefinition` subclass registered via a Wagtail telepath adapter
  (`js_constructor`, documented Wagtail API) that shows only the selected type's field and
  updates on change. Without JS everything still shows (graceful).
- All built-in defaults updated to set `link_type` (e.g. `{"label": "Get in touch",
  "link_type": "anchor", "anchor": "contact"}`).
- Check: `makemigrations prblm_builder_blocks --check` (StructBlock subclasses deconstruct by
  class path, so adding child fields shouldn't need a migration — verify; same for sites
  using `builder_blocks()`).
- Note: sections seeded with the *old* defaults lose the "Not edited yet" badge (their value
  no longer equals the new default) — false negative only, acceptable.

### 2.3 Section settings
- **Declaring:** `Meta.builder_settings = [field names]` on any StructBlock. Built-ins: a shared
  base `SectionBlock` sets `["background", "anchor_id"]` (Header/Footer: `["background"]`) and
  overrides `get_form_layout()` → `BlockGroup(children=<content fields>, settings=<those>)`,
  so the Content tab shows them in Wagtail's collapsed settings area. (Changing the base
  class keeps every block's module path — the promise holds.)
- **Schema to the canvas:** for each block type with settings, the builder page receives a
  small schema per field: `choice` (+ choices; the four backgrounds render as colour swatches),
  `text` (+ max length / pattern), `boolean`. Current values per section come with the
  section list.
- **Popover** (builder.js/css): ⚙ button in the section toolbar (only when the type has
  settings); popover anchored to the section, keyboard-accessible, Esc / click-outside closes.
  Changes apply instantly to the preview (preview URL gets `&settings=<json>`; the preview
  view overrides those fields before rendering).
- **Saving:** `_pb_layout` items carry `settings: {field: value}` **only for changed fields**;
  `layout.reconcile` writes them into the section's value (existing, new and copied sections),
  validating each with the child block's `clean()` — an invalid anchor ID becomes a normal form
  error (and the arrangement is kept, as in 0.4). If the same field was also changed in the
  Content tab, the Layout tab's change wins (documented).

### 2.4 Copy / paste + context menu (builder.js)
- In-memory clipboard of a section (`type`, source id, settings), also in `sessionStorage`
  keyed by page id so it survives the iframe reloading; ignored on other pages.
- Paste inserts a `copy_from` section (the mechanism Duplicate already uses), carrying the
  copied settings; part of undo/redo.
- Toolbar: **Copy**; when the clipboard is filled, **Paste below** appears in toolbars.
- Keys: Ctrl/⌘+C / Ctrl/⌘+V on the selected section (not while typing in inputs).
- Right-click on a section: custom menu (Copy, Paste above, Paste below, Duplicate,
  Settings, Delete); the browser menu still works elsewhere.

### 2.5 Sidebar tabs + header/footer dropdowns
- **Generic "Page" options (core):** a new hook `prblm_builder_page_options(request, page,
  model)` returns option descriptors `{name, label, choices, value}`. The core renders a
  **Sections | Page** tab bar only when some option exists. The blocks app answers for
  Builder pages with *Header* and *Footer*.
- **Where the values live:** the real `header_choice` / `header` / `footer_choice` / `footer`
  form fields move from the Content tab into the Layout tab, **visually hidden**; the
  sidebar dropdown writes into them (same-origin, like the hidden layout fields). One
  dropdown value maps to the two stored fields (`"h:12"` → choice *custom* + header 12).
- **Live canvas:** changing a dropdown reloads the header/footer frame with the chosen
  override (`&header=…`).
- Works on new, unsaved Builder pages too.

## 3. Phases (checklist)

- [x] **Phase 1 — Preview values + descriptions** (core). Tests.
- [x] **Phase 2 — Link block**: fields, inferred types, validation, admin JS, new defaults,
      migration check. Tests + browser check of the show/hide.
- [x] **Phase 3 — Section settings**: `builder_settings`, collapsed settings area in the Content
      tab, schema, ⚙ popover, live preview, save + validation. Tests + browser check.
- [x] **Phase 4 — Copy / paste + right-click menu** (same page). Browser check.
- [x] **Phase 5 — Sidebar tabs + header/footer dropdowns** (page-options hook). Tests +
      browser check.
- [ ] **Phase 6 — Release**
  - [x] README (⚙ settings + `BuilderSettingsMixin`, preview values, links, copy/paste, Page
        tab, upgrading 0.4 → 0.5, troubleshooting), CHANGELOG, history doc, CLAUDE.md,
        version 0.5.0, CI wheel checks
  - [x] Upgrade test: fresh site on 0.4.1 (Builder page with a chosen header + a page model
        using `builder_blocks()`) → 0.5.0 wheel → `migrate` + one `makemigrations` (Alter
        field) → old links work, Page tab pre-selects the header, admin pages load
  - [ ] Owner tests in a real project
  - [ ] Merge to `main`, tag `v0.5.0`

## 4. Progress log

- 2026-11-09 — Discussion + interview done; plan written.
- Phase 1 done (118 tests): explicit `preview_value` first everywhere; descriptions in the
  library + sidebar tooltips (also searchable); all 21 built-ins got a description (no migration).
- Phase 2 done (124 tests; browser-checked: only the chosen type's field shows, switching
  works, saves as `mailto:`). Findings: (1) block **default values** are part of the
  migration description, so the new link defaults need migration `0003_link_types` (no data
  change) — sites using `builder_blocks()` will see an "Alter field" on `makemigrations`;
  (2) hide the element marked `data-contentpath="<field>"` (it holds the label too), not the
  input wrapper; (3) a document link falls back to the file URL if the site doesn't route
  `wagtail.documents` URLs.
- Phase 3 done (134 tests; browser-checked in the real editor: ⚙ → popover with Background
  swatches + Anchor ID → canvas turns dark/brand instantly → Save → stored `background` /
  `anchor_id` changed, content untouched). `BuilderSettingsMixin` lives in the **core**
  (`prblm_builder/mixins.py`) so site blocks can use it without the blocks app; the test app
  has such a block. Findings: (1) the floating "Wider preview" button covered the top
  section's toolbar → moved to the bottom-right; (2) Playwright's auto-scroll inside a fixed
  popover in an iframe shifts Wagtail's `main` sideways — a test artifact (real mouse clicks
  don't); (3) **Wagtail 8.1 auto-saves drafts** (`WAGTAIL_AUTOSAVE_INTERVAL`, default 500 ms)
  when the form changes — Layout-tab changes trigger it too, and reconcile handles repeated
  saves correctly.
- Phase 4 done (136 tests; browser-checked: Copy in the toolbar → Paste button appears;
  right-click → Paste below; Ctrl+C / Ctrl+V; undo; saved copies keep content + settings
  with unique ids). Toolbar actions, shortcuts and the menu share one `act()` function.
- Phase 5 done (146 tests; browser-checked: header fields gone from the Content tab; Layout
  sidebar **Sections | Page** tabs; picking a header shows it on the canvas at once, saves
  as custom + id, "No header" hides it; the tab is remembered). A Builder page set to
  "Choose one" whose header was deleted now falls back to the site default (no error on a
  hidden field). Two older bugs found and fixed while checking:
  1. **The Layout tab showed the published page, not the latest draft** (the long-open
     "draft vs live" question — now confirmed and fixed: builder, section previews,
     header/footer and the standalone save all use `get_latest_revision_as_object()`).
     No data had been lost (saves merged with the draft), but the canvas was out of date.
  2. **"Not edited yet" disappeared after the first normal save**: Wagtail's form stores
     empty text as `""` (default `None`) and adds `data-block-key` to rich text. The
     comparison now ignores both.
- Phase 6 docs + upgrade test done; 146 tests. Waiting for the owner's test.
- Owner request while testing: clear tooltips on the section toolbar buttons (were slow,
  faint browser `title` tooltips) — instant `[data-tip]` tooltips, also on keyboard focus.
- More owner feedback: chevron + bigger line icons in the toolbar; the toolbar Paste button
  removed (paste via right-click / Ctrl+V); Page tab on the site's own page types is
  **information only** (where the header/footer come from). Per-page header choice for site
  pages was discussed (plugin-owned table + wrapping tag, or a model mixin) and postponed.
