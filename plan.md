# Plan — v0.6.0: Layout first, tabs in sync, two-column forms, examples

Branch: `feature/v0.6.0` · Status: **in progress** · Written 2026-11-09
Previous plans: `docs/plans/` (v0.3.0 built-in blocks, v0.4.0 feedback round, v0.5.0 Layout editing).

---

## 1. Decisions (agreed)

| # | Topic | Decision |
|---|---|---|
| 1 | **Tab order** | The **Layout** tab is the **first tab, always** — for new and existing pages, on every builder-enabled page type. (Title lives in the Content tab; the existing "Save draft now" banner already fills a placeholder title, and Wagtail jumps to a tab with errors.) |
| 2 | **Two-column fields** in block forms | **Narrow (50%)**: short text, email, URL, number, dropdown, checkbox, date, image / page / document choosers. **Full (100%)**: long text (textarea), rich text, lists, grouped fields (e.g. a button's Label + Link to) — and the fields *inside* a group get the same two-column treatment. A narrow field **without a partner** (before the next full-width field, or at the end) becomes **full width**. Every field fills its column (dropdowns, choosers stretched). One column below ~600px of form width. |
| 3 | **Settings area** (Wagtail's collapsed block settings) | Its fields (background, anchor ID) use the same two-column rule, with a **divider under it only while it's open**. |
| 4 | **Where it applies** | Built-in blocks **always** (Content tab of any page, Headers, Footers, Builder pages), plus the plugin's own admin forms (Theme). The site's **own blocks: opt-in** via a setting. |
| 5 | **Keep the Layout and Content tabs in sync** | (a) **Settings sync both ways, instantly**: a change in the ⚙ popover also updates the same field in the Content tab; a change to a settings field in the Content tab updates the canvas. (b) **Existing pages**: after adding / removing / moving sections, switching to the Content tab reloads the editor (the change is already auto-saved) and opens the Content tab with the new sections in it. (c) Switching to the Layout tab after Content edits refreshes the canvas from the auto-saved draft. (d) **New pages** stay manual ("Save draft now") until the first save. (e) With Wagtail auto-save off (`WAGTAIL_AUTOSAVE_INTERVAL = 0`) it falls back to today's behaviour. |
| 6 | **Examples guide** | A new **`docs/EXAMPLES.md`**: copy-paste StreamField models and blocks for every feature (plain `body` page; own blocks with templates, `description`, `preview_value`; `builder_settings` + `BuilderSettingsMixin`; hiding blocks; mixing `builder_blocks()` with own blocks; Builder page extras + parents; header/footer tags in `base.html`; block templates using the settings). The same code lives in the test project so tests prove the examples work. Linked from the README. |
| 7 | **Release** | v0.5.0 released first; this is **v0.6.0** on `feature/v0.6.0`. |

## 2. Technical approach

### 2.1 Layout tab first (core, `integration.py`)
- Insert the Layout tab at position 0 instead of 1 (for models with their own `edit_handler`
  and for generated ones). Wagtail opens the first tab by default; a URL hash (`#tab-content`)
  still opens another tab.
- Check: create + edit views, validation errors (Wagtail switches to the tab with the error),
  the "Save draft now" banner, models with a custom `edit_handler`.

### 2.2 Two-column forms (core JS + CSS, `form-columns.js`)
- **Where Wagtail puts fields** (8.1): a StructBlock's fields are sibling
  `div[data-contentpath="<name>"]` elements inside `.struct-block`; the settings area is a
  `[data-block-settings]` element (`hidden` until opened).
- A small script, loaded on admin edit pages (Wagtail `insert_global_admin_js` hook), finds
  struct-block forms to lay out and turns their field container into a 2-column CSS grid:
  - **kind of each field** from its widget: `textarea`, rich-text editor, list/stream
    containers or nested `[data-contentpath]` children → *full*; everything else → *narrow*;
  - **pairing**: walk the *visible* fields in order, pair consecutive narrow fields; an
    unpaired narrow field → full;
  - re-runs when the form changes (MutationObserver: blocks/list items added, link-type
    switch hiding fields, settings area opened).
- **Which forms**: built-in blocks are marked with a form class (`pbk-form`, set via
  `Meta.form_classname` on the built-in StructBlocks, incl. item blocks like FAQ items and
  the link block); site blocks only when the setting allows.
- **CSS**: grid with `grid-column: span 2` for full fields; stretched selects/choosers;
  divider + 2-column grid for an open `[data-block-settings]`; container query → 1 column.
- **Fallback**: if Wagtail's markup changes, the script finds nothing and forms stay
  Wagtail's normal stacked layout.

### 2.3 Plugin admin forms
- Theme page: colour fields in two columns (same CSS classes via panel `classname`).
- Headers / Footers / Builder page: their StreamField block forms are built-in blocks → 2.2.

### 2.4 Tabs in sync (core JS: `builder.js` + `layout_panel.html`)
- **Settings, Layout → Content**: the editor form holds each stream child's id in a hidden
  `<field>-N-id` input; from a section id the builder finds index N and writes the new value
  into `<field>-N-value-<setting>` (select / input / checkbox) and fires `change` — the
  Content tab shows it at once and the save uses it directly. Sections not yet in the
  Content tab (new, unsaved) keep today's hidden-field route.
- **Settings, Content → Layout**: the panel script listens for changes to those inputs and
  tells the builder iframe to update that section's settings + preview.
- **Structure changes on existing pages**: the builder marks the layout "structurally
  changed" (add / remove / move / paste / duplicate). When the editor switches to the
  Content tab, the panel script waits for Wagtail's auto-save to finish (or triggers a
  draft save), then reloads the edit view on `#tab-content`.
- **Content edits → canvas**: on switching to the Layout tab after Content-tab changes,
  wait for the auto-save, then reload the section previews (they render the latest draft).
- **New pages / auto-save off**: no automatic reload; the existing banner + "Save draft now".
- Check first: Wagtail 8.1's auto-save events/state for "save finished" (and that create
  views don't auto-save), so we never reload over unsaved input.

### 2.5 Examples guide (`docs/EXAMPLES.md` + `tests/examples/`)
- A small example app in the test project (`tests/examples/`: `models.py`, `blocks.py`,
  templates) with the exact code shown in the guide.
- `tests/test_examples.py` checks each example: the Layout tab appears, ⚙ settings show,
  preview values / descriptions are used, hidden blocks stay hidden, the Builder page gets
  the extra blocks.
- The guide explains *why* for each snippet and links back to the README sections.

### 2.6 New setting
`PRBLM_BUILDER_FORM_COLUMNS` — `"builtin"` (default: built-in blocks + plugin forms),
`"all"` (also the site's own blocks), `False` (off everywhere).

## 3. Phases (checklist)

- [x] **Phase 1 — Layout tab first.** Tests (tab order for generated + custom edit
      handlers) + browser check (create, edit, validation error).
- [x] **Phase 2 — Tabs in sync**: settings both ways, reload into the Content tab after
      structure changes, canvas refresh after Content edits, new-page + auto-save-off
      fallbacks. Tests + browser checks (existing page, new page, auto-save off).
- [ ] **Phase 3 — Two-column block forms**: `form-columns.js` + CSS, `pbk-form` on built-in
      blocks, settings-area divider, re-layout on changes, setting. Tests + browser checks
      (Hero, FAQ list items, link type switch, settings open/closed, narrow window).
- [ ] **Phase 4 — Plugin admin forms** (Theme page) + opt-in for site blocks ("all").
      Browser check.
- [ ] **Phase 5 — Examples guide**: `docs/EXAMPLES.md` + `tests/examples/` app + tests.
- [ ] **Phase 6 — Release**: README (link the examples, new setting, tab order, sync),
      CHANGELOG, history doc, CLAUDE.md, version 0.6.0, upgrade check from 0.5.0, merge +
      tag after the owner tests.

## 4. Progress log

- 2026-11-09 — v0.5.0 released. Interview done; plan written. Wagtail 8.1 markup inspected
  (tabs: `w-tabs`, first tab active, URL hash honoured; block fields: sibling
  `[data-contentpath]` in `.struct-block`; settings: `[data-block-settings][hidden]`).
- 2026-11-09 — Added: tabs-in-sync phase (settings both ways; reload into Content after
  structure changes on existing pages; new pages stay manual) and an examples guide.
- Phase 1 done (152 tests; browser: Layout opens first on new + existing pages of every
  builder type). Found: after a failed save the title error was hidden behind the Layout tab →
  the panel script now opens the tab holding the first invalid field.
- Phase 2 done (154 tests; browser-checked: opening a page no longer auto-saves; ⚙ change
  shows in the Content tab; Content-tab setting change updates the canvas; add a section →
  open Content → auto-save + reload onto the Content tab with the new section; edit content
  → open Layout → canvas refreshed; new pages don't reload and keep the banner). Findings:
  (1) Wagtail 8.1 auto-save = `w-unsaved` (snapshot 2 s after load, compares FormData every
  500 ms) → `w-autosave` (posts the form, events `w-autosave:save|success|error`, clears the
  unsaved flag on success; on a create view it also turns the page into an edit view);
  (2) because the Layout tab is now first, the builder iframe loads immediately and used to
  write its hidden fields on load → a pointless auto-saved draft on every open; it now writes
  them only after a real change; (3) the panel script runs before the rest of the form (the
  Content tab) is parsed → it waits for DOMContentLoaded.
