"""Admin views for the page builder.

Structure only: the builder writes the StreamField's *order and membership*; field
content is edited in Wagtail's normal editor. Existing blocks keep their stored value
across a reorder; newly added blocks are seeded with demo content.
"""
import json
import re

from django.apps import apps as django_apps
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import strip_tags
from django.views.decorators.clickjacking import xframe_options_sameorigin
from wagtail.models import Page

from . import chrome
from . import previews, registry
from . import settings as cfg


# ----------------------------------------------------------------- helpers
def _editing_page(page_id):
    """The page as the editor sees it: its latest revision (the draft), like Wagtail's own
    edit view — not the published row, which may be older."""
    page = _specific_page(page_id)
    try:
        return page.get_latest_revision_as_object()
    except Exception:
        return page


def _specific_page(page_id):
    try:
        page_id = int(page_id)
    except (TypeError, ValueError):
        raise Http404("Bad page id.")
    return get_object_or_404(Page, id=page_id).specific


def _can_edit(page, user):
    return page.permissions_for_user(user).can_edit()


def _sections(page, field_name):
    """Current blocks on the page as ``[{id, type, label}]`` in order."""
    out = []
    stream = getattr(page, field_name)
    raw_by_id = {str(d.get("id")): d.get("value") for d in stream.raw_data}
    for child in stream:
        out.append({
            "id": child.id,
            "type": child.block_type,
            "label": registry.block_label(child.block_type, child.block),
            # Still holds the demo content it was seeded with → "Not edited yet" badge.
            "unedited": previews.is_unedited(child.block, child.block_type,
                                             raw_by_id.get(str(child.id)), page.pk, child.id),
            # Current ⚙ settings (Meta.builder_settings), editable from the canvas.
            "settings": registry.settings_values(child.block, raw_by_id.get(str(child.id))),
        })
    return out


SWATCH_HOOK = "prblm_builder_swatch_colors"


def _swatch_colors(request):
    """Colours for the background swatches of built-in blocks — ``{"light": "#fff", …}``
    from ``prblm_builder_swatch_colors`` hooks (the blocks app answers with the current
    site's Theme). Empty when nothing provides them: swatches then show names only."""
    from wagtail import hooks
    colors = {}
    for fn in hooks.get_hooks(SWATCH_HOOK):
        try:
            colors.update(fn(request) or {})
        except Exception:
            continue
    return colors


def _settings_schema(stream_block, request=None):
    """``{block type: {"fields": [...], "defaults": {...}}}`` for blocks with ⚙ settings —
    the popover's form, and the starting values for a newly added section. Background
    swatches of built-in blocks carry the Theme's real colours; a site block's swatches
    don't (its own CSS decides what "dark" means)."""
    out = {}
    theme = None
    for name, block in stream_block.child_blocks.items():
        fields = registry.settings_schema(block)
        if not fields:
            continue
        for field in fields:
            if field.get("swatches") and registry.is_builtin(block):
                if theme is None:
                    theme = _swatch_colors(request)
                colors = {k: theme[k] for k, _l in field["choices"] if k in theme}
                if colors:
                    field["colors"] = colors
        try:
            start = block.get_prep_value(previews.demo_value(block, name, prefer_real=False))
        except Exception:
            start = {}
        out[name] = {"fields": fields, "defaults": registry.settings_values(block, start)}
    return out


def _apply_settings_preview(block, value, request):
    """Show unsaved ⚙ settings on the canvas: ``?settings={"background": "dark"}`` is
    applied to the previewed value (invalid values are simply ignored)."""
    raw = request.GET.get("settings")
    if not raw:
        return value
    from .mixins import builder_setting_names
    try:
        settings = json.loads(raw)
        allowed = set(builder_setting_names(block))
        prep = dict(block.get_prep_value(value))
        for name, v in settings.items():
            if name in allowed:
                child = block.child_blocks[name]
                prep[name] = child.get_prep_value(child.clean(child.to_python(v)))
        return block.to_python(prep)
    except Exception:
        return value


def _usage_site(site):
    """The site whose pages count for usage order — only when the project has several."""
    from . import sites
    return site if site is not None and sites.multi_site() else None


def _palette(stream_block, site=None):
    """The builder sidebar: ``[{kind, key, groups: [{group, key, blocks: [{type, label}]}]}]``
    — kinds (built-in / site) and groups each foldable by their ``key``, ordered by usage
    on ``site``'s pages (``PRBLM_BUILDER_BLOCK_ORDER``)."""
    from django.utils.text import slugify

    from . import demo as demo_mod
    out = []
    for kind, groups in registry.palette_sections(stream_block):
        groups = registry.order_by_usage(groups, lambda n, b: len(demo_mod.usage(n, b, site)))
        kkey = registry.KIND_KEYS[kind]
        out.append({"kind": kind, "key": kkey, "short": registry.KIND_SHORT[kind], "groups": [
            {"group": g, "key": f"{kkey}:{slugify(g)}",
             "blocks": [{"type": n, "label": lbl, "description": registry.block_description(b)}
                        for (n, b, lbl) in items]}
            for g, items in groups]})
    return out


def _render_block(block, value, request, page=None):
    # Mark the request as a preview so blocks that fill themselves with sample data
    # under preview (the common Wagtail convention) show demo content on the canvas.
    request.is_preview = True
    request.is_prblm_preview = True
    ctx = {"request": request, "sample_fill": True}
    if page is not None:
        ctx["page"] = page
    return block.render(value, context=ctx)


def _render_block_safe(block, value, request, page=None):
    try:
        return _render_block(block, value, request, page)
    except Exception as exc:
        return (f'<div style="padding:24px;font-family:sans-serif;color:#7a1010;'
                f'background:#fdecec">Preview unavailable: {type(exc).__name__}</div>')


_VISIBLE_TAGS = re.compile(r"<(img|picture|svg|video|iframe|canvas|object|embed|hr)\b", re.I)


def _is_blank(html):
    """True if rendered HTML shows nothing: no text and no media."""
    html = str(html or "")
    return not strip_tags(html).strip() and not _VISIBLE_TAGS.search(html)


def _demo_value(block_name, block, trim=True):
    """``(value, page)`` to preview a block with: a real instance used on the site
    (with its page, so hero-style blocks render fully), else synthesised content. The
    block's own Wagtail ``preview_value`` comes first. ``trim`` shortens long text for the
    Block library and thumbnails; a new section on the canvas isn't trimmed, so it shows
    exactly what will be saved (``layout.new_block_value``)."""
    def done(value):
        return previews.trim_for_demo(block, value) if trim else value
    from . import demo
    value, src_page = demo.build(block, block_name)
    return done(value), src_page


def _preview_problem(block_name, block, request):
    """Why a block can't be previewed on its own (``None`` if it can): it errors, or
    renders nothing with demo content (e.g. a link/button fragment)."""
    try:
        value, src_page = _demo_value(block_name, block, trim=False)
        html = _render_block(block, previews.trim_for_demo(block, value), request, src_page)
    except Exception as exc:
        return f"Error while rendering ({type(exc).__name__})"
    if _is_blank(html):
        return "Shows no text or images with demo content"
    from . import demo
    issue = demo.problem(block, value)
    if issue:
        return f"Its demo content doesn't pass the block's validation ({issue})"
    return None


# ----------------------------------------------------------------- page options (sidebar "Page" tab)
PAGE_OPTIONS_HOOK = "prblm_builder_page_options"


def _page_options(request, page=None, model=None):
    """Options shown in the builder sidebar's "Page" tab, from ``prblm_builder_page_options``
    hooks: ``[{name, label, help, value, chrome, manage_url, choices: [{value, label, set}]}]``.
    ``set`` maps edit-form field names to the values that choice writes into them."""
    from wagtail import hooks
    out = []
    for fn in hooks.get_hooks(PAGE_OPTIONS_HOOK):
        try:
            out.extend(fn(request, page, model) or [])
        except Exception:
            continue
    # Header / footer that nothing lets the editor choose (the site's own page types):
    # explain where they come from instead of leaving editors looking for an option.
    # A page type that decides its own header/footer in code, or the site's template,
    # replaces any generic note, so the tab never points at a file the canvas doesn't use.
    for kind in ("header", "footer"):
        src = chrome.source(kind, request, page, model)
        current = next((o for o in out if o.get("name") == kind), None)
        if current is not None and (current.get("choices") or src[0] == "default"):
            continue                                   # a real choice (Builder page) / plugin default
        info = _chrome_info(kind, page, request, model, src)
        if current is None:
            out.append(info)
        else:
            out[out.index(current)] = info
    for opt in out:
        for choice in opt.get("choices", []):
            choice["set_json"] = json.dumps(choice.get("set", {}))
    return out


def _chrome_info(kind, page=None, request=None, model=None, src=None):
    """An information-only "Page" tab entry: where this page's header/footer really come
    from (see ``chrome.source``), in words an editor can act on."""
    noun = kind
    src = src or chrome.source(kind, request, page, model)
    dev = ""
    if src[0] == "page" and src[1]:
        text = (f"This page type has its own {noun}: it's built into the page, not shared "
                f"with the rest of the site. Change it in this page's content (or ask your "
                f"developer) — editing the site's {noun} won't change it.")
    elif src[0] == "page":
        text = (f"This page type has no separate {noun}. If it needs one, build it from "
                f"sections on the page.")
    elif src[0] == "template":
        from .sites import site_for
        site = site_for(page, request)
        where = f"every page of \u201c{site.site_name or site.hostname}\u201d" if site else "every page"
        text = (f"Your site's shared {noun}, the same on {where} that shows it. Changing it "
                f"changes all those pages, so it isn't edited here.")
        dev = f"For developers: the template {src[1]}."
    else:
        text = f"No {noun} is shown on the canvas for this page type."
        dev = (f"For developers: set PRBLM_BUILDER_{kind.upper()}_TEMPLATE (or a site's "
               f"\u201c{kind}_template\u201d) to show your site's {noun} here.")
    hint = f"{noun.capitalize()}s can be chosen per page on Builder pages."
    return {"name": kind, "label": noun.capitalize(), "info": text,
            "hint": f"{dev} {hint}".strip()}


# ----------------------------------------------------------------- site header / footer
def _has_chrome(kind, request, page=None, model=None):
    """Whether the header/footer shows anything (an empty template or hook result, e.g.
    ``""`` or an empty StreamField, takes no space on the canvas)."""
    return not _is_blank(chrome.html(kind, request, page, model))


# ----------------------------------------------------------------- per-page builder
@xframe_options_sameorigin  # so it can be framed by the editor's Layout tab (same origin)
def builder(request, page_id):
    """The Layout tab's canvas (embedded in the page editor with ``?embed=1``). Opened on
    its own, the address sends you to the page editor — pages are only saved through
    Wagtail's Save draft / Publish."""
    page = _editing_page(page_id)
    if not _can_edit(page, request.user):
        raise PermissionDenied
    if not request.GET.get("embed"):
        return redirect("wagtailadmin_pages:edit", page.pk)
    field_name, stream_block = registry.stream_block_for(type(page))
    if not stream_block:
        raise Http404("This page type has no builder-enabled StreamField.")
    from .sites import config as site_config, site_for
    site = site_for(page, request)
    palette = _palette(stream_block, _usage_site(site))
    return render(request, "prblm_builder/builder.html", {
        "mode": "page",
        "embed": True,
        "page": page,
        "field_name": field_name,
        "sections": _sections(page, field_name),
        "palette": palette,
        "settings_schema": _settings_schema(stream_block, request),
        "page_options": (page_options := _page_options(request, page=page)),
        "page_options_editable": any(o.get("choices") for o in page_options),
        "chrome_base": reverse("prblm_builder:preview") + f"?page={page.id}",
        "show_kinds": len(palette) > 1,
        "preview_url": reverse("prblm_builder:preview"),
        "check_url": reverse("prblm_builder:check_setting"),
        "context_param": f"page={page.id}",
        "header_src": (reverse("prblm_builder:preview") + f"?page={page.id}&chrome=header")
        if _has_chrome("header", request, page) else "",
        "footer_src": (reverse("prblm_builder:preview") + f"?page={page.id}&chrome=footer")
        if _has_chrome("footer", request, page) else "",
        "canvas_width": cfg.canvas_width(),
        "canvas_height": cfg.canvas_height(),
        "canvas_overlap": bool(site_config(site=site)["canvas_overlap"]),
    })


@xframe_options_sameorigin
def builder_new(request):
    """Builder for a brand-new, unsaved page — scoped to a model (no page id yet).

    The canvas starts empty and the palette shows that model's blocks; what you add
    is written to the edit form's hidden layout fields and seeded on the first save.
    """
    label = request.GET.get("model") or ""
    parent = request.GET.get("parent") or ""
    scope = f"model={label}" + (f"&parent={int(parent)}" if parent.isdigit() else "")
    try:
        app_label, model_name = label.split(".")
        model = django_apps.get_model(app_label, model_name)
    except (ValueError, LookupError):
        raise Http404("Unknown page model.")
    if model is None:
        raise Http404("Unknown page model.")
    field_name, stream_block = registry.stream_block_for(model)
    if not stream_block:
        raise Http404("This page type has no builder-enabled StreamField.")
    from .sites import config as site_config, site_for
    site = site_for(None, request)
    palette = _palette(stream_block, _usage_site(site))
    return render(request, "prblm_builder/builder.html", {
        "mode": "new",
        "embed": True,
        "page": None,
        "field_name": field_name,
        "sections": [],
        "palette": palette,
        "settings_schema": _settings_schema(stream_block, request),
        "page_options": (page_options := _page_options(request, model=model)),
        "page_options_editable": any(o.get("choices") for o in page_options),
        "chrome_base": reverse("prblm_builder:preview") + f"?{scope}",
        "show_kinds": len(palette) > 1,
        "preview_url": reverse("prblm_builder:preview"),
        "check_url": reverse("prblm_builder:check_setting"),
        "context_param": scope,
        "header_src": (reverse("prblm_builder:preview") + f"?{scope}&chrome=header")
        if _has_chrome("header", request, model=model) else "",
        "footer_src": (reverse("prblm_builder:preview") + f"?{scope}&chrome=footer")
        if _has_chrome("footer", request, model=model) else "",
        "canvas_width": cfg.canvas_width(),
        "canvas_height": cfg.canvas_height(),
        "canvas_overlap": bool(site_config(site=site)["canvas_overlap"]),
    })


def demo(request):
    """The block library — every previewable block in the project, grouped, each with
    a live demo preview (same content engine as the builder). Admin-only via the URL."""
    if not cfg.demo_enabled():
        raise Http404("The block library is disabled (PRBLM_BUILDER_DEMO).")
    from django.utils.text import slugify

    from . import demo as demo_mod
    from . import sites
    groups, unpreviewable, kinds = [], [], []
    sections = registry.library_sections()
    origins = registry.library_origins() if cfg.library_scope() == "all" else {}
    # Several sites with their own preview settings: a switcher picks whose CSS is used.
    # Several sites: the switcher picks whose CSS previews use AND whose pages count in
    # "Used on N pages" ("all" = every site, default preview styles).
    site_choices = sites.choices()
    site_host, usage_site = "", None
    if site_choices:
        wanted = request.GET.get("site")
        known = [h for h, _l in site_choices]
        current = sites.site_for(request=request)
        site_host = wanted if wanted in known else (current.hostname if current and current.hostname in known else known[0])
        if site_host != sites.ALL:
            from wagtail.models import Site
            usage_site = Site.objects.filter(hostname=site_host).first()
    for kind, kind_groups in sections:
        kind_groups = registry.order_by_usage(
            kind_groups, lambda n, b: len(demo_mod.usage(n, b, usage_site)))
        kkey = registry.KIND_KEYS[kind]
        kind_entry = {"kind": kind, "key": kkey, "short": registry.KIND_SHORT[kind], "groups": []}
        for g, items in kind_groups:
            ok = []
            builtin = kind == registry.KIND_BUILTIN
            for name, block, label in items:
                problem = _preview_problem(name, block, request)
                if problem:
                    unpreviewable.append({"name": name, "label": label, "reason": problem})
                else:
                    pages = demo_mod.usage(name, block, usage_site)
                    ok.append({"name": name, "label": label, "builtin": builtin,
                               "description": registry.block_description(block),
                               "origin": origins.get((name, builtin), ""),
                               "used": len(pages),
                               "pages": [{"title": p.title,
                                          "url": reverse("wagtailadmin_pages:edit", args=[p.pk])}
                                         for p in pages[:12]]})
            if ok:
                entry = {"kind": kind, "group": g, "key": f"{kkey}:{slugify(g)}", "blocks": ok}
                groups.append(entry)
                kind_entry["groups"].append(entry)
        if kind_entry["groups"]:
            kinds.append(kind_entry)
    return render(request, "prblm_builder/demo.html", {
        "groups": groups,
        "kinds": kinds,
        # Kind headings ("Built-in blocks" / "Your site's blocks") only when both exist.
        "show_kinds": len(sections) > 1,
        "total": sum(len(g["blocks"]) for g in groups),
        "unpreviewable": unpreviewable,
        "preview_url": reverse("prblm_builder:preview"),
        "site_choices": sites.library_choices() if site_choices else [],
        # Tabs for a few sites (+ "All sites"); a dropdown beyond that.
        "site_tabs": len(site_choices) - 1 <= sites.SITE_TABS_MAX,
        "admin_home": reverse("wagtailadmin_home"),
        "site": site_host,
        "site_param": f"&site={site_host}" if site_host and site_host != sites.ALL else "",
        "site_label": dict(site_choices).get(site_host, "") if site_choices else "",
        "site_scoped": usage_site is not None,
        "canvas_height": cfg.canvas_height(),
    })


# ----------------------------------------------------------------- block preview (iframe body)
@xframe_options_sameorigin  # admin responses default to X-Frame-Options: DENY; the
def preview(request):       # builder frames this from the same origin, so allow it.
    """Render a single block for a canvas iframe.

    ``?page=<id>&section=<uuid>`` → the real stored block on that page.
    ``?page=<id>&block=<name>``  → a demo-data preview (page used for context).
    ``?model=<app.Model>&block=<name>`` → demo preview with no page (standalone).
    """
    # Lets the site's template tags (analytics, tracking, SEO) skip themselves in previews.
    request.is_prblm_preview = True
    # Site header/footer chrome (shown around the page on the canvas).
    chrome_kind = request.GET.get("chrome")
    if chrome_kind in ("header", "footer"):
        chrome_page = chrome_model = None
        if request.GET.get("model"):
            try:
                chrome_model = django_apps.get_model(*request.GET["model"].split("."))
            except (ValueError, LookupError):
                raise Http404("Unknown page model.")
        if request.GET.get("page"):
            # The page being edited, so headers/footers that use ``page`` render as on
            # the site. (A brand-new unsaved page has none.)
            chrome_page = _editing_page(request.GET["page"])
            if not _can_edit(chrome_page, request.user):
                raise PermissionDenied
        request.is_preview = True
        html = chrome.html(chrome_kind, request, chrome_page, chrome_model)
        # Nothing to show → an empty frame (the canvas hides it), not an error page.
        return HttpResponse(previews.frame("" if _is_blank(html) else html, request,
                                           page=chrome_page))

    page = None
    stream_block = field_name = None
    if request.GET.get("page"):
        page = _editing_page(request.GET["page"])
        if not _can_edit(page, request.user):
            raise PermissionDenied
        field_name, stream_block = registry.stream_block_for(type(page))
    elif request.GET.get("model"):
        try:
            app_label, model_name = request.GET["model"].split(".")
            model = django_apps.get_model(app_label, model_name)
        except (ValueError, LookupError):
            raise Http404("Unknown page model.")
        field_name, stream_block = registry.stream_block_for(model)

    section_id = request.GET.get("section")
    if section_id and page is not None and stream_block is not None:
        for child in getattr(page, field_name):
            if str(child.id) == section_id:
                value = _apply_settings_preview(child.block, child.value, request)
                html = _render_block_safe(child.block, value, request, page)
                return HttpResponse(previews.frame(html, request, page=page))

    block_name = request.GET.get("block")
    # Scoped to a page/model → that field's block; otherwise (demo) resolve anywhere.
    block = stream_block.child_blocks.get(block_name) if stream_block is not None \
        else registry.find_block(block_name, builtin=True if request.GET.get("builtin") == "1" else None)
    if block is None:
        raise Http404(f"Unknown block {block_name!r}")
    # Demo content: prefer a real instance of this block used on the site — real images
    # and copy, and its page as context so hero-style blocks (which read the page's
    # title / header_image / excerpt) render fully instead of an empty band. Long text
    # is trimmed (``&trim=1``) in the Block library and thumbnails; a new section on the
    # canvas shows it in full, as it will be saved.
    value, src_page = _demo_value(block_name, block, trim=request.GET.get("trim") == "1")
    value = _apply_settings_preview(block, value, request)
    html = _render_block_safe(block, value, request, src_page or page)
    return HttpResponse(previews.frame(html, request, page=page))


# ----------------------------------------------------------------- ⚙ check
def check_setting(request):
    """Check one ⚙ setting value as the editor types: ``?page=<id>`` or ``?model=<app.Model>``,
    ``&block=<name>&name=<field>&value=…`` → ``{"ok": true}`` or ``{"ok": false, "error": …}``."""
    stream_block = None
    if request.GET.get("page"):
        page = _editing_page(request.GET["page"])
        if not _can_edit(page, request.user):
            raise PermissionDenied
        _f, stream_block = registry.stream_block_for(type(page))
    elif request.GET.get("model"):
        try:
            model = django_apps.get_model(*request.GET["model"].split("."))
        except (ValueError, LookupError):
            raise Http404("Unknown page model.")
        _f, stream_block = registry.stream_block_for(model)
    block = stream_block.child_blocks.get(request.GET.get("block")) if stream_block else None
    if block is None:
        raise Http404("Unknown block.")
    error = registry.check_setting(block, request.GET.get("name", ""), request.GET.get("value", ""))
    return JsonResponse({"ok": error is None, "error": error or ""})
