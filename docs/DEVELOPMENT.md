# Development

## Project structure

```
prblm_builder/                  the installable Django app
  apps.py                       on startup → integration.autoenable()
  integration.py                adds the Layout tab + save form to every enabled page model
  panels.py                     LayoutBuilderPanel — the Layout tab (embeds the builder iframe)
  forms.py                      LayoutBuilderForm — applies the arrangement on Save/Publish
  layout.py                     reconcile() — merges arrangement + content; new-block values
  registry.py                   finds page models + blocks; palette/library lists; hiding rules
  demo.py                       demo content, field by field (preview_value → real → default → generated)
  cleanup.py                    removes demo-content records of deleted pages' sections
  management/commands/          prblm_builder_cleanup (leftover demo-content records)
  previews.py                   preview HTML frame, asset tags, trimming, "Not edited yet"
  sites.py                      per-site preview settings (PRBLM_BUILDER_PREVIEW_SITES)
  compat.py                     imports that differ between Wagtail versions (7.0 – 8.x)
  models.py, migrations/        SeededSection — sections the plugin filled with demo content
  views.py                      builder (the Layout tab's canvas), builder_new, preview, demo (Block library)
  wagtail_hooks.py              admin URLs + the "Page builder" sidebar section
  settings.py                   reads every PRBLM_BUILDER_* setting (with defaults)
  assets.py                     the installed version (stamped on the plugin's CSS/JS URLs)
  checks.py                     startup warnings (e.g. removed settings)
  mixins.py                     BuilderSettingsMixin (⚙ settings → Wagtail's settings area)
  chrome.py                     header/footer around the canvas (template setting / hooks)
  templates/prblm_builder/      builder.html (canvas), layout_panel.html (tab), demo.html (library)
  templatetags/prblm_builder_tags.py   {% prblm_static %} — static URL + ?v=<version>
  static/prblm_builder/         builder.js, builder.css, fold.js, vendor/sortable.min.js,
                                frames.js (measuring frames, margins, overlap), form-columns.js/.css
                                (two-column forms), form-columns-site.css
  tests/test_builder.py         generic tests — also runnable inside a host project
  blocks/                       optional app "prblm_builder.blocks" (built-in blocks)
    __init__.py                 builder_blocks() helper
    sections/                   the 21 blocks: site, heroes, content, conversion, media, utility
      base.py                   shared LinkBlock, BackgroundBlock, AnchorBlock, icon choice
    models.py                   ThemeSettings, SiteHeader, SiteFooter, BuilderPage
    fields.py                   Builder page body: built-ins + PRBLM_BUILDER_PAGE_EXTRA_BLOCKS
    theme.py                    theme values → CSS variables
    chrome.py                   which header/footer a page shows
    icons.py                    the built-in line icons
    templatetags/prblm_blocks.py  prblm_assets, prblm_header/footer, pbk_icon, pbk_image
    templates/prblm_builder/blocks/  one template per block + builder_page.html
    static/prblm_builder/blocks/     blocks.css, blocks.js, link-block.js (link type switch)
    wagtail_hooks.py            Theme / Headers / Footers menu items, canvas header/footer
tests/                          test project for this repo (not shipped)
  settings.py, urls.py          minimal Wagtail settings
  testapp/                      StandardPage + edge-case blocks; BlocksPage (built-ins)
  test_options.py               settings and Block library rules
  test_blocks*.py, test_site_chrome.py, test_builder_page.py   built-in blocks
  test_save_flow.py, test_page_options.py   save banner, folding, page placement, extra blocks
  test_v05.py                   preview values, links, ⚙ settings, copy/paste, Page tab, drafts
  test_v06.py, test_v06_fixes.py   tab order/sync, forms, site assets, demo content matching
  test_v07.py                   demo content chain, per-site previews, preview template, ⚙ checks
  test_v08.py                   preview marker, attributes, site matching, release workflow
  test_v09.py                   older Wagtail, overlap, demo values, usage order, site tabs, cleanup
  test_v091.py                  demo-content records removed with their page; cleanup command
  test_v010.py                  publish question, tab after save, Content cover, padding, fill hint
  examples/, test_examples.py   the code from docs/EXAMPLES.md, checked
runtests.py                     runs all tests against tests/
.github/workflows/test.yml      CI: tests on Python 3.12–3.14 (latest Wagtail) and Wagtail 7.0 + wheel check
.github/workflows/release.yml   on a v* tag: test, build, attach wheel + sdist to the release
README.md                       what it is, quick start, where to read next
docs/GUIDE.md                   feature guide: every feature, one at a time
docs/SETTINGS.md                every PRBLM_BUILDER_* setting
docs/TROUBLESHOOTING.md         symptoms and fixes, by topic
docs/UPGRADING.md               notes per version
docs/DEVELOPMENT.md             this file
docs/EXAMPLES.md                copy-paste models and blocks for every feature
docs/PREVIEWS.md                step by step: make previews match your site
docs/DEVELOPMENT_HISTORY.md     architecture, design decisions, bugs + lessons, roadmap
docs/plans/                     the plan behind each release
CHANGELOG.md                    what changed in each release
```

## Working on the plugin

```bash
git clone git@github.com:prblmcodes/prblm-builder.git
cd prblm-builder
python -m venv .venv && source .venv/bin/activate
pip install -e .
python runtests.py                                   # all tests
python runtests.py tests.test_options                # one module
python runtests.py makemigrations                    # after changing tests/testapp/models.py
python runtests.py makemigrations prblm_builder_blocks   # after changing the built-in blocks
python runtests.py makemigrations prblm_builder          # after changing prblm_builder/models.py
```

New migrations: `makemigrations` makes them depend on the newest `wagtailcore` migration
of your Wagtail. Lower that to `('wagtailcore', '0094_alter_page_locale')` by hand (a test
fails otherwise), so the plugin keeps installing on Wagtail 7.0.

Inside a host project you can also run the generic tests against its own models:
`python manage.py test prblm_builder` (needs a page model whose StreamField has a
`rich_text` block).

Releasing: bump `version` in `pyproject.toml`, add a `CHANGELOG.md` entry, commit, then
`git tag -a vX.Y.Z -m "…" && git push origin main vX.Y.Z`. The **Release files** workflow
tests the tag, checks it matches the version, builds the wheel and source archive and
attaches them to the GitHub release (creating a draft if there's none yet) — write the
notes and publish it.

The design record — architecture, every decision, bugs and lessons, roadmap — is
[DEVELOPMENT_HISTORY.md](DEVELOPMENT_HISTORY.md); the plan behind each release is in
[plans/](plans/).
