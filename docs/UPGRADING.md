# Upgrading

1. Change the version you install (e.g. `@v0.9.1` → `@v0.10.0` in `requirements.txt`, or
   download the new release wheel) and install it.
2. Run `python manage.py migrate` (and `collectstatic` in production).
3. Restart the server. The plugin's CSS/JS are version-stamped, so browsers load the new
   files without a hard refresh.

If pip says the version is *already installed* (you installed the same version from a
wheel or a branch before), add `--force-reinstall --no-deps` — `--no-deps` keeps pip from
reinstalling Wagtail and Django too.

What changed in each version: [CHANGELOG.md](../CHANGELOG.md). Notes per version:

**0.9 → 0.10**
- No migrations, no setting changes — install and restart (hard-refresh the editor once).
- After Save draft / Publish the editor reopens the tab you saved from (it used to always
  open Layout).
- Publishing an "Untitled page N" asks in the editor instead of the browser's confirm box.
- Selected sections also show their padding (green), next to their margins (orange).
- Changes made in the Content tab (added, deleted, moved or edited sections) now show in
  the Layout tab — after Wagtail's auto-save, or on Wagtail 7.0 after you save.
- Demo content picks up newly published content at once, and is no longer re-read every
  minute while nothing changes.

**0.9.0 → 0.9.1**
- No migrations, no setting changes — install and restart.
- Optional: `python manage.py prblm_builder_cleanup` removes demo-content records left
  behind by pages deleted before 0.9.1 (`--dry-run` first to see how many).

**0.8 → 0.9**
- Run `python manage.py migrate` as usual (nothing new to apply; one migration's
  dependency was lowered so it also works on Wagtail 7.0 — safe for sites that already ran it).
- The package now only requires Wagtail (7.0+, below 9). If you installed 0.8 with
  `--no-deps` on an older Wagtail and patched it by hand, reinstall normally and drop the
  patches — they're included.
- The canvas now overlaps a transparent header and sections with negative margins like
  the live page. Prefer them stacked? `PRBLM_BUILDER_CANVAS_OVERLAP = False`.
- The Layout sidebar and Block library list the most used blocks first.
  `PRBLM_BUILDER_BLOCK_ORDER = "alpha"` keeps A–Z.
- The Block library's site chooser is now the **Preview as** tabs and only appears with
  more than one Wagtail Site.
- `PRBLM_BUILDER_LIBRARY_SCOPE = "all"` no longer lists blocks of snippets, settings and
  menu apps — only page types.
- The full-screen builder at `/admin/page-builder/page/<id>/` (unlinked since 0.2) is gone:
  that address opens the page editor, and its separate save endpoint was removed — pages
  are saved only through Wagtail's Save draft / Publish.
- Preview requests have `request.is_prblm_preview = True`; see
  [Keep analytics out of previews](https://github.com/prblmcodes/prblm-builder/blob/main/docs/PREVIEWS.md#keep-analytics-and-seo-tags-out-of-previews).

**0.7 → 0.8**
- No migrations, no required changes — install the new version and restart.
- Previews now have `class="prblm-canvas"` on `<html>`, and animations / transitions run
  instantly in them (`PRBLM_BUILDER_REDUCE_MOTION = False` to keep them).
- Gaps between sections on the canvas now merge like on a page (they used to add up), so
  sections may sit closer together than in 0.7 — that's the live spacing.
- `PRBLM_BUILDER_PREVIEW_SITES` keys may now be site names or wildcards; exact hostnames
  keep working.
- If you override `builder_page.html`, add `{% prblm_site_html_attrs %}` to `<html>` and
  `{% prblm_site_body_attrs %}` to `<body>` to get the new attribute settings there.

**0.6 → 0.7**
- Run `python manage.py migrate` — the plugin now has one small table (`SeededSection`) to
  remember which sections hold its own demo content.
- New sections get **neutral** demo text ("Section heading", "Button label") instead of
  sample marketing copy, and images that fit each field. Sections already saved keep their
  content; ones 0.6 seeded and nobody edited are still recognised as "Not edited yet".
- Demo content is only borrowed from **published** pages now (not drafts), and never from
  untouched demo sections.
- A "Builder placeholders" image collection may appear (placeholders shaped for banners,
  logos and photos, created only when no library image fits). Turn it off with
  `PRBLM_BUILDER_PLACEHOLDER_IMAGES = False`.
- Builder pages wrap the header in `<div class="prblm-header-slot">` and pad `<main>` by a
  fixed header's height. If you override `builder_page.html`, copy that part.
- Two-column forms switch to one column below 720px of form width (was 560px).
- Optional new settings: `PRBLM_BUILDER_CANVAS_HEIGHT`, `PRBLM_BUILDER_PREVIEW_TEMPLATE`,
  `PRBLM_BUILDER_PREVIEW_SITES`; dict entries in `PRBLM_BUILDER_PREVIEW_CSS` / `_JS`.

**0.5 → 0.6**
- No migrations, no setting changes needed — just install the new version (with
  `--force-reinstall` if you tested a 0.6.0 wheel or branch before) and restart.
- The **Layout** tab is now the first tab in the page editor.
- The built-in blocks' forms use two columns. Want it for your own blocks too?
  `PRBLM_BUILDER_SITE_BLOCK_COLUMNS = True`.
- Builder pages that show your site's header/footer, or contain your own blocks, now load
  your site's CSS/JS (`PRBLM_BUILDER_PREVIEW_CSS` / `_JS`) — so make sure those are set.
- Built-in blocks are now shielded from your site's global CSS. If you relied on a site rule
  changing a built-in block (other than fonts, which they still inherit), use the Theme or
  your own block instead.
- Your blocks in `PRBLM_BUILDER_PAGE_EXTRA_BLOCKS` no longer need the same names as on your
  other page types to share demo content.

**0.4 → 0.5**
- Run `python manage.py migrate` (migration `0003_link_types` only updates the built-in
  blocks' stored definitions — no content changes).
- If you use `builder_blocks()` in your own page models, run `python manage.py
  makemigrations` once: it records the new link fields as an "Alter field" (no data change).
- Existing links keep working: their link type is worked out from what they contain.
- Builder pages: the header/footer choice moved from the Content tab to the Layout
  sidebar's **Page** tab.
- Sections added with 0.4's example content may lose their "Not edited yet" badge (the
  example links changed shape). Nothing else changes.

**0.3 → 0.4**
- Run `python manage.py migrate`. Your 0.3 **Header & footer** content moves
  automatically into **Page builder → Headers / Footers**, marked as the site default.
- `{% prblm_header %}` / `{% prblm_footer %}` keep working (they show the site default).
- Builder pages get *Header* / *Footer* options; existing ones use **Site default**, so
  nothing changes on your site.
- New optional settings: `PRBLM_BUILDER_PAGE_PARENTS`, `PRBLM_BUILDER_PAGE_EXTRA_BLOCKS`.

**0.2 → 0.3**
- `PRBLM_BUILDER_SEED_NEW_BLOCKS` was removed: new blocks always start with content and
  the canvas marks them **"Not edited yet"**. Delete the setting (a startup warning,
  `prblm_builder.W001`, reminds you).
- The Block library moved from *Settings* to the new **Page builder** sidebar section.
- The built-in blocks are new and optional — nothing changes unless you add
  `prblm_builder.blocks`.
