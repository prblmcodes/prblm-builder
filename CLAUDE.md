# prblm-builder — project context for Claude

This repo is a standalone **Wagtail page-builder plugin**, extracted from a host Wagtail
site ("bemore") where it was first developed. The goal now is to make it cleanly
installable in **any** Wagtail project.

**Read `docs/DEVELOPMENT_HISTORY.md` first** — it has the full architecture, every design
decision, the bugs that shaped the code, the settings reference, and the roadmap. This
file is just the quick orientation.

## What it does
Adds a **Layout** tab to the Wagtail page editor to compose a page by dragging the site's
own StreamField blocks onto a canvas. It discovers blocks by introspection, auto-attaches
to every block-based page model (from `apps.ready()`), and the arrangement **rides along
with the page's own Save/Publish** (hidden form fields → `LayoutBuilderForm.clean` →
`layout.reconcile`). Ships a Block library (demo page) with realistic demo content (real
site content where a block is used, else synthesis).

## Where things live
- `prblm_builder/integration.py` + `panels.py` — auto-attaches the Layout tab + save form.
- `prblm_builder/forms.py` + `layout.py` — the ride-along save + reconciliation; new-block
  values (always demo content; "Not edited yet" detection lives in `previews.is_unedited`).
- `prblm_builder/registry.py` — finds models/blocks; palette + Block library lists; hiding
  rules (`Meta: builder = False`, `PRBLM_BUILDER_EXCLUDE_BLOCKS`).
- `prblm_builder/previews.py` — demo content engine (real-instance → synth → trim) + iframe frame.
- `prblm_builder/views.py` — builder / builder_new / preview / demo / save.
- `prblm_builder/static/prblm_builder/builder.{js,css}` — the canvas (SortableJS, scaled iframes, undo/redo); `fold.js` — foldable groups.
- `prblm_builder/chrome.py` — header/footer around the canvas (hooks → template setting → default).
- `prblm_builder/settings.py` — one reader per `PRBLM_BUILDER_*` setting (all optional).
  User-facing reference: README "Settings reference"; dev table: history doc §6.
- `prblm_builder/blocks/` — **optional** app with the 21 built-in blocks (`sections/`), Theme
  + Headers/Footers (snippets) + Builder page (`models.py`, `fields.py`), `{% prblm_assets %}` etc.
  (`templatetags/prblm_blocks.py`), self-contained `blocks.css`/`blocks.js`. The core must
  never import it; it plugs in via hooks (`register_prblm_builder_menu_item`,
  `prblm_builder_chrome`, `prblm_builder_chrome_for_page`).
- `tests/` + `runtests.py` — the bundled test project (not shipped); CI in `.github/workflows/`.

## Conventions / gotchas (learned the hard way)
- **Django templates:** never use `{# … #}` for multi-line comments — they render as
  visible text. Use `{% comment %}…{% endcomment %}`.
- **Data migrations** that read soon-to-be-removed fields must use `apps.get_model` (the
  historical model), not `from app.models import …`, or they silently convert nothing. A
  data migration that sets a page field must also `save_revision()` + `publish()`.
- **Preview iframes:** strip `loading="lazy"` server-side; set the iframe's own height; size
  sections from `body.scrollHeight` (not `documentElement.scrollHeight`). Frame views need
  `@xframe_options_sameorigin`.
- Some full-width / header-link / preview-coexist features depend on **Wagtail admin
  classes** and degrade gracefully — they're the first things to check on a new Wagtail
  version (switchable via `PRBLM_BUILDER_ADMIN_TWEAKS`).
- **Empty block values:** `block.get_default()` is `None` for text blocks and renders as
  "None" — use `layout.empty_value()`.
- **Adding a setting:** reader in `settings.py`, row in README "Settings reference" + history
  doc §6, CHANGELOG entry, a test in `tests/test_options.py`.
- **Built-in blocks are a promise:** block names, field names and class *module paths*
  (`prblm_builder.blocks.sections.*`) end up in sites' data and migrations — never rename
  or move; only add. Changing a block definition needs
  `python runtests.py makemigrations prblm_builder_blocks` (BuilderPage records them).
- **Wagtail quirks:** `ChoiceBlock` ignores `Meta.default` (set it in `__init__`); admin
  menus are built once (use `is_shown()` for setting-dependent items); list items get a
  fresh random `id` on every save (strip ids before comparing content).
- **Check CSS / JS in a real browser** — screenshot blocks with headless Chrome, and drive
  admin flows with Playwright (`channel="chrome"`) against a throwaway dev server (see the
  history doc); Django tests can't run the JS or see layout.

## Running / testing
`python runtests.py` runs `prblm_builder/tests/` against the bundled test project in
`tests/` (settings + `tests.testapp.StandardPage` with a `body` StreamField). CI
(`.github/workflows/test.yml`) runs it on Python 3.12–3.14 and checks the wheel builds.
Target stack: **Wagtail 8.1+ (<9), Django 6.1+, Python 3.12+** (latest stable as of v0.3.0).

## Current state
Latest release **v0.4.1** (plan + log in `plan.md`; older plans in `docs/plans/`). Install in another project
with `pip install "prblm-builder @ git+ssh://git@github.com/prblmcodes/prblm-builder.git@<tag or branch>"`.
Tests: `prblm_builder/tests/` (generic, shipped) + `tests/test_options.py` (needs the
edge-case blocks in `tests/testapp`).
Remaining roadmap in the history doc §9.

## Note on the raw transcript
`.history/` (gitignored) may hold the raw build-session transcript from the host project.
It's large and contains host-site infra details — **keep it out of git and don't share it.**
Use `docs/DEVELOPMENT_HISTORY.md` as the shareable record.
