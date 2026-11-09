# Plan — v0.6.0: Layout first + two-column block forms

Branch: `feature/v0.6.0` · Status: **planned — not started** · Written 2026-11-09
Previous plans: `docs/plans/` (v0.3.0 built-in blocks, v0.4.0 feedback round, v0.5.0 Layout editing).

---

## 1. Decisions (agreed)

| # | Topic | Decision |
|---|---|---|
| 1 | **Tab order** | The **Layout** tab is the **first tab, always** — for new and existing pages, on every builder-enabled page type. (Title lives in the Content tab; the existing "Save draft now" banner already fills a placeholder title, and Wagtail jumps to a tab with errors.) |
| 2 | **Two-column fields** in block forms | **Narrow (50%)**: short text, email, URL, number, dropdown, checkbox, date, image / page / document choosers. **Full (100%)**: long text (textarea), rich text, lists, grouped fields (e.g. a button's Label + Link to) — and the fields *inside* a group get the same two-column treatment. A narrow field **without a partner** (before the next full-width field, or at the end) becomes **full width**. Every field fills its column (dropdowns, choosers stretched). One column below ~600px of form width. |
| 3 | **Settings area** (Wagtail's collapsed block settings) | Its fields (background, anchor ID) use the same two-column rule, with a **divider under it only while it's open**. |
| 4 | **Where it applies** | Built-in blocks **always** (Content tab of any page, Headers, Footers, Builder pages), plus the plugin's own admin forms (Theme). The site's **own blocks: opt-in** via a setting. |
| 5 | **Release** | v0.5.0 released first; this is **v0.6.0** on `feature/v0.6.0`. |

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

### 2.4 New setting
`PRBLM_BUILDER_FORM_COLUMNS` — `"builtin"` (default: built-in blocks + plugin forms),
`"all"` (also the site's own blocks), `False` (off everywhere).

## 3. Phases (checklist)

- [ ] **Phase 1 — Layout tab first.** Tests (tab order for generated + custom edit
      handlers) + browser check (create, edit, validation error).
- [ ] **Phase 2 — Two-column block forms**: `form-columns.js` + CSS, `pbk-form` on built-in
      blocks, settings-area divider, re-layout on changes, setting. Tests + browser checks
      (Hero, FAQ list items, link type switch, settings open/closed, narrow window).
- [ ] **Phase 3 — Plugin admin forms** (Theme page) + opt-in for site blocks ("all").
      Browser check.
- [ ] **Phase 4 — Release**: README, CHANGELOG, history doc, CLAUDE.md, version 0.6.0,
      upgrade check from 0.5.0, merge + tag after the owner tests.

## 4. Progress log

- 2026-11-09 — v0.5.0 released. Interview done; plan written. Wagtail 8.1 markup inspected
  (tabs: `w-tabs`, first tab active, URL hash honoured; block fields: sibling
  `[data-contentpath]` in `.struct-block`; settings: `[data-block-settings][hidden]`).
