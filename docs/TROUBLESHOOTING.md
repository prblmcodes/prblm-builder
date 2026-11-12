# Troubleshooting

Find the symptom under its topic. Still stuck? Open the **Block library** — blocks that
can't be previewed are listed at the bottom with the reason — and check the
[Feature guide](GUIDE.md).

- [Installing and upgrading](#installing-and-upgrading)
- [The Layout tab and saving](#the-layout-tab-and-saving)
- [Which blocks show up](#which-blocks-show-up)
- [Previews and the canvas](#previews-and-the-canvas)
- [Demo content and the Block library](#demo-content-and-the-block-library)
- [Built-in blocks](#built-in-blocks)
- [Fixed in older versions — upgrade](#fixed-in-older-versions--upgrade)

## Installing and upgrading

| Symptom | Likely cause / fix |
|---|---|
| `pip install` leaves the old version | Same version number already installed → add `--force-reinstall --no-deps`. |
| `pip` wants to upgrade (or refuses) Wagtail/Django | Fixed in 0.9.0: the plugin only needs Wagtail 7.0+. Upgrade the plugin. |
| `ImportError … BlockGroup` / `No module named 'wagtail.admin.telepath'` / `NodeNotFoundError … 0098_apitoken` | Wagtail older than 8.1 with plugin 0.8 or earlier → upgrade to 0.9.0. |
| Canvas blank on a server | `collectstatic` not run. |
| Warning `prblm_builder.W001` | Remove `PRBLM_BUILDER_SEED_NEW_BLOCKS` from your settings. |
| Error importing `builder_blocks` / `No installed app with label 'prblm_builder_blocks'` | Add `"prblm_builder.blocks"` and `"wagtail.contrib.settings"` to `INSTALLED_APPS`, then `migrate`. |
| Error `prblm_builder_blocks.E001` on startup | Add `"wagtail.contrib.settings"` to `INSTALLED_APPS`. |
| `makemigrations` wants to alter my page's `body` after upgrading to 0.5 | Expected if you use `builder_blocks()`: the built-in link fields changed. Run it; no data changes. |

## The Layout tab and saving

| Symptom | Likely cause / fix |
|---|---|
| No Layout tab on a page type | Its StreamField isn't called `body` → set `PRBLM_BUILDER_FIELD_NAMES`, or check `PRBLM_BUILDER_PAGE_MODELS`. |
| New sections don't appear in the Content tab | Save the page first (use **Save draft now** in the banner) — the Content tab only shows saved sections. |
| "Couldn't save automatically — your layout isn't saved yet" | Wagtail's auto-save was refused (often another tab saved a newer version). Click **Save draft**; reload first if Wagtail says the page changed. |
| "This page is still called 'Untitled page N'" when publishing | The page still has the placeholder title from **Save draft now** — click **Rename it**, or **Publish anyway**. |
| Clicking **Publish** on an "Untitled page" does nothing | Fixed in 0.10.0 (the question used the browser's confirm box, which a browser can block silently). Upgrade. |
| The editor always reopens on the Layout tab after saving | Fixed in 0.10.0: it reopens the tab you saved from. |
| The Content tab shows old sections for a moment after changing the layout | Fixed in 0.10.0: it shows "Loading the new sections…" until the editor reloads. |
| Sections added or deleted in the Content tab don't show in the Layout tab | Fixed in 0.10.0. On Wagtail 7.0 (no auto-save) save the page first — the bar on the Layout tab offers **Save draft now**. |
| `/admin/page-builder/page/<id>/` opens the page editor | Expected since 0.9.0: the separate full-screen builder was removed — use the **Layout** tab. |
| Paste is greyed out in the right-click menu | Copy a section first — copy & paste work within the same page. |
| Wagtail's preview doesn't seem to show a new section | It was added where you dropped it — scroll the preview. On a long page it's often below the visible part. |

## Which blocks show up

| Symptom | Likely cause / fix |
|---|---|
| A block is missing from the palette | It has no `template`, or it's hidden (`builder = False`, `PRBLM_BUILDER_EXCLUDE_BLOCKS`, template prefix). |
| A non-section block (link, button) shows up | It's a top-level option of a page `body` field → hide it with `builder = False` or `PRBLM_BUILDER_EXCLUDE_BLOCKS`. |
| `PRBLM_BUILDER_EXCLUDE_BLOCKS` has no effect | You used a bare class name (`"LinkBlock"`) — use the StreamField name (`"link"`) or the full path (`"core.blocks.LinkBlock"`). See [Hiding a block](GUIDE.md#hiding-a-block). |
| My blocks are all listed under "Other" | Give them a `group` (`class Meta: group = "Heroes"`) — see [Groups](GUIDE.md#groups). |
| No ⚙ button on my block's sections | List the fields in the block's `Meta.builder_settings` (only choice, on/off and short-text fields are shown). |
| My block's settings still show in the Content tab | Add `BuilderSettingsMixin` to the block to move them into Wagtail's collapsed settings area. |
| ⚙ fields show in the Content tab as well | Wagtail older than 8.1 has no collapsed settings area for blocks; both places work. |
| `PRBLM_BUILDER_SITE_BLOCK_COLUMNS = True` changes nothing | Hard-refresh the admin (Ctrl+Shift+R). Two columns apply to StructBlock forms; a plain text/rich-text block has a single field. |

## Previews and the canvas

| Symptom | Likely cause / fix |
|---|---|
| Previews are unstyled | `PRBLM_BUILDER_PREVIEW_CSS` not set or wrong path (relative to `static/`). |
| Fonts/colours differ from the site | Your CSS relies on `<body>` classes → set `PRBLM_BUILDER_PREVIEW_BODY_CLASS`. |
| A section is blank or half-faded on the canvas | A scroll / entrance animation that never fires in a preview: add `.prblm-canvas .your-class{opacity:1 !important;transform:none !important}` — see [Animations](GUIDE.md#animations-and-scroll-effects). |
| Clicking a link in a preview does nothing | Expected — previews don't navigate. Open the page itself (or Wagtail's preview) to follow links. |
| Previews of one site use another site's (or the global) CSS | Its hostname isn't a key in `PRBLM_BUILDER_PREVIEW_SITES`: use the Site's name or a wildcard (`"landing.*"`). The Block library's **Preview as** tabs mark sites with no match (\*). |
| `showModal is not defined` (Alpine) in previews, without a preview template | Set `PRBLM_BUILDER_PREVIEW_BODY_ATTRS = {"x-data": "{ showModal: false }"}`. |
| A tall section (`min-h-[70vh]`, `h-screen`) looks short or very tall on the canvas | Set `PRBLM_BUILDER_CANVAS_HEIGHT` to the screen height you design for (default 900). |
| The first section is hidden under my fixed header on a Builder page | It's padded automatically; if your header appears late (e.g. built by JS), set `:root{--prblm-header-offset:128px}` in your CSS. |
| Alpine errors (`showModal is not defined`) or missing `<body>` attributes in previews | Use a [preview template](GUIDE.md#your-own-preview-template) that extends your `base.html`. |
| Several sites, but previews use one site's CSS | Set per-site CSS / templates in [`PRBLM_BUILDER_PREVIEW_SITES`](GUIDE.md#several-sites). |
| A library or CDN script must load before mine / with `defer` / as a module | Order the list (it's the load order) and use dict entries — see [Scripts and stylesheets](GUIDE.md#scripts-and-stylesheets). |
| White header text invisible above the canvas | Fixed in 0.9.0: a transparent fixed header lies over the first section. With `PRBLM_BUILDER_CANVAS_OVERLAP = False` it's stacked on white — give it a background under `.prblm-canvas`. |
| A section's top is cut off, or it doesn't overlap the section above like on the page | Fixed in 0.9.0 (negative margins). Upgrade. |
| Analytics count page views from the editor | Previews render your template: skip tracking tags with `{% if not prblm_preview %}` or `request.is_prblm_preview` — see [docs/PREVIEWS.md](https://github.com/prblmcodes/prblm-builder/blob/main/docs/PREVIEWS.md#keep-analytics-and-seo-tags-out-of-previews). |
| `PRBLM_BUILDER_ADMIN_TWEAKS` seems to do nothing | Look in the **page editor**: Layout tab width and the "Block library" button in the top-right header. If that button never appears even with `True`, please open an issue. |
| Full-width tab / header link broke after a Wagtail upgrade | Set `PRBLM_BUILDER_ADMIN_TWEAKS = False` and open an issue. |

## Demo content and the Block library

| Symptom | Likely cause / fix |
|---|---|
| `/demo` gives 404 | The Block library lives under the admin: `/admin/page-builder/demo/`. |
| Block library 404 at the right address | `PRBLM_BUILDER_DEMO = False` is set. |
| Demo content shows "Section heading", "Button label"… | Expected when the block isn't used on any published page yet: neutral text so placeholder copy is easy to spot. Set `preview_value`, or publish a page that uses the block. |
| A "Builder placeholders" image collection appeared | Placeholder images shaped for banners / logos / photos, created when no library image fits a demo field. Delete them any time, or set `PRBLM_BUILDER_PLACEHOLDER_IMAGES = False`. |
| My `preview_value` has no image and the section still saves | Expected — missing fields are filled from real content or generated (images: a fitting library image or placeholder). |
| A block is listed under "Couldn't preview … doesn't pass the block's validation" | Even with the gaps filled, its demo content fails one of its own rules (the field is named). Usually a required field the plugin can't fill (e.g. a required image with placeholders off). |
| A "Not edited yet" section shows generic text though the block is used on my site now | Expected — a section is filled once, when added. Edit it in the Content tab (or remove it and add it again to get today's best content). |
| A block always shows under "Couldn't preview: … This field is required" | A field with a pattern no common value fits — give the block a `preview_value`. |
| `PRBLM_BUILDER_PLACEHOLDER_IMAGES` does nothing | Expected when your image library has images — it only applies to an empty library. |

## Built-in blocks

| Symptom | Likely cause / fix |
|---|---|
| Built-in blocks not in a page's palette | They must be in that page's StreamField: use the **Builder page**, or add `builder_blocks()` to your model and run `makemigrations` + `migrate`. |
| Your site's header looks unstyled on a Builder page | Set `PRBLM_BUILDER_PREVIEW_CSS` (and `_JS`) to your site's files — Builder pages load them when they show your site's header/footer. |
| No "Builder page" in *Add page* | `prblm_builder.blocks` not installed / not migrated, or `PRBLM_BUILDER_PAGE_TYPE = False`. |
| Theme changes don't affect my own blocks | Expected — the Theme only styles the built-in blocks. |
| Site-wide header not on my live pages | Add `{% load prblm_blocks %}{% prblm_header %}` to your base template (the Builder page shows it automatically). |
| Builder page only offered at the top level, not under Home | Your home page type restricts its children: add `PRBLM_BUILDER_PAGE_PARENTS = ["home.HomePage"]`. |
| `ImproperlyConfigured: PRBLM_BUILDER_PAGE_EXTRA_BLOCKS …` | A block path can't be imported, an entry isn't a `("name", "path")` pair, or a name clashes with a built-in block. The message says which. |
| A "Snippets" menu appeared | Headers and Footers are stored as snippets; Wagtail lists them there too. |
| Built-in blocks look unstyled on my own live pages | Add `{% load prblm_blocks %}` and `{% prblm_assets %}` to your `base.html` `<head>`, after your own CSS. |

## Fixed in older versions — upgrade

| Symptom | Likely cause / fix |
|---|---|
| My header / own blocks unstyled in Wagtail's **preview panel** but fine on the canvas | Fixed in 0.6.0 (the site's CSS was linked with the Wagtail Site's host name). Upgrade. |
| The same block appears twice in the Block library, or looks different on the Builder page | Fixed in 0.6.0 (blocks are now matched by class, not name). Upgrade. |
| The page won't save after adding a section (e.g. with wagtail-link-block or a `preview_value` missing a required field), no error visible | Fixed in 0.6.0 / 0.7.0 (demo content always passes the block's own validation). Upgrade; remove the section added before and add it again. |
| A new section copies content from a forgotten draft or demo page | Fixed in 0.7.0: real content comes only from published pages and edited sections. |
| A gap between the header and the first section on the canvas | Fixed in 0.6.0 (and for fixed headers in 0.7.0). Upgrade. |
| "Layout changed" appears after dragging a section and dropping it in the same place | Fixed in 0.7.0. |
| The Page tab names a template, but editing it doesn't change this page's header | Fixed in 0.8.0: when a page type decides its own header in code, the Page tab says so instead of naming the site template. |
| Gaps between sections on the canvas are bigger than on the page | Fixed in 0.8.0 (margins merge like on a page). Inside a flex / grid wrapper in your preview template they don't merge — like the live page. |
