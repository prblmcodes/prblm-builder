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
`layout.reconcile`). Ships a Block library (demo page) with demo content chosen field by
field (preview_value → real site content of the same block → default → neutral generated).

## Where things live
- `prblm_builder/integration.py` + `panels.py` — auto-attaches the Layout tab + save form.
- `prblm_builder/forms.py` + `layout.py` — the ride-along save + reconciliation; new-block
  values (always demo content; "Not edited yet" detection lives in `previews.is_unedited`).
- `prblm_builder/registry.py` — finds models/blocks; palette + Block library lists; hiding
  rules (`Meta: builder = False`, `PRBLM_BUILDER_EXCLUDE_BLOCKS`).
- `prblm_builder/demo.py` — demo content, field by field (preview_value → real → default → generated, then `clean()`); `models.py` `SeededSection` records the plugin's own demo sections.
- `prblm_builder/previews.py` — iframe frame (+ preview template, asset tags), trimming, "Not edited yet"; `sites.py` — per-site preview settings.
- `prblm_builder/views.py` — builder (the Layout tab's canvas, `?embed=1`; alone it redirects to the editor) / builder_new / preview / demo. Pages are saved only through Wagtail's edit form.
- `prblm_builder/static/prblm_builder/builder.{js,css}` — the canvas (SortableJS, scaled iframes, undo/redo, overlap); `frames.js` — measuring preview frames: margins, negative-margin overlaps, transparent headers (shared with the Block library); `fold.js` — foldable groups.
- `prblm_builder/static/prblm_builder/form-columns.{js,css}` — two-column block forms
  (CSS does the layout; JS only marks unpaired fields; built-ins = `pbk-form` class, site
  blocks via `PRBLM_BUILDER_SITE_BLOCK_COLUMNS` + `form-columns-site.css`). Tab sync lives
  in `layout_panel.html`.
- `prblm_builder/chrome.py` — header/footer around the canvas (hooks → template setting → default).
- `prblm_builder/mixins.py` — `BuilderSettingsMixin` (⚙ settings → Wagtail's settings area).
- `prblm_builder/settings.py` — one reader per `PRBLM_BUILDER_*` setting (all optional).
  User-facing reference: `docs/SETTINGS.md`; dev table: history doc §6.
- `prblm_builder/blocks/` — **optional** app with the 21 built-in blocks (`sections/`), Theme
  + Headers/Footers (snippets) + Builder page (`models.py`, `fields.py`), `{% prblm_assets %}` etc.
  (`templatetags/prblm_blocks.py`), self-contained `blocks.css`/`blocks.js`. The core must
  never import it; it plugs in via hooks (`register_prblm_builder_menu_item`,
  `prblm_builder_chrome`, `prblm_builder_chrome_for_page`, `prblm_builder_page_options`).
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
- **Adding a setting:** reader in `settings.py`, row in `docs/SETTINGS.md` (and the feature's part of `docs/GUIDE.md`) + history
  doc §6, CHANGELOG entry, a test in `tests/test_options.py`.
- **Built-in blocks are a promise:** block names, field names and class *module paths*
  (`prblm_builder.blocks.sections.*`) end up in sites' data and migrations — never rename
  or move; only add. Changing a block definition needs
  `python runtests.py makemigrations prblm_builder_blocks` (BuilderPage records them).
- **Migrations:** `makemigrations` makes them depend on the newest wagtailcore migration —
  lower it to `('wagtailcore', '0094_alter_page_locale')` and use
  `getattr(settings, "WAGTAIL_PAGE_MODEL", "wagtailcore.page")`, or Wagtail 7.0 sites can't
  migrate (`tests/test_v09.py` checks). Never change an already released migration's
  dependency to something newer.
- **Wagtail quirks:** `ChoiceBlock` ignores `Meta.default` (set it in `__init__`); admin
  menus are built once (use `is_shown()` for setting-dependent items); list items get a
  fresh random `id` on every save, empty text becomes `""` and rich text gains
  `data-block-key` (compare content via `previews._canon`); block **defaults** are part of
  the migration description; Wagtail 8.1 **auto-saves drafts** on form changes.
- **Always work on the draft:** load pages for the builder with `views._editing_page`
  (latest revision), never the published row.
- **Built-in block CSS:** every rule scoped to `.pbk…`; the shield at the top of
  `blocks.css` (`all:revert`, one class of specificity) must stay *before* the block rules.
  After CSS changes, compare all 21 blocks with/without a hostile site stylesheet.
- **Check CSS / JS in a real browser** — screenshot blocks with headless Chrome, and drive
  admin flows with Playwright (`channel="chrome"`) against a throwaway dev server (see the
  history doc); Django tests can't run the JS or see layout.

## Running / testing
`python runtests.py` runs `prblm_builder/tests/` against the bundled test project in
`tests/` (settings + `tests.testapp.StandardPage` with a `body` StreamField). CI
(`.github/workflows/test.yml`) runs it on Python 3.12–3.14 and checks the wheel builds.
Supported: **Wagtail 7.0+ (<9), Django from Wagtail (5.2+), Python 3.12+**. CI runs the
latest Wagtail and Wagtail 7.0. Version-dependent imports go in `prblm_builder/compat.py`.

## Current state
User docs: `README.md` = what it is + quick start (links are absolute GitHub URLs — it's
also the package page); `docs/GUIDE.md` = every feature in order; `docs/SETTINGS.md`,
`docs/TROUBLESHOOTING.md` (by topic), `docs/UPGRADING.md`, `docs/DEVELOPMENT.md`. Put new
user-facing docs in the matching file, not the README.
Latest release **v0.9.0** (plan in `docs/plans/v0.9.0.md`; earlier plans in `docs/plans/`). Preview setup guide for users: `docs/PREVIEWS.md`. Pushing a `v*` tag attaches the wheel to the GitHub release (`.github/workflows/release.yml`). Copy-paste usage examples:
`docs/EXAMPLES.md` — its code lives in `tests/examples/` (keep them identical). Install in another project
with `pip install "prblm-builder @ git+ssh://git@github.com/prblmcodes/prblm-builder.git@<tag or branch>"`.
Tests: `prblm_builder/tests/` (generic, shipped) + `tests/test_options.py` (needs the
edge-case blocks in `tests/testapp`).
Remaining roadmap in the history doc §9.

## Note on the raw transcript
`.history/` (gitignored) may hold the raw build-session transcript from the host project.
It's large and contains host-site infra details — **keep it out of git and don't share it.**
Use `docs/DEVELOPMENT_HISTORY.md` as the shareable record.
