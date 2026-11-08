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
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.html import strip_tags
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST
from wagtail.models import Page

from . import layout as layout_mod
from . import previews, registry
from . import settings as cfg


# ----------------------------------------------------------------- helpers
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
        })
    return out


def _palette(stream_block):
    """``[(group, [{type, label}, …]), …]`` for the builder sidebar."""
    groups = registry.grouped_blocks(stream_block)
    return [(g, [{"type": n, "label": lbl} for (n, _b, lbl) in items]) for g, items in groups]


def _render_block(block, value, request, page=None):
    # Mark the request as a preview so blocks that fill themselves with sample data
    # under preview (the common Wagtail convention) show demo content on the canvas.
    request.is_preview = True
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


def _demo_value(block_name, block):
    """``(value, page)`` to preview a block with: a real instance used on the site
    (with its page, so hero-style blocks render fully), else synthesised content —
    trimmed for display."""
    if registry.is_builtin(block):
        # Built-ins always show their own explanatory example content.
        return block.get_default(), None
    value, src_page = previews.real_instance_for(block_name)
    if value is None:
        value = previews.demo_value(block, block_name, prefer_real=False)
    return previews.trim_for_demo(block, value), src_page


def _preview_problem(block_name, block, request):
    """Why a block can't be previewed on its own (``None`` if it can): it errors, or
    renders nothing with demo content (e.g. a link/button fragment)."""
    try:
        value, src_page = _demo_value(block_name, block)
        html = _render_block(block, value, request, src_page)
    except Exception as exc:
        return f"Error while rendering ({type(exc).__name__})"
    if _is_blank(html):
        return "Shows no text or images with demo content"
    return None


# ----------------------------------------------------------------- per-page builder
@xframe_options_sameorigin  # so it can be framed by the editor's Layout tab (same origin)
def builder(request, page_id):
    page = _specific_page(page_id)
    if not _can_edit(page, request.user):
        raise PermissionDenied
    field_name, stream_block = registry.stream_block_for(type(page))
    if not stream_block:
        raise Http404("This page type has no builder-enabled StreamField.")
    return render(request, "prblm_builder/builder.html", {
        "mode": "page",
        "embed": bool(request.GET.get("embed")),
        "page": page,
        "field_name": field_name,
        "sections": _sections(page, field_name),
        "palette": _palette(stream_block),
        "preview_url": reverse("prblm_builder:preview"),
        "save_url": reverse("prblm_builder:save", args=[page.id]),
        "context_param": f"page={page.id}",
        "header_src": (reverse("prblm_builder:preview") + f"?page={page.id}&chrome=header")
        if cfg.header_template() else "",
        "footer_src": (reverse("prblm_builder:preview") + f"?page={page.id}&chrome=footer")
        if cfg.footer_template() else "",
        "edit_url": reverse("wagtailadmin_pages:edit", args=[page.id]),
        "preview_page_url": reverse("prblm_builder:page_preview", args=[page.id]),
        "back_url": reverse("wagtailadmin_explore", args=[page.get_parent().id]),
        "canvas_width": cfg.canvas_width(),
    })


@xframe_options_sameorigin
def builder_new(request):
    """Builder for a brand-new, unsaved page — scoped to a model (no page id yet).

    The canvas starts empty and the palette shows that model's blocks; what you add
    is written to the edit form's hidden layout fields and seeded on the first save.
    """
    label = request.GET.get("model") or ""
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
    return render(request, "prblm_builder/builder.html", {
        "mode": "new",
        "embed": True,
        "page": None,
        "field_name": field_name,
        "sections": [],
        "palette": _palette(stream_block),
        "preview_url": reverse("prblm_builder:preview"),
        "save_url": "",
        "context_param": f"model={label}",
        "header_src": (reverse("prblm_builder:preview") + f"?model={label}&chrome=header")
        if cfg.header_template() else "",
        "footer_src": (reverse("prblm_builder:preview") + f"?model={label}&chrome=footer")
        if cfg.footer_template() else "",
        "edit_url": "",
        "preview_page_url": "",
        "back_url": "",
        "canvas_width": cfg.canvas_width(),
    })


def demo(request):
    """The block library — every previewable block in the project, grouped, each with
    a live demo preview (same content engine as the builder). Admin-only via the URL."""
    if not cfg.demo_enabled():
        raise Http404("The block library is disabled (PRBLM_BUILDER_DEMO).")
    groups, unpreviewable = [], []
    sections = registry.library_sections()
    for kind, kind_groups in sections:
        for g, items in kind_groups:
            ok = []
            builtin = kind == registry.KIND_BUILTIN
            for name, block, label in items:
                problem = _preview_problem(name, block, request)
                if problem:
                    unpreviewable.append({"name": name, "label": label, "reason": problem})
                else:
                    ok.append({"name": name, "label": label, "builtin": builtin})
            if ok:
                groups.append({"kind": kind, "group": g, "blocks": ok})
    return render(request, "prblm_builder/demo.html", {
        "groups": groups,
        # Kind headings ("Built-in blocks" / "Your site's blocks") only when both exist.
        "show_kinds": len(sections) > 1,
        "total": sum(len(g["blocks"]) for g in groups),
        "unpreviewable": unpreviewable,
        "preview_url": reverse("prblm_builder:preview"),
    })


@xframe_options_sameorigin
def page_preview(request, page_id):
    """Render the whole page from its latest (draft) revision — the real page, as a
    single document, for the 'open in new tab' preview."""
    page = _specific_page(page_id)
    if not _can_edit(page, request.user):
        raise PermissionDenied
    page = page.get_latest_revision_as_object()
    request.is_preview = True
    request.preview_mode = ""
    return page.serve_preview(request, page.default_preview_mode)


# ----------------------------------------------------------------- block preview (iframe body)
@xframe_options_sameorigin  # admin responses default to X-Frame-Options: DENY; the
def preview(request):       # builder frames this from the same origin, so allow it.
    """Render a single block for a canvas iframe.

    ``?page=<id>&section=<uuid>`` → the real stored block on that page.
    ``?page=<id>&block=<name>``  → a demo-data preview (page used for context).
    ``?model=<app.Model>&block=<name>`` → demo preview with no page (standalone).
    """
    # Site header/footer chrome (shown around the page on the canvas).
    chrome = request.GET.get("chrome")
    if chrome in ("header", "footer"):
        from django.template.loader import render_to_string
        tmpl = cfg.header_template() if chrome == "header" else cfg.footer_template()
        if not tmpl:
            raise Http404
        ctx = {}
        if request.GET.get("page"):
            # The page being edited, so headers/footers that use ``page`` render as on
            # the site. (A brand-new unsaved page has none.)
            chrome_page = _specific_page(request.GET["page"])
            if not _can_edit(chrome_page, request.user):
                raise PermissionDenied
            ctx = {"page": chrome_page, "self": chrome_page}
        request.is_preview = True
        html = render_to_string(tmpl, ctx, request=request)  # request → context processors
        return HttpResponse(previews.frame(html, request))

    page = None
    stream_block = field_name = None
    if request.GET.get("page"):
        page = _specific_page(request.GET["page"])
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
                html = _render_block_safe(child.block, child.value, request, page)
                return HttpResponse(previews.frame(html, request))

    block_name = request.GET.get("block")
    # Scoped to a page/model → that field's block; otherwise (demo) resolve anywhere.
    block = stream_block.child_blocks.get(block_name) if stream_block is not None \
        else registry.find_block(block_name, builtin=True if request.GET.get("builtin") == "1" else None)
    if block is None:
        raise Http404(f"Unknown block {block_name!r}")
    # Demo content: prefer a real instance of this block used on the site — real images
    # and copy, and its page as context so hero-style blocks (which read the page's
    # title / header_image / excerpt) render fully instead of an empty band. Long text
    # is trimmed for an elegant demo (display only).
    value, src_page = _demo_value(block_name, block)
    html = _render_block_safe(block, value, request, src_page or page)
    return HttpResponse(previews.frame(html, request))


# ----------------------------------------------------------------- save
@require_POST
def save(request, page_id):
    page = _specific_page(page_id)
    if not _can_edit(page, request.user):
        raise PermissionDenied
    field_name, stream_block = registry.stream_block_for(type(page))
    if not stream_block:
        raise Http404

    try:
        posted = json.loads(request.body.decode())
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "bad payload"}, status=400)
    sections = posted.get("sections", [])
    publish = bool(posted.get("publish"))

    # Standalone builder: it shows every section and saves the whole set, so the
    # listed sections are authoritative — initial = the current ids, meaning any
    # omitted one was removed by the editor and is dropped.
    current_raw = list(getattr(page, field_name).raw_data)
    initial_ids = [d.get("id") for d in current_raw]
    new_raw = layout_mod.reconcile(stream_block, current_raw, sections, initial_ids)

    setattr(page, field_name, stream_block.to_python(new_raw))
    revision = page.save_revision(user=request.user)
    if publish:
        revision.publish(user=request.user)

    return JsonResponse({
        "ok": True,
        "published": publish,
        "edit_url": reverse("wagtailadmin_pages:edit", args=[page.id]),
    })
