# prblm-builder

A visual drag-and-drop **page builder** for Wagtail. It adds a **Layout** tab to the page
editor where you build a page by dragging your site's own StreamField blocks onto a canvas
— reorder, duplicate and delete sections with live previews at desktop size. Words and
images are still edited in the normal **Content** tab, and everything saves with Wagtail's
own **Save draft / Publish**.

- **Works with the blocks you already have** — it finds them itself; no block list to keep.
- **Attaches itself** to every page type with a `body` StreamField; no model changes.
- **Optional extras:** 21 ready-made section blocks (hero, features, pricing, FAQ…), a
  ready-made **Builder page** type, a **Theme** and reusable **Headers & Footers** — all
  self-contained, no Node or Tailwind needed.

## Requirements

- **Wagtail 7.0 or newer (below 9)** — the only requirement; it brings a matching Django
  (5.2+). Tested on Wagtail 7.0 LTS and the latest 8.x.
- Python 3.12+

## Quick start

About ten minutes, on any Wagtail site.

**1. Install** it in your project's virtual environment:

```bash
pip install "prblm-builder @ git+https://github.com/prblmcodes/prblm-builder.git@v0.9.0"
# private repo (uses your GitHub SSH key):
# pip install "prblm-builder @ git+ssh://git@github.com/prblmcodes/prblm-builder.git@v0.9.0"
```

Or download the wheel attached to the [GitHub release](https://github.com/prblmcodes/prblm-builder/releases)
and `pip install prblm_builder-0.9.0-py3-none-any.whl`. To keep it installed, put the same
`prblm-builder @ git+…@v0.9.0` line in `requirements.txt`.

**2. Add it to `INSTALLED_APPS`** (your settings file, e.g. `<project>/settings/base.py`):

```python
INSTALLED_APPS = [
    "prblm_builder",
    # … your apps, wagtail apps …
]
```

No URL changes needed — its admin pages register themselves through Wagtail hooks.

**3. Create its table:**

```bash
python manage.py migrate
```

**4. Make previews look like your site** — point them at your compiled CSS, and show your
header and footer around the canvas. Paths are what you'd write in `{% static '…' %}` and
`{% include '…' %}`:

```python
PRBLM_BUILDER_PREVIEW_CSS = ["css/main.css"]                # core/static/css/main.css
PRBLM_BUILDER_HEADER_TEMPLATE = "components/header.html"    # optional
PRBLM_BUILDER_FOOTER_TEMPLATE = "components/footer.html"    # optional
```

**5. Try it:** restart the server and open any page in the Wagtail editor — the **Layout**
tab opens first. Then open **Page builder → Block library** in the admin sidebar: it shows
every block with a preview, and lists any block that can't be previewed with the reason.

In production, run `python manage.py collectstatic` as usual.

**No Layout tab?** Your StreamField isn't called `body`: set
`PRBLM_BUILDER_FIELD_NAMES = ["content"]` (your field's name). **A block is missing?** It
needs its own `template`. More in [Troubleshooting](https://github.com/prblmcodes/prblm-builder/blob/main/docs/TROUBLESHOOTING.md).

## Next steps

Pick what you need — each links to its part of the [Feature guide](https://github.com/prblmcodes/prblm-builder/blob/main/docs/GUIDE.md).

| I want to… | Go to |
|---|---|
| Learn the Layout tab (adding, moving, copy & paste, the sidebar) | [Using the Layout tab](https://github.com/prblmcodes/prblm-builder/blob/main/docs/GUIDE.md#1-using-the-layout-tab) |
| Group my blocks, or hide some from the builder | [Which blocks show up](https://github.com/prblmcodes/prblm-builder/blob/main/docs/GUIDE.md#2-which-blocks-show-up) |
| Control the demo content new sections start with | [Demo content](https://github.com/prblmcodes/prblm-builder/blob/main/docs/GUIDE.md#4-demo-content) |
| Let editors change a section's background / anchor from the canvas | [Section settings (⚙)](https://github.com/prblmcodes/prblm-builder/blob/main/docs/GUIDE.md#5-section-settings-) |
| Make previews match my site exactly (fonts, Alpine, several sites) | [Previews](https://github.com/prblmcodes/prblm-builder/blob/main/docs/GUIDE.md#6-previews-that-match-your-site), step by step: [PREVIEWS.md](https://github.com/prblmcodes/prblm-builder/blob/main/docs/PREVIEWS.md) |
| Add ready-made sections, a Builder page, a Theme, Headers & Footers | [Built-in blocks](https://github.com/prblmcodes/prblm-builder/blob/main/docs/GUIDE.md#7-built-in-blocks-optional) |
| See a full setup for an existing site | [A complete setup](https://github.com/prblmcodes/prblm-builder/blob/main/docs/GUIDE.md#8-a-complete-setup-for-an-existing-site) |
| Copy working code for a feature | [EXAMPLES.md](https://github.com/prblmcodes/prblm-builder/blob/main/docs/EXAMPLES.md) |
| Look up a setting | [SETTINGS.md](https://github.com/prblmcodes/prblm-builder/blob/main/docs/SETTINGS.md) |

## Installing on servers

Pin a release so every server installs the same version:

- **From the git tag** — the server needs read access to the repository (a deploy key for
  the SSH URL, or a token in the HTTPS URL):

  ```text
  prblm-builder @ git+ssh://git@github.com/prblmcodes/prblm-builder.git@v0.9.0
  ```

- **From the release wheel** — every GitHub release has the wheel attached. Keep it in your
  project (e.g. `deploy/wheels/`); no GitHub access needed on the server:

  ```text
  prblm-builder @ file:./deploy/wheels/prblm_builder-0.9.0-py3-none-any.whl
  ```

  or `pip install --no-index --find-links deploy/wheels prblm-builder==0.9.0`.

After each upgrade run `python manage.py migrate` and `collectstatic`.

## Upgrading

Change the version (`@v0.8.0` → `@v0.9.0`), reinstall, `migrate`, restart. If pip says the
version is already installed, add `--force-reinstall --no-deps`. Notes for each version:
[UPGRADING.md](https://github.com/prblmcodes/prblm-builder/blob/main/docs/UPGRADING.md); what changed:
[CHANGELOG.md](https://github.com/prblmcodes/prblm-builder/blob/main/CHANGELOG.md).

## Documentation

| | |
|---|---|
| [Feature guide](https://github.com/prblmcodes/prblm-builder/blob/main/docs/GUIDE.md) | Every feature, one at a time |
| [Previews step by step](https://github.com/prblmcodes/prblm-builder/blob/main/docs/PREVIEWS.md) | Make the canvas match your site |
| [Examples](https://github.com/prblmcodes/prblm-builder/blob/main/docs/EXAMPLES.md) | Copy-paste models and blocks (checked by the tests) |
| [Settings](https://github.com/prblmcodes/prblm-builder/blob/main/docs/SETTINGS.md) | Every `PRBLM_BUILDER_*` setting |
| [Troubleshooting](https://github.com/prblmcodes/prblm-builder/blob/main/docs/TROUBLESHOOTING.md) | Symptoms and fixes, by topic |
| [Upgrading](https://github.com/prblmcodes/prblm-builder/blob/main/docs/UPGRADING.md) | Notes per version |
| [Changelog](https://github.com/prblmcodes/prblm-builder/blob/main/CHANGELOG.md) | What changed in each release |
| [Development](https://github.com/prblmcodes/prblm-builder/blob/main/docs/DEVELOPMENT.md) | Project structure, running the tests, releasing |

## License

MIT — see [LICENSE](https://github.com/prblmcodes/prblm-builder/blob/main/LICENSE).
