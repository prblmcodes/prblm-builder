"""Preview frames, trimming for display, and "Not edited yet" detection.

New demo content is built by ``demo.py``. The realistic-copy generator below
(``synth_value`` / ``synth_demo``) is 0.6's: it's kept only to recognise sections that
0.6 seeded and nobody has edited since.
"""
import json
import random
import re
from datetime import date, timedelta

from django.templatetags.static import static
from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock

from . import settings as cfg

PLACEHOLDER_PREFIX = "Builder placeholder"


def _rng(seed):
    return random.Random(str(seed))


def _pick(pool, seed):
    return pool[_rng(seed).randrange(len(pool))]


# ---------------------------------------------------------------- realistic copy
HEADINGS = [
    "Be more than you thought possible", "Great work starts here",
    "Grow with confidence", "Built around how you really work",
    "Where good ideas take off", "Results you can measure",
    "Let's make it happen together", "Designed for real life",
    "Your next step, made simple", "Do your best work, every day",
]
SUBHEADINGS = [
    "Practical support that meets you where you are.",
    "We help teams do their best work, together.",
    "Simple tools, real results, no fuss.",
    "Everything you need to get started today.",
    "Thoughtful design, built to last.",
    "Clear thinking for complex problems.",
]
BODY = [
    "We work alongside you to turn everyday challenges into lasting progress. From "
    "the first conversation to the final result, you'll have a partner focused on "
    "what matters most to you.",
    "Our approach is simple: understand the problem, shape a clear plan, and deliver "
    "work you can be proud of. No jargon, no surprises — just steady progress you "
    "can see.",
    "Good things happen when the right people have the right support. We bring the "
    "structure, you bring the ambition, and together we make real change stick.",
]
EXCERPTS = [
    "A short summary of what this piece is about, enough to tempt a click.",
    "The key idea in a sentence or two, ready to draw readers in.",
    "A quick taste of the story, with just enough to make you want more.",
]
QUOTES = [
    "This completely changed how our team works together.",
    "Honestly the best decision we made all year.",
    "Clear, practical and genuinely helpful from day one.",
]
COMPANIES = ["Northwind Studio", "Brightpath Collective", "Example Company Ltd", "Harbour & Co"]
NAMES = ["Alex Morgan", "Sam Rivera", "Jordan Lee", "Taylor Brooks", "Casey Quinn"]

RICH_TEXT = (
    "<h2>Great work starts with a clear story</h2>"
    "<p>Use rich text for articles, service write-ups or any free-form content. You "
    "can mix <b>headings</b>, <i>paragraphs</i> and lists to shape a longer read, and "
    "link out to <a href=\"https://example.com\">related pages</a> along the way.</p>"
    "<h3>Why it matters</h3>"
    "<ul><li>It keeps readers moving down the page</li>"
    "<li>It makes the important things easy to find</li>"
    "<li>It gives your words room to breathe</li></ul>"
    "<p>When the structure is right, the message takes care of itself.</p>"
)
RICH_TEXT_SHORT = (
    "<p>A short, friendly line of rich text with <b>bold</b>, <i>italic</i> and "
    "<a href=\"https://example.com\">a link</a> to set the scene.</p>"
)

IDENTIFIER_FIELDS = {"anchor", "anchor_id", "slug", "id", "css_class", "classname", "class_name"}
# Text fields that hold a link (often with a URL validator): demo content gets a valid URL.
URL_FIELDS = {"url", "link", "href", "website", "link_url", "custom_url", "external_url"}
PHONE_FIELDS = {"phone", "tel", "telephone", "phone_number"}


def _text_for(name, label, seed, max_length=None):
    key = (name or "").lower()
    if any(w in key for w in ("subheading", "subtitle", "intro", "description", "tagline")):
        pool = SUBHEADINGS
    elif any(w in key for w in ("heading", "title")):
        pool = HEADINGS
    elif any(w in key for w in ("excerpt", "summary", "blurb")):
        pool = EXCERPTS
    elif "quote" in key:
        pool = QUOTES
    elif "company" in key:
        pool = COMPANIES
    elif any(w in key for w in ("author", "name", "person")):
        pool = NAMES
    elif isinstance(max_length, int) and max_length and max_length <= 90:
        pool = SUBHEADINGS
    else:
        pool = BODY
    text = _pick(pool, seed)
    if max_length and len(text) > max_length:
        text = text[:max_length].rsplit(" ", 1)[0]
    return text


def _button_label(block):
    try:
        default = block.get_default()
    except Exception:
        default = None
    text = str(default).strip() if default not in (None, "") else ""
    return text or "Learn more"


# ---------------------------------------------------------------- images
_IMG_CACHE = {}


_NO_NEW_IMAGES = {"on": False}


def placeholder_image(width=1200, height=800):
    """0.6's soft-gradient placeholder Wagtail Image — kept so sections seeded by 0.6 are
    still recognised as "Not edited yet". New demo content uses ``demo.placeholder_image``
    (labelled, shaped by role). ``None`` when ``PRBLM_BUILDER_PLACEHOLDER_IMAGES`` is off."""
    if not cfg.placeholder_images():
        return None
    if _NO_NEW_IMAGES["on"]:
        from wagtail.images import get_image_model
        return get_image_model().objects.filter(title=f"{PLACEHOLDER_PREFIX} {width}x{height}").first()
    key = (width, height)
    if key in _IMG_CACHE:
        return _IMG_CACHE[key]
    from io import BytesIO

    from django.core.files.images import ImageFile
    from wagtail.images import get_image_model

    Image = get_image_model()
    title = f"{PLACEHOLDER_PREFIX} {width}x{height}"
    existing = Image.objects.filter(title=title).first()
    if existing:
        _IMG_CACHE[key] = existing
        return existing
    try:
        from PIL import Image as PILImage
        from PIL import ImageDraw

        im = PILImage.new("RGB", (width, height), (229, 233, 240))
        draw = ImageDraw.Draw(im)
        for y in range(height):  # soft vertical gradient
            t = y / max(1, height - 1)
            draw.line([(0, y), (width, y)],
                      fill=(int(229 - 30 * t), int(233 - 24 * t), int(240 - 12 * t)))
        buf = BytesIO()
        im.save(buf, "PNG")
        buf.seek(0)
        img = Image(title=title)
        img.file.save(f"builder-placeholder-{width}x{height}.png", ImageFile(buf), save=False)
        img.width, img.height = width, height
        img.file_size = img.file.size
        img.save()
    except Exception:
        _IMG_CACHE[key] = None
        return None
    _IMG_CACHE[key] = img
    return img


def _demo_image(seed=""):
    """A real image from the host site's library (realistic + site-appropriate),
    chosen deterministically; falls back to a generated placeholder. Skips images
    whose file is missing on disk, so a half-synced media dir can't break a preview."""
    from wagtail.images import get_image_model

    Image = get_image_model()
    ids = list(Image.objects.exclude(title__startswith=PLACEHOLDER_PREFIX)
               .order_by("id").values_list("id", flat=True)[:400])
    rng = _rng(seed)
    rng.shuffle(ids)
    for pk in ids[:10]:
        img = Image.objects.filter(id=pk).first()
        try:
            if img and img.file and img.file.storage.exists(img.file.name):
                return img
        except Exception:
            continue
    return placeholder_image()


# ---------------------------------------------------------------- synthesis
def synth_value(block, name="", depth=0, seed=""):
    """A plain-Python demo value for ``block`` (pass through normalize())."""
    if depth > 6:
        return None
    seed = seed or name

    if isinstance(block, blocks.StructBlock):
        children = block.child_blocks
        linkish = "text" in children and any(k in children for k in ("url", "page", "relative", "document"))
        out = {}
        for cname, child in children.items():
            csd = seed + "." + cname
            if linkish and cname == "text":
                out[cname] = _button_label(child)
            elif linkish and cname == "relative":
                out[cname] = "/example-page"            # ONE destination only…
            elif linkish and cname in ("url", "page", "document"):
                out[cname] = None                        # …leave the others empty (a link has one)
            else:
                out[cname] = synth_value(child, cname, depth + 1, csd)
        return out
    if isinstance(block, blocks.ListBlock):
        return [synth_value(block.child_block, name, depth + 1, seed + "." + str(i)) for i in range(3)]
    if isinstance(block, blocks.StreamBlock):
        return [(cn, synth_value(c, cn, depth + 1, seed + "." + cn))
                for cn, c in list(block.child_blocks.items())[:2]]
    if isinstance(block, ImageChooserBlock):
        return _demo_image(seed)
    if isinstance(block, blocks.PageChooserBlock):
        from wagtail.models import Page
        return Page.objects.live().public().filter(depth__gt=2).first()
    if isinstance(block, DocumentChooserBlock):
        from wagtail.documents import get_document_model
        return get_document_model().objects.first()
    if isinstance(block, blocks.ChooserBlock):
        # Snippets and other model choosers: the first one there is (like pages above).
        try:
            return block.model_class.objects.first()
        except Exception:
            return None
    if isinstance(block, blocks.ChoiceBlock):
        choices = [c[0] for c in (block.field.choices or []) if c[0]]
        return choices[0] if choices else None
    if isinstance(block, blocks.RichTextBlock):
        key = (name or "").lower()
        if "rich_text" in key or key in ("body", "content"):
            return RICH_TEXT
        if any(w in key for w in ("heading", "title", "subtitle")):
            return "<p>" + _text_for(name, None, seed) + "</p>"
        return RICH_TEXT_SHORT
    if isinstance(block, blocks.BooleanBlock):
        return block.get_default()
    if isinstance(block, blocks.IntegerBlock):
        d = block.get_default()
        return d if d not in (None, "") else 3
    if isinstance(block, blocks.URLBlock):
        return "https://www.youtube.com/watch?v=A8VRZd17stk" \
            if any(w in (name or "").lower() for w in ("video", "youtube", "embed")) else "https://example.com"
    if isinstance(block, blocks.EmailBlock):
        return "hello@example.com"
    if isinstance(block, blocks.DateTimeBlock):
        from django.utils import timezone
        return timezone.now() + timedelta(days=12, hours=5)
    if isinstance(block, blocks.DateBlock):
        return date.today() + timedelta(days=12)
    if isinstance(block, (blocks.CharBlock, blocks.TextBlock)):
        key = (name or "").lower()
        if key in IDENTIFIER_FIELDS:
            return ""
        if key in URL_FIELDS or key.endswith("_url"):
            return "https://example.com"
        if key in PHONE_FIELDS:
            return "+1 555 0100"
        if "button" in key or "label" in key:
            return _button_label(block)
        max_length = getattr(getattr(block, "field", None), "max_length", None)
        return _text_for(name, getattr(block.meta, "label", None), seed, max_length)
    try:
        return block.get_default()
    except Exception:
        return None


def _first_error(err):
    """A child's error as one ``ValidationError`` (Wagtail may hand over an ErrorList)."""
    if isinstance(err, (list, tuple)):
        data = err.as_data() if hasattr(err, "as_data") else list(err)
        return data[0] if data else None
    return err


def _repair(block, value, error, hard=False):
    """``value`` with the parts that failed validation reset to their empty default. Struct
    and list errors are followed down to the failing field, so the rest of the demo content
    stays. ``hard`` also resets a failing struct's dropdowns: in blocks like a "link to:
    page / URL / email" chooser, the dropdown decides which field is required."""
    errs = getattr(_first_error(error), "block_errors", None)
    try:
        if isinstance(block, blocks.StructBlock) and isinstance(errs, dict) and errs:
            out = dict(value)
            for cname, cerr in errs.items():
                child = block.child_blocks.get(cname)
                if child is not None:
                    out[cname] = _repair(child, out.get(cname), cerr, hard)
            if hard:
                for cname, child in block.child_blocks.items():
                    if isinstance(child, blocks.ChoiceBlock):
                        out[cname] = child.normalize(child.get_default())
            return block.normalize(out)
        if isinstance(block, blocks.ListBlock) and isinstance(errs, dict) and errs:
            items = list(value)
            for i, cerr in errs.items():
                if isinstance(i, int) and 0 <= i < len(items):
                    items[i] = _repair(block.child_block, items[i], cerr, hard)
            return block.normalize(items)
    except Exception:
        pass
    return block.normalize(block.get_default())


def synth_demo(block, name=""):
    """Synthesised demo content that passes the block's own validation, so a new section
    can always be saved — also for third-party blocks with rules we can't know (e.g. a URL
    validator on a field their own script hides). Failing parts are reset to empty."""
    value = block.normalize(synth_value(block, name, seed=name))
    from django.core.exceptions import ValidationError
    for attempt in range(4):
        try:
            block.clean(value)
            return value
        except ValidationError as exc:
            value = _repair(block, value, exc, hard=attempt >= 1)
        except Exception:
            return value
    return value


# ---------------------------------------------------------------- real-instance index
# Demo content prefers a *real* instance of a block used somewhere on the site: real
# images + copy, and (crucially) the page it lives on, so hero-style blocks that read
# page fields (title / header_image / excerpt) render fully in a preview. Site-agnostic
# — it just walks every page model's StreamFields. Cached briefly so a page of previews
# doesn't rescan per block.
def real_instance_for(name, block):
    """``(value, page)``: the best real instance of ``block`` on a live page (see
    ``demo.real_instance``), or ``(None, None)``."""
    from . import demo
    return demo.real_instance(name, block)


def real_value_for(name, block):
    return real_instance_for(name, block)[0]


DEMO_RICHTEXT_WORDS = 80   # rich text shown in previews, trimmed to this many words
DEMO_TEXT_CHARS = 360      # plain long-text fields, trimmed to this many characters


def _trim_text(s, is_html):
    from django.utils.text import Truncator
    s = s or ""
    if is_html:
        return Truncator(s).words(DEMO_RICHTEXT_WORDS, html=True, truncate=" …")
    if len(s) > DEMO_TEXT_CHARS:
        return Truncator(s).chars(DEMO_TEXT_CHARS, truncate="…")
    return s


def _trim_walk(block, value):
    if isinstance(block, blocks.StructBlock):
        out = {}
        for cname, child in block.child_blocks.items():
            try:
                cv = value[cname]
            except Exception:
                cv = None
            out[cname] = _trim_walk(child, cv)
        return out
    if isinstance(block, blocks.ListBlock):
        return [_trim_walk(block.child_block, v) for v in (value or [])]
    if isinstance(block, blocks.StreamBlock):
        out = []
        for bound in (value or []):
            try:
                out.append((bound.block_type, _trim_walk(bound.block, bound.value)))
            except Exception:
                continue
        return out
    if isinstance(block, blocks.RichTextBlock):
        src = getattr(value, "source", None)
        return _trim_text(src if src is not None else str(value or ""), True)
    if isinstance(block, (blocks.CharBlock, blocks.TextBlock)):
        return _trim_text(str(value or ""), False)
    return value


def trim_for_demo(block, value):
    """A copy of a demo value with long rich-text / text fields shortened (with an
    ellipsis) so the Block library and canvas stay elegant. Display only — it never
    touches stored content, and non-text values (images, pages) pass through."""
    try:
        return block.normalize(_trim_walk(block, value))
    except Exception:
        return value


def _strip_ids(data):
    """Drop the ``id`` Wagtail gives each list/stream item: it's freshly generated every
    time content is prepared for saving, so it must not count when comparing content."""
    if isinstance(data, list):
        return [_strip_ids(d) for d in data]
    if isinstance(data, dict):
        if "type" in data and "value" in data:
            return {k: _strip_ids(v) for k, v in data.items() if k != "id"}
        return {k: _strip_ids(v) for k, v in data.items()}
    return data


_BLOCK_KEY = re.compile(r'\s+data-block-key="[^"]*"')


def _canon(data):
    """Content as compared by "Not edited yet": list/stream item ids dropped, empty text
    as ``""`` whether stored as ``None`` or ``""``, and rich text without the
    ``data-block-key`` attributes Wagtail's editor adds on save. (Saving a page through
    the editor changes these without anyone editing anything.)"""
    data = _strip_ids(data)
    if isinstance(data, list):
        return [_canon(d) for d in data]
    if isinstance(data, dict):
        return {k: _canon(v) for k, v in data.items()}
    if data is None:
        return ""
    if isinstance(data, str):
        return _BLOCK_KEY.sub("", data)
    return data


def _prep(block, value):
    try:
        return _canon(block.get_prep_value(value))
    except Exception:
        return None


def _content(block, data):
    """Canonical content for comparing: ⚙ settings left out (changing background or anchor
    doesn't "edit" a section)."""
    from .mixins import builder_setting_names
    skip = set(builder_setting_names(block))
    data = _canon(data)
    if skip and isinstance(data, dict):
        return {k: v for k, v in data.items() if k not in skip}
    return data


_LEGACY = {}


def legacy_unedited(block, name, stored_prep, extra=()):
    """For sections seeded before 0.7 (no seeded-section record): does the content still
    equal what the plugin could have seeded — the block's default, its preview value, or
    0.6's generated content? ``extra`` adds more candidates (prep values)."""
    if stored_prep is None:
        return False
    from .registry import block_key
    key = block_key(name, block)
    if key not in _LEGACY:
        cands = [_prep(block, block.get_default())]
        preview = explicit_preview_value(block)
        if preview is not None:
            cands.append(_prep(block, preview))
        try:
            _NO_NEW_IMAGES["on"] = True
            cands.append(_prep(block, synth_demo(block, name)))
        except Exception:
            pass
        finally:
            _NO_NEW_IMAGES["on"] = False
        _LEGACY[key] = [_content(block, c) for c in cands if c is not None]
    stored = _content(block, stored_prep)
    others = [_content(block, c) for c in extra if c is not None]
    return any(c == stored for c in _LEGACY[key] + others)


def is_unedited(block, name, stored_prep, page_id=None, section_id=None):
    """True if a stored section still holds the demo content it was seeded with — i.e. an
    editor hasn't changed it yet. Sections seeded by 0.7+ are recorded (``SeededSection``):
    their content is compared with the recorded hash. Older ones are compared with what
    the plugin could have seeded (``legacy_unedited``), plus the real content it may have
    copied (unless this section *is* that real content)."""
    if stored_prep is None:
        return False
    from . import demo
    recorded = demo.seeded_hash(section_id)
    if recorded is not None:
        return demo.content_hash(block, stored_prep) == recorded
    extra = []
    value, src_page = real_instance_for(name, block)
    if value is not None and str(getattr(src_page, "pk", "")) != str(page_id):
        extra.append(_prep(block, value))
    return legacy_unedited(block, name, stored_prep, extra)


def explicit_preview_value(block):
    """The block's own Wagtail ``preview_value`` (Wagtail 6.4+ block previews), or ``None``
    when the developer didn't set one. (Wagtail itself falls back to ``default``; we only
    want the value someone chose on purpose.)"""
    if not hasattr(block.meta, "preview_value"):
        return None
    try:
        return block.get_preview_value()
    except Exception:
        return None


def demo_value(block, name="", prefer_real=True):
    """Demo content for a new section of ``block`` — see ``demo.build`` (field by field:
    preview_value → real content of the same block → defaults → neutral generated content).
    ``prefer_real=False`` skips real content."""
    from . import demo
    return demo.build(block, name, real=prefer_real)[0]


# ---------------------------------------------------------------- iframe frame
def _url(path):
    return path if path.startswith(("http://", "https://", "//", "/")) else static(path)


def asset_urls(items):
    """URLs for ``PRBLM_BUILDER_PREVIEW_CSS`` / ``_JS`` entries: full URLs as given, static
    paths as root-relative ``/static/…``. Never absolute with the request's host: Wagtail's
    preview renders with a fake request using the Site's hostname / port, which isn't
    necessarily the address the editor is browsing (the files would fail to load)."""
    out = []
    for it in items:
        if isinstance(it, dict):
            src = it.get("href") or it.get("src")
            if src:
                out.append(_url(src))
        elif it:
            out.append(_url(str(it)))
    return out


_BOOL_ATTRS = {"defer", "async", "nomodule"}
_SCRIPT_ATTRS = ("type", "integrity", "crossorigin", "referrerpolicy", "nonce", "id")
_LINK_ATTRS = ("media", "integrity", "crossorigin", "referrerpolicy", "id", "as", "type")


def _attrs(entry, names):
    from django.utils.html import format_html_join
    pairs = [(k, entry[k]) for k in names if entry.get(k) not in (None, "", False)]
    html = format_html_join("", ' {}="{}"', pairs)
    flags = "".join(f" {k}" for k in sorted(_BOOL_ATTRS) if entry.get(k) is True)
    return str(html) + flags


def css_tags(items):
    """``<link>`` / ``<style>`` tags for ``PRBLM_BUILDER_PREVIEW_CSS`` entries. An entry is a
    static path or URL, or a dict: ``{"href": …, "media": "print", "integrity": …,
    "crossorigin": "anonymous"}``, ``{"href": …, "rel": "preload", "as": "font"}`` or
    ``{"inline": "body{…}"}``."""
    from django.utils.html import escape
    out = []
    for it in items:
        if isinstance(it, dict):
            if it.get("inline"):
                out.append(f"<style>{it['inline']}</style>")
                continue
            href = it.get("href") or it.get("src")
            if not href:
                continue
            rel = escape(it.get("rel") or "stylesheet")
            out.append(f'<link rel="{rel}" href="{escape(_url(href))}"{_attrs(it, _LINK_ATTRS)}>')
        elif it:
            out.append(f'<link rel="stylesheet" href="{escape(_url(str(it)))}">')
    return "".join(out)


def js_tags(items):
    """``<script>`` tags for ``PRBLM_BUILDER_PREVIEW_JS`` entries, in list order (= load
    order). An entry is a static path or URL, or a dict: ``{"src": …, "defer": True,
    "type": "module", "integrity": …, "crossorigin": "anonymous"}``, ``{"inline": "…"}``
    (runs in place — e.g. config a library needs first) or ``{"importmap": {…}}``."""
    from django.utils.html import escape
    out = []
    for it in items:
        if isinstance(it, dict):
            if it.get("importmap"):
                out.append('<script type="importmap">' + json.dumps(it["importmap"]) + "</script>")
            elif it.get("inline"):
                kind = f' type="{escape(it["type"])}"' if it.get("type") else ""
                out.append(f"<script{kind}>{it['inline']}</script>")
            elif it.get("src"):
                out.append(f'<script src="{escape(_url(it["src"]))}"{_attrs(it, _SCRIPT_ATTRS)}></script>')
        elif it:
            out.append(f'<script src="{escape(_url(str(it)))}"></script>')
    return "".join(out)


def _strip_lazy(html):
    # Previews are scaled/offscreen, so lazy images never enter the frame's viewport and
    # would load partially — then the measured height is wrong (the section shows as a
    # thin stripe). Strip loading="lazy" so every image loads eagerly: the iframe's load
    # event waits for them, so the height is correct in a single measure.
    return re.sub(r'\sloading=(["\'])lazy\1', " ", str(html))


# Marks where the section starts and ends inside a site's own preview template, so the
# canvas measures just the section (not the template's wrappers or padding).
SECTION_START = "<template data-prblm-start></template>"
SECTION_END = "<template data-prblm-end></template>"


CANVAS_CLASS = "prblm-canvas"
# PRBLM_BUILDER_REDUCE_MOTION: animations / transitions finish at once in previews.
MOTION_CSS = (".prblm-canvas *,.prblm-canvas *::before,.prblm-canvas *::after{"
              "animation-duration:0s!important;animation-delay:0s!important;"
              "animation-iteration-count:1!important;transition-duration:0s!important;"
              "transition-delay:0s!important}.prblm-canvas{scroll-behavior:auto!important}")


def attrs_html(attrs):
    """`` name="value"`` pairs for a tag, escaped (``True`` → a bare attribute)."""
    from django.utils.html import escape
    out = []
    for name, value in (attrs or {}).items():
        name = str(name).strip()
        if not name or not re.fullmatch(r"[A-Za-z_:@][\w:.@-]*", name) or value in (None, False):
            continue
        out.append(f" {escape(name)}" if value is True else f' {escape(name)}="{escape(value)}"')
    return "".join(out)


# Previews are pictures: a click on a link (or a form submit) must not load another page
# inside the frame. Only the default action is stopped, so script buttons (Alpine @click,
# accordions, tabs) keep working and hovering still shows the address.
INERT_LINKS_JS = ('<script>(function(){function stop(e){var a=e.target&&e.target.closest&&'
                  'e.target.closest("a[href],area[href]");if(a)e.preventDefault();}'
                  'document.addEventListener("click",stop,true);'
                  'document.addEventListener("auxclick",stop,true);'
                  'document.addEventListener("submit",function(e){e.preventDefault();},true);'
                  '})();</script>')


def _canvas_head():
    """What every preview gets: inert links, and instant animations (the ``prblm-canvas``
    marker itself is added by the caller)."""
    style = f"<style>{MOTION_CSS}</style>" if cfg.reduce_motion() else ""
    return INERT_LINKS_JS + style


def frame(block_html, request, page=None, site=None):
    """A whole HTML page showing one section (or header/footer) for a preview iframe.

    With ``PRBLM_BUILDER_PREVIEW_TEMPLATE`` (or a site's ``template``) the section is
    rendered inside the site's own template, so it gets the site's real <head>, <body>
    attributes, inline scripts and wrappers. Otherwise a plain page with the configured
    CSS / JS and body class."""
    from django.template.loader import render_to_string
    from django.utils.safestring import mark_safe

    from .sites import config
    conf = config(page, request, site)
    section = _strip_lazy(block_html)
    if conf["template"]:
        # The site's template owns <html>/<body>: mark the document from inside the section
        # (runs before the section and before the site's DOMContentLoaded scripts).
        marker = (f'<script>document.documentElement.classList.add("{CANVAS_CLASS}")</script>'
                  + _canvas_head())
        ctx = {"page": page, "self": page, "request": request, "prblm_preview": True,
               "prblm_canvas_class": CANVAS_CLASS,
               "prblm_section": mark_safe(marker + SECTION_START + section + SECTION_END)}
        return _strip_lazy(render_to_string(conf["template"], ctx, request=request))
    from django.utils.html import escape
    html_attrs = dict(conf["html_attrs"])
    html_class = " ".join(x for x in (CANVAS_CLASS, str(html_attrs.pop("class", "") or "")) if x)
    parts = [
        f'<!doctype html><html class="{escape(html_class)}"{attrs_html(html_attrs)}><head>'
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        css_tags(conf["css"]),
        _canvas_head(),
        # No body padding: on the builder canvas sections stack flush, like a real page.
        # Height auto: the frame keeps a tall viewport (for vh sizes), and a site rule like
        # `html, body {height: 100%}` would otherwise make every section that tall.
        "<style>html,body{margin:0;background:#fff;height:auto!important;"
        "min-height:0!important}</style>",
        f'</head><body class="{escape(conf["body_class"])}"{attrs_html(conf["body_attrs"])}>',
        section,
        js_tags(conf["js"]),
        "</body></html>",
    ]
    return "".join(parts)
