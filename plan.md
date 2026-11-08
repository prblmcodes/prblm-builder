# Plan — v0.3.0: built-in blocks + "Page builder" admin section

Branch: `feature/builtin-blocks` · Status: **in progress** · Started 2026-11-08

This file tracks what we agreed to build and how far we are. Tick items as they land.

---

## 1. Goals

1. Ship **21 optional, ready-made section blocks** (incl. a generic Header and Footer) that
   work on any Wagtail site with **no extra CSS/JS to install** — everything they need
   lives inside the plugin.
2. Give the plugin its own **"Page builder" section in the admin sidebar**: Block library
   (built-in and site blocks grouped separately), Theme, and Header & footer.
3. Keep the core plugin **block-agnostic**: sites that don't enable the built-in blocks see
   no change apart from the new admin section.

## 2. Decisions (agreed)

| Topic | Decision |
|---|---|
| Scope | All 20 proposed blocks **+ Contact info** = 21 blocks, in v0.3.0. |
| Opt-in | Separate app `prblm_builder.blocks`; only active when added to `INSTALLED_APPS`. |
| Header / footer | Normal blocks **and** a site-wide Header & footer set once in the admin; always shown on the builder canvas; on the live site via optional `{% prblm_header %}` / `{% prblm_footer %}` template tags. |
| Admin | New sidebar section **"Page builder"** → *Block library*, *Theme*, *Header & footer*. Replaces Settings → Block library. Editor-header link stays. |
| Block library | One page, two groups: **Built-in blocks** and **Your site's blocks**. |
| Styling | Fully self-contained CSS shipped in the plugin, class prefix `pbk-`, driven by CSS variables. |
| Theme | Admin *Theme* page: brand colour, text colour, background colours, font, corner roundness, content width. Restyles every built-in block at once. |
| Backgrounds | Every section has a **background** choice: Light, Muted, Dark, Brand (all follow the Theme). |
| Font | Inherit the site's font, fall back to a system font stack; Theme page can set a font name. No font files shipped. |
| Content | New built-in blocks are **pre-filled with explanatory content** (e.g. "Your main headline — keep it under 8 words") set as the block's own defaults, so it also appears when added from the Content tab. |
| Icons | Built-in set of ~40 SVG icons shipped in the plugin, chosen from a dropdown. |
| Images | Empty image fields render **bundled SVG placeholders** labelled with purpose + size (e.g. "Hero image · 1600×900"). Nothing is added to the image library. |
| Header menu | Typed in the block: label + page / URL / anchor, with optional one-level dropdowns. |
| Header behaviour | Checkbox for sticky; mobile menu on small screens (a few lines of JS shipped in the plugin). |
| Page models | (a) Ready **"Builder page"** page type with all 21 blocks (hideable by a setting); (b) helper `builder_blocks()` for a site's own page models, next to its custom blocks. |
| Seeding setting | **Remove `PRBLM_BUILDER_SEED_NEW_BLOCKS`.** New blocks always start with content. Add a **"Not edited yet"** badge on canvas sections that still hold demo/default content. |
| Contact forms | Out of scope (needs storage, email, spam protection). Contact *info* block only. |

## 3. Things to know (constraints)

- **Built-in blocks don't appear in a page automatically.** Wagtail stores a page's
  allowed blocks in its StreamField definition, so a site either uses the ready
  "Builder page" type, or adds `builder_blocks()` to its own model **and runs a migration**.
- **Custom blocks can't be added to our "Builder page" via a setting** — the block list is
  recorded in our app's migrations; changing it from settings would make Django try to
  write migrations inside the installed package. Custom blocks go on the site's own page
  model with the helper.
- **Block names and fields are a promise.** Once released, renaming a block or a field
  breaks saved pages. Get them right before v0.3.0; afterwards only add, never rename.
- Theme / Header & footer need a database table → the blocks app ships **one migration**
  and needs `wagtail.contrib.settings` in `INSTALLED_APPS`.

## 4. How it will be used (target developer experience)

```python
# settings.py
INSTALLED_APPS = [
    "prblm_builder",
    "prblm_builder.blocks",        # optional: built-in blocks + Builder page + Theme
    "wagtail.contrib.settings",
    ...
]
```

```bash
python manage.py migrate           # creates the Theme / Header & footer table + Builder page
```

Then either create a **Builder page** in the admin, or use the blocks in your own model:

```python
from prblm_builder.blocks import builder_blocks

class LandingPage(Page):
    body = StreamField(builder_blocks() + [("my_block", MyBlock())], blank=True)
```

Optional, to use the site-wide header/footer on the live site (`base.html`):

```django
{% load prblm_blocks %}
{% prblm_header %}
...
{% prblm_footer %}
```

## 5. The blocks

Every section block also has: **background** (Light / Muted / Dark / Brand) and an
optional **anchor ID** (so menus can link to `#pricing` etc.). Links everywhere use one
shared link type: label + one of page / URL / anchor.

| # | Block | Purpose | Main fields |
|---|---|---|---|
| 1 | **Header** | Site top bar | logo, site name (if no logo), menu items (+ one-level dropdowns), button, sticky |
| 2 | **Footer** | Site bottom area | logo, short description, link columns, social links, copyright |
| 3 | **Hero** | Big page opener | eyebrow, headline, text, primary + secondary button, image, image position (side / background), alignment |
| 4 | **Page banner** | Title strip for inner pages | headline, intro, show breadcrumbs |
| 5 | **Text** | Formatted long text | rich text, width (narrow / wide), alignment |
| 6 | **Text + image** | Text beside an image | headline, rich text, button, image, image side (left / right) |
| 7 | **Features** | Grid of benefits | headline, intro, columns (2/3/4), items: icon, title, text |
| 8 | **Cards** | Services / projects / articles | headline, intro, columns, items: image, title, text, link |
| 9 | **Steps** | Numbered process | headline, intro, items: title, text (auto-numbered) |
| 10 | **Quote** | One highlighted quote | quote, author, role |
| 11 | **Testimonials** | Customer quotes | headline, items: quote, name, role, photo |
| 12 | **Logo strip** | Clients / partners | headline, items: logo, name, link; greyscale on/off |
| 13 | **Stats** | Big numbers | headline, items: number, label, note |
| 14 | **Call to action** | Conversion band | headline, text, primary + secondary button (default background: Brand) |
| 15 | **FAQ** | Expandable Q&A (no JS) | headline, intro, items: question, answer (rich text) |
| 16 | **Pricing** | Plan comparison | headline, intro, plans: name, price, period, description, features, button, highlighted |
| 17 | **Gallery** | Image grid | headline, columns, images: image, caption |
| 18 | **Video** | YouTube / Vimeo embed | headline, video URL, caption (embed built from the URL — no network call; privacy-friendly YouTube domain) |
| 19 | **Team** | People | headline, intro, members: photo, name, role, bio, link |
| 20 | **Divider** | Line or space | style (line / space), size (S / M / L) |
| 21 | **Contact info** | How to reach you | headline, intro, address, email, phone, opening hours, map link button; icons per row |

## 6. Technical approach

- **Package layout**
  ```
  prblm_builder/blocks/
    __init__.py         builder_blocks(), BUILTIN_BLOCKS
    apps.py             app config (label "prblm_builder_blocks")
    blocks/             one module per block family + shared LinkBlock, IconChoiceBlock, SectionBase
    models.py           ThemeSettings + SiteChrome (site settings), BuilderPage
    migrations/0001_initial.py
    templatetags/prblm_blocks.py   prblm_header, prblm_footer, prblm_assets
    templates/prblm_builder/blocks/*.html
    static/prblm_builder/blocks/   blocks.css, header.js, icons.svg (sprite), placeholders/*.svg
  ```
- **Self-contained assets.** Each block template calls `{% prblm_assets %}`, which emits the
  stylesheet link, the theme's CSS variables (`<style>:root{--pbk-brand:…}</style>`) and the
  header JS **once per page render** (tracked on the request). Works on the live site and in
  preview iframes with no setup.
- **Theme → CSS variables.** Theme values become `--pbk-*` variables; blocks.css uses only
  those. Sites can also override variables in their own CSS.
- **Pre-filled content** lives in each block's `Meta.default` / child defaults. The demo
  engine uses it for built-ins instead of synthesised text.
- **"Not edited yet" badge.** A section is "unedited" if its stored value still equals the
  block's default (built-ins) or the demo value it was seeded with (site blocks). The
  canvas shows a small badge on those sections. *(Known limit: for site blocks seeded from
  real content, a changed demo source may hide the badge — false negatives only.)*
- **Admin section.** A "Page builder" sidebar menu (Wagtail `register_admin_menu_item` +
  submenu). Theme and Header & footer edit views use Wagtail's site-settings machinery but
  are linked from this menu instead of the Settings menu.
- **Removing the seed setting.** Drop the reader + empty-start code paths; add a Django
  system-check **warning** if a project still sets `PRBLM_BUILDER_SEED_NEW_BLOCKS`.
- **Accessibility basics**: semantic HTML, alt text from images, keyboard-usable mobile
  menu and FAQ (`<details>`), sufficient contrast for the four backgrounds.

## 7. Phases (checklist)

- [x] **Phase 0 — Plan** — this file reviewed and agreed.
- [x] **Phase 1 — Core changes**
  - [x] Remove `PRBLM_BUILDER_SEED_NEW_BLOCKS` (+ system-check warning W001, docs, tests)
  - [x] "Not edited yet" badge on the canvas
  - [x] "Page builder" admin sidebar section; Block library moved there, grouped Built-in / Site
- [x] **Phase 2 — Blocks foundation**
  - [x] `prblm_builder.blocks` app skeleton, ThemeSettings model, migration, system checks
  - [x] `blocks.css` design system (tokens, layout, four backgrounds, buttons, typography)
  - [x] `{% prblm_assets %}` once-per-page asset tag (CSS + theme variables + JS)
  - [x] Icon set (50 line icons + 9 social marks) + IconChoiceBlock; SVG image placeholders
  - [x] Shared LinkBlock, BackgroundBlock, AnchorBlock; section base template
  - [x] Theme admin page (under Page builder, hidden from Settings)
- [x] **Phase 3 — Blocks, batch 1**: Header, Footer, Hero, Page banner, Text, Text + image,
      Features, Cards, Call to action, FAQ, Contact info
- [x] **Phase 4 — Blocks, batch 2**: Steps, Quote, Testimonials, Logo strip, Stats, Pricing,
      Gallery, Video, Team, Divider
- [x] **Phase 5 — Site-wide header & footer**: admin page, canvas integration,
      `{% prblm_header %}` / `{% prblm_footer %}`
- [x] **Phase 6 — Page models**: Builder page (+ hide setting), `builder_blocks()` helper
- [ ] **Phase 7 — Release**: tests for every block (render, defaults, no "None", a11y basics),
      README + history doc + CHANGELOG, version 0.3.0, merge to `main`, tag

## 8. Settled defaults (were open questions — change before release if needed)

1. **Block names** — plain (`hero`, `cards`, …). `builder_blocks(exclude=[…])` lets a site
   drop any that clash with its own; a duplicate name raises a clear error.
2. **Builder page hide setting** — `PRBLM_BUILDER_PAGE_TYPE = True` (False hides the type).
3. **Default theme** — neutral: near-black text, soft grey muted background, blue brand.

## 9. Progress log

- 2026-11-08 — Interview done; decisions recorded above. Plan drafted.
- 2026-11-09 — Plan agreed; open questions settled with the suggested defaults. Phase 1 started.
- 2026-11-09 — Phase 1 done (38 tests). Found + fixed: menu hooks are cached by Wagtail,
  so `PRBLM_BUILDER_DEMO = False` never hid the menu item → `is_shown()` subclass.
- 2026-11-09 — Phase 2 done (53 tests). Notes: Wagtail's ChoiceBlock ignores `Meta.default`
  (set it in `__init__`); block class *module paths* are recorded in sites' migrations, so
  `prblm_builder.blocks.sections.*` paths are now a promise like block names. Font
  fallback uses a zero-specificity `:where(html)` rule so any site font wins.
- 2026-11-09 — Phase 3 done (71 tests; checked visually at 1280px and 390px in headless
  Chrome). Found + fixed: (1) a site block and a built-in block with the same name (e.g.
  `hero`) collided in the Block library and in the real-content index — both are now
  keyed by name *and* kind (`?builtin=1` on library previews); (2) Wagtail gives list
  items a fresh random `id` on every save, so "Not edited yet" compared unequal — item ids
  are now ignored when comparing.
- 2026-11-09 — Phase 4 done: all 21 blocks exist (81 tests, checked visually). Video embeds
  are built from the URL (youtube-nocookie / Vimeo `dnt=1`), no network call; non-video
  links are rejected when saving.
- 2026-11-09 — Phase 5 done (88 tests). Core got a `prblm_builder_chrome` hook so the
  optional blocks app can supply the canvas header/footer without the core depending on
  it. Precedence: `PRBLM_BUILDER_HEADER/FOOTER_TEMPLATE` setting → site-wide Header &
  footer → none. Migrations squashed into one `0001_initial` (nothing released yet).
- 2026-11-09 — Phase 6 done (94 tests). Builder page renders as a standalone HTML page
  (site header + sections + site footer) so it works with zero site templates; sites can
  override `prblm_builder/blocks/builder_page.html`. `PRBLM_BUILDER_PAGE_TYPE` is read once
  at startup (sets `BuilderPage.is_creatable`). The shipped generic tests now pick a page
  model that has a `rich_text` block, so they still run when the blocks app is installed.
