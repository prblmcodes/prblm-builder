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
- `prblm_builder/integration.py` — auto-attaches the Layout tab + save form.
- `prblm_builder/forms.py` + `layout.py` — the ride-along save + reconciliation.
- `prblm_builder/previews.py` — demo content engine (real-instance → synth → trim) + iframe frame.
- `prblm_builder/views.py` — builder / builder_new / preview / demo / save.
- `prblm_builder/static/prblm_builder/builder.{js,css}` — the canvas (SortableJS, scaled iframes, undo/redo).
- `prblm_builder/settings.py` — all `PRBLM_BUILDER_*` settings (optional; see the history doc).

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
  version.

## Running / testing
`prblm_builder/tests/test_builder.py` runs against a **host** Wagtail project's models — it
can't run standalone yet. Setting up a tiny demo/test project + CI is roadmap item #1 (see
the history doc). Target stack: Wagtail ≥ 7, Django 5.2, Python 3.12.

## Current state
First version is done and running in the host site + on its staging server. This repo holds
the extracted package (`016dc51` initial commit). Immediate next steps: demo project + CI,
a LICENSE, then install into a second Wagtail project. Full roadmap in the history doc.

## Note on the raw transcript
`.history/` (gitignored) may hold the raw build-session transcript from the host project.
It's large and contains host-site infra details — **keep it out of git and don't share it.**
Use `docs/DEVELOPMENT_HISTORY.md` as the shareable record.
