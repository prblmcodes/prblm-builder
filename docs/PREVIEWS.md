# Set up previews for your site

The Layout canvas, the sidebar thumbnails and the Block library show each section in its own
small page. Out of the box that page loads only your CSS / JS files. This guide makes it
behave like your real pages: same `<head>`, same fonts, same `<body>` state, per site.
Allow 20–30 minutes for a typical project. Every step is optional — stop when the canvas
matches.

All settings go in your Django settings file (the one with `INSTALLED_APPS`). Restart the
server after changing them.

---

## 1. Put the parts previews must leave out into blocks

Previews should show your page **without** its header, footer, cookie banner, modals,
Wagtail's user bar, **analytics / tracking scripts** and SEO tags (the canvas shows the
header and footer separately; tracking in previews would count a page view for every
section an editor looks at). Wrap each of them in a `{% block %}` in your base template, so
a preview template can empty them:

```django
{# templates/base.html #}
<body class="…" x-data="{ showModal: false }">
  {% block wagtail_userbar %}{% wagtailuserbar %}{% endblock %}
  {% block site_header %}{% include "partials/_header.html" %}{% endblock %}
  <main>{% block content %}{% endblock %}</main>
  {% block site_footer %}{% include "partials/_footer.html" %}{% endblock %}
  {% block modals %}{% include "partials/_modals.html" %}{% endblock %}
  {% block cookie_banner %}{% include "partials/_cookies.html" %}{% endblock %}
</body>
```

Your live pages don't change: a block with content renders exactly as the include did.

### Keep analytics and SEO tags out of previews

Instead of a block, you can also wrap them in a check — previews set `prblm_preview` in the
template and `request.is_prblm_preview` on the request (handy inside your own template tags):

```django
{% if not prblm_preview %}
  {% include "partials/_analytics.html" %}
  <meta property="og:title" content="{{ page.seo_title|default:page.title }}">
{% endif %}
```

```python
# a template tag or context processor of yours
if getattr(request, "is_prblm_preview", False):
    return ""          # no tracking in builder previews
```

`prblm_preview` exists in the preview template (step 2); `request.is_prblm_preview` in
every preview, with or without one.

## 2. Create a preview template

```django
{# templates/prblm_preview.html #}
{% extends "base.html" %}
{% block wagtail_userbar %}{% endblock %}
{% block site_header %}{% endblock %}
{% block site_footer %}{% endblock %}
{% block modals %}{% endblock %}
{% block cookie_banner %}{% endblock %}
{% block content %}{{ prblm_section }}{% endblock %}
```

```python
PRBLM_BUILDER_PREVIEW_TEMPLATE = "prblm_preview.html"
```

Previews now get your real `<head>` (CSS, fonts, inline scripts, **inline `<style>`
with your colour variables**), your `<body>` attributes and your wrappers — no need to
copy inline styles into `PRBLM_BUILDER_PREVIEW_CSS` and keep two copies in sync. The template gets `page` (the page being edited, when there is one),
`request`, and `prblm_preview` (always `True`) if you want to change something only in
previews. The canvas measures just the section, so padding around `{{ prblm_section }}`
(e.g. under a fixed header) doesn't add space.

Show your header and footer around the canvas too:

```python
PRBLM_BUILDER_HEADER_TEMPLATE = "partials/_header.html"
PRBLM_BUILDER_FOOTER_TEMPLATE = "partials/_footer.html"
```

## 3. One profile per site

If your project has several Wagtail sites with different CSS builds, fonts or headers, give
each its own settings. Anything a profile doesn't set comes from the global settings.

```python
_PROFILES = {
    "main": {
        "template": "prblm_preview.html",
        "css": ["css/main.css"],
        "js": ["https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"],
        "header_template": "partials/_header.html",
        "footer_template": "partials/_footer.html",
    },
    "landing": {
        "template": "landing/prblm_preview.html",
        "css": ["landing/css/main.css"],
        "js": [{"inline": "document.documentElement.classList.add('js');"}],
    },
}
PRBLM_BUILDER_PREVIEW_SITES = {
    "Main": _PROFILES["main"],            # the Site's name (Settings → Sites)
    "landing.*": _PROFILES["landing"],    # or a wildcard on the hostname
}
```

A key matches a Wagtail Site by, in this order: `"hostname:port"`, `"hostname"`, the Site's
**name**, then **wildcards** (`landing.*`, `*.example.com`). Site names and wildcards work
on every environment (local, staging, production) without listing each hostname. A site
that matches nothing uses the global settings: the Block library's Site switcher says
"uses the default preview settings" next to it, and the server log warns once.

## 4. Alpine.js and other `<body>` state

Sections that use state set on `<body>` — `@click="showModal = true"` with
`<body x-data="{ showModal: false }">` — need that state in previews too.

- **With a preview template** (step 2) you already have it: the template keeps your
  `<body>`.
- **Without one**, set the attributes:

  ```python
  PRBLM_BUILDER_PREVIEW_BODY_ATTRS = {"x-data": "{ showModal: false }"}
  PRBLM_BUILDER_PREVIEW_HTML_ATTRS = {"data-theme": "light", "lang": "en"}
  # or per site: "body_attrs" / "html_attrs" in a PRBLM_BUILDER_PREVIEW_SITES profile
  ```

  They also go on published Builder pages that show your header/footer or contain your
  own blocks. With a preview template they're ignored (the template owns `<body>`).

Load order matters: the JS list loads in order, so put Alpine plugins before Alpine, and
config that must run first as `{"inline": "…"}` at the top.

## 5. Animations and scroll effects

Previews are still pictures, and scroll-triggered effects often never fire in them (the
frame is scaled, not scrolled), leaving sections blank or half-faded.

- Every preview has `class="prblm-canvas"` on `<html>`.
- `PRBLM_BUILDER_REDUCE_MOTION = True` (the default) makes CSS animations and transitions
  finish instantly inside previews.
- Elements **hidden until a script adds a class** (scroll-reveal, AOS, Alpine
  `x-intersect`) still need one rule from you — show them in previews:

  ```css
  .prblm-canvas .reveal,
  .prblm-canvas [data-aos] { opacity: 1 !important; transform: none !important; }
  ```

  Put it in your CSS, or in the preview template:
  `{% if prblm_preview %}<style>…</style>{% endif %}`.

## 6. Transparent headers and overlapping sections

Nothing to set up. The canvas lies a **transparent fixed / absolute header** over the first
section (as on the page at the top of the screen), and shows sections pulled over a
neighbour by **negative margins** overlapping it. If the header should look solid on the
canvas, give it a background under `.prblm-canvas`:

```css
.prblm-canvas .site-header { background: #0f172a; }
```

To stack everything instead: `PRBLM_BUILDER_CANVAS_OVERLAP = False` (or
`"canvas_overlap": False` in one site's profile).

## 7. Page types with their own header and footer

When a page type renders its own header and footer (e.g. from its StreamFields), tell the
canvas with the `prblm_builder_chrome_for_page` hook. Return the HTML, `""` for "none", or
`None` for "not mine" (the settings decide):

```python
# yourapp/wagtail_hooks.py
from django.template.loader import render_to_string
from wagtail import hooks


@hooks.register("prblm_builder_chrome_for_page")
def landing_chrome(kind, request, page, model):
    page_type = model or type(page)
    if page_type.__name__ != "LandingPage":
        return None                                    # not mine
    if page is None:                                   # a new, unsaved page
        return ""
    template = "landing/_header.html" if kind == "header" else "landing/_footer.html"
    return render_to_string(template, {"page": page}, request=request)
```

## 8. Good to know

- Links and forms inside previews don't do anything when clicked (the canvas is a picture,
  not a browser); scripted buttons — Alpine `@click`, menus, accordions — still work.
- Select a section on the canvas to see its margins as striped "Space" bands.

## 9. Check it

Open a page with several sections in the editor and compare the **Layout** canvas with
Wagtail's **Preview** panel:

- [ ] fonts and colours match (else: CSS order, `body_class`, the preview template);
- [ ] the gaps between sections match (the canvas merges margins like a normal page; inside
      a flex / grid wrapper it doesn't, like the live page);
- [ ] a transparent header and overlapping sections look as on the page (step 6);
- [ ] tall sections (`70vh`, `h-screen`) look right (`PRBLM_BUILDER_CANVAS_HEIGHT`, default 900);
- [ ] animated or script-driven parts are visible (step 5);
- [ ] buttons using Alpine state don't show errors in the browser console (step 4);
- [ ] the header and footer above / below the canvas are right for each page type (steps 2, 7);
- [ ] no analytics hits / tracking requests from previews (step 1);
- [ ] each site in the Block library's Site switcher uses its own styles (step 3).

The canvas can't copy everything: sections are separate frames, so CSS that styles one
section by its neighbour (`section + section`), or a script that reads the next section
(e.g. colouring a wave with the next section's background), can't work there. Overlaps by
negative margins do work (step 6).
