"""Realistic demo content + live preview for any block — site-agnostic.

Values are built from each block's *type* and field name, using a small library of
real-sounding copy and the host site's own images, so a freshly-built section looks
like a real page (and the saved block gives the editor a usable starting point).

Deterministic: the same block always yields the same demo value, so the canvas
preview, the palette thumbnail and the saved content all agree.
"""
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

IDENTIFIER_FIELDS = {"anchor_id", "slug", "id", "css_class", "classname", "class_name"}


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


def placeholder_image(width=1200, height=800):
    """A reusable soft-gradient placeholder Wagtail Image (fallback when the site has
    no images of its own). Returns None when ``PRBLM_BUILDER_PLACEHOLDER_IMAGES`` is
    off — the demo then simply has no image."""
    if not cfg.placeholder_images():
        return None
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
        if "button" in key or "label" in key:
            return _button_label(block)
        max_length = getattr(getattr(block, "field", None), "max_length", None)
        return _text_for(name, getattr(block.meta, "label", None), seed, max_length)
    try:
        return block.get_default()
    except Exception:
        return None


# ---------------------------------------------------------------- real-instance index
# Demo content prefers a *real* instance of a block used somewhere on the site: real
# images + copy, and (crucially) the page it lives on, so hero-style blocks that read
# page fields (title / header_image / excerpt) render fully in a preview. Site-agnostic
# — it just walks every page model's StreamFields. Cached briefly so a page of previews
# doesn't rescan per block.
import time

_INDEX = {"at": 0.0, "data": None}


def _build_instance_index():
    from django.apps import apps
    from wagtail.fields import StreamField
    from wagtail.models import Page

    from .registry import is_builtin

    # (name, is_builtin) -> (score, value, page, block id). Keyed by kind too, so a site
    # block and a built-in block that share a name never lend each other content.
    best = {}
    for model in apps.get_models():
        if not (issubclass(model, Page) and model is not Page):
            continue
        sfs = [f.name for f in model._meta.get_fields() if isinstance(f, StreamField)]
        if not sfs:
            continue
        try:
            # Newest first, capped — bounds the cost on very large sites.
            pages = list(model.objects.order_by("-pk")[: cfg.index_scan_limit()])
        except Exception:
            continue
        for page in pages:
            for fname in sfs:
                try:
                    value = getattr(page, fname)
                except Exception:
                    continue
                for child in value:
                    try:
                        score = len(str(child.block.get_prep_value(child.value)))
                    except Exception:
                        score = 0
                    key = (child.block_type, is_builtin(child.block))
                    cur = best.get(key)
                    if cur is None or score > cur[0]:
                        best[key] = (score, child.value, page, str(child.id))
    return {key: (v, p, bid) for key, (s, v, p, bid) in best.items()}


def instance_index(max_age=60):
    now = time.time()
    if _INDEX["data"] is None or now - _INDEX["at"] > max_age:
        try:
            _INDEX["data"] = _build_instance_index()
        except Exception:
            _INDEX["data"] = {}
        _INDEX["at"] = now
    return _INDEX["data"]


def real_instance_for(name):
    """``(value, page)`` of the most-filled real instance of block ``name``, or
    ``(None, None)``. The page is the context for blocks that read page fields."""
    if not name:
        return None, None
    value, page, _bid = instance_index().get((name, False), (None, None, None))
    return value, page


def real_value_for(name):
    return real_instance_for(name)[0]


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


def _prep(block, value):
    try:
        return _strip_ids(block.get_prep_value(value))
    except Exception:
        return None


def is_unedited(block, name, stored_prep, page_id=None, section_id=None):
    """True if a stored section still holds the demo content it was seeded with — i.e. an
    editor hasn't changed it yet. Compares against the block's own default, the
    synthesised demo value, and the real instance used as demo (unless this section *is*
    that real instance). Can miss a section seeded from content that has since changed
    (a false "edited"), never the other way round."""
    if stored_prep is None:
        return False
    # ⚙ settings (background, anchor…) aren't content: changing them doesn't "edit" a section.
    from .mixins import builder_setting_names
    skip = set(builder_setting_names(block))

    def content(data):
        data = _strip_ids(data)
        if skip and isinstance(data, dict):
            return {k: v for k, v in data.items() if k not in skip}
        return data
    stored_prep = content(stored_prep)
    candidates = [_prep(block, block.get_default())]
    preview = explicit_preview_value(block)
    if preview is not None:
        candidates.append(_prep(block, preview))
    try:
        candidates.append(_prep(block, block.normalize(synth_value(block, name, seed=name))))
    except Exception:
        pass
    from .registry import is_builtin
    value, src_page, src_id = instance_index().get((name, is_builtin(block)), (None, None, None))
    is_source = (src_page is not None and str(getattr(src_page, "pk", "")) == str(page_id)
                 and src_id == str(section_id))
    if value is not None and not is_source:
        candidates.append(_prep(block, value))
    return any(c is not None and content(c) == stored_prep for c in candidates)


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
    """A deterministic demo value for a top-level block.

    1. The block's own Wagtail ``preview_value``, if the developer set one.
    2. Built-in blocks (``prblm_builder.blocks``): their explanatory default content.
    3. A real instance of the block used somewhere on the site (real images + copy).
    4. Synthesised content. Pass ``prefer_real=False`` to skip step 3.
    """
    preview = explicit_preview_value(block)
    if preview is not None:
        return preview
    from .registry import is_builtin
    if is_builtin(block):
        return block.get_default()
    if prefer_real:
        real = real_value_for(name)
        if real is not None:
            return real
    return block.normalize(synth_value(block, name, seed=name))


# ---------------------------------------------------------------- iframe frame
def _urls(request, items):
    out = []
    for it in items:
        out.append(it if it.startswith(("http://", "https://", "//")) else request.build_absolute_uri(static(it)))
    return out


def frame(block_html, request):
    parts = [
        '<!doctype html><html><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
    ]
    for url in _urls(request, cfg.preview_css()):
        parts.append(f'<link rel="stylesheet" href="{url}">')
    # No body padding: on the builder canvas sections stack flush, like a real page.
    parts.append("<style>html,body{margin:0;background:#fff}</style>")
    parts.append(f'</head><body class="{cfg.preview_body_class()}">')
    # Previews are scaled/offscreen, so lazy images never enter the frame's viewport and
    # would load partially — then the measured height is wrong (the section shows as a
    # thin stripe). Strip loading="lazy" so every image loads eagerly: the iframe's load
    # event waits for them, so the height is correct in a single measure.
    parts.append(re.sub(r'\sloading=(["\'])lazy\1', " ", str(block_html)))
    for url in _urls(request, cfg.preview_js()):
        parts.append(f'<script src="{url}"></script>')
    parts.append("</body></html>")
    return "".join(parts)
