"""Demo content for new sections and previews — chosen field by field.

For every field of a block, the first of these that has something:

1. the block's own ``preview_value`` (it may leave fields out),
2. real content of the **same block** (same class) on a live page — only sections an editor
   changed (never the plugin's own unedited demo content) and only values that validate,
3. the field's own ``default``,
4. generated content: neutral, labelled placeholder text sized to the field ("Section
   heading", "Short description … (1–2 sentences)"), an image that fits the field's role
   (wide photo for a banner, square / vector for a logo), one consistent link, list sizes
   from ``min_num`` / ``max_num``.

The result is checked with the block's own ``clean()``; a field that fails falls back a step
(generated, then empty). Built-in blocks keep their own explanatory example content.
"""
import hashlib
import json
import re
import time
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock

from . import settings as cfg

MISSING = object()

PLACEHOLDER_PREFIX = "Builder placeholder"
PLACEHOLDER_COLLECTION = "Builder placeholders"

IDENTIFIER_FIELDS = {"anchor", "anchor_id", "slug", "id", "css_class", "classname", "class_name"}
URL_FIELDS = {"url", "link", "href", "website", "link_url", "custom_url", "external_url"}
PHONE_FIELDS = {"phone", "tel", "telephone", "phone_number"}
EMAIL_FIELDS = {"email", "email_address"}
# Fields of a link-like StructBlock that hold its destination (one per link type).
DESTINATION_FIELDS = {"page", "url", "custom_url", "external_url", "link", "href", "anchor",
                      "document", "file", "doc", "email", "phone", "tel"}
HEADING_WORDS = ("heading", "title", "headline", "subtitle", "subheading", "label", "name", "kicker",
                 "eyebrow", "caption", "tagline")
BODY_WORDS = ("body", "content", "rich_text", "richtext", "article", "main_text")
WIDE_WORDS = ("background", "hero", "banner", "cover", "header", "bg", "slide", "carousel", "wide",
              "panorama", "feature_image", "featured")
SQUARE_WORDS = ("logo", "icon", "avatar", "badge", "favicon", "emblem", "signature", "seal",
                "headshot", "portrait", "profile")
VIDEO_WORDS = ("video", "youtube", "vimeo", "embed")


# --------------------------------------------------------------------------- helpers
def _is_empty(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    source = getattr(value, "source", None)          # RichText
    if isinstance(source, str):
        return not strip_tags(source).strip()
    if isinstance(value, (list, tuple)):
        return not value
    if isinstance(value, (blocks.list_block.ListValue, blocks.StreamValue)):
        return len(value) == 0
    return False


def _all_blank(value):
    """True when a value holds nothing at all (empty fields all the way down)."""
    value = getattr(value, "value", value) if not isinstance(value, (str, dict)) and hasattr(value, "block") else value
    if isinstance(value, dict):
        return all(_all_blank(v) for v in value.values())
    if isinstance(value, (list, tuple, blocks.list_block.ListValue)):
        return all(_all_blank(v) for v in value)
    if isinstance(value, bool):
        return not value
    return _is_empty(value)


def _get(value, key):
    if value is MISSING or value is None:
        return MISSING
    try:
        got = value[key] if hasattr(value, "__getitem__") and not isinstance(value, str) else MISSING
    except (KeyError, IndexError, TypeError):
        return MISSING
    return MISSING if _is_empty(got) else got


def _meta(block, attr):
    value = getattr(block.meta, attr, None)
    if value is None:
        value = getattr(getattr(block, "field", None), attr, None)
    return value


def _label(block, name):
    label = getattr(block, "label", None) or getattr(block.meta, "label", None)
    if not label:
        label = (name or "text").replace("_", " ")
    return str(label)


_INSTRUCTION = re.compile(r"^(e\.?g\b|eg\b|ex\b|http|leave|optional|use |enter |choose|select|pick|"
                          r"the |a |an |if |when |this |shown |only |will |must |max|min|add )", re.I)


def _sentence_case(text):
    words = text.split()
    out = []
    for i, w in enumerate(words):
        if len(w) <= 5 and w.isupper():            # URL, FAQ, CTA…
            out.append(w)
        elif i == 0:
            out.append(w[:1].upper() + w[1:].lower())
        else:
            out.append(w.lower())
    return " ".join(out)


def _phrase(block, name):
    """What the field is, in a few words: its help text when that's a short name for it
    ("Section heading line one"), else its label ("Button label")."""
    help_text = str(_meta(block, "help_text") or "").strip().rstrip(".").strip()
    if (help_text and len(help_text.split()) <= 7 and not re.search(r"[.?:;!()]", help_text)
            and not _INSTRUCTION.match(help_text)):
        return _sentence_case(help_text)
    return _sentence_case(_label(block, name))


def _fit(text, max_length):
    if max_length and len(text) > max_length:
        text = text[:max_length].rsplit(" ", 1)[0] if " " in text[:max_length] else text[:max_length]
    return text


def _key(name):
    return (name or "").lower()


def _has(name, words):
    key = _key(name)
    return any(w in key for w in words)


# --------------------------------------------------------------------------- text
def _char_text(block, name, ctx):
    key = _key(name)
    max_length = _meta(block, "max_length")
    if key in IDENTIFIER_FIELDS:
        return ""
    if key in URL_FIELDS or key.endswith("_url"):
        return _site_url(video=_has(name, VIDEO_WORDS))
    if key in PHONE_FIELDS:
        return "+1 555 0100"
    if key in EMAIL_FIELDS:
        return "name@example.com"
    if ctx.get("link") and key in ("label", "text", "title", "link_text", "button_text"):
        text = "Button label" if ctx.get("button") else "Link text"
    else:
        text = _phrase(block, name)
    if ctx.get("index") is not None:
        text = f"{text} {ctx['index'] + 1}"
    return _fit(text, max_length)


def _long_text(block, name, ctx):
    phrase = _phrase(block, name)
    if ctx.get("index") is not None:
        phrase = f"{phrase} {ctx['index'] + 1}"
    text = f"{phrase} — replace this with one or two sentences of your own."
    return _fit(text, _meta(block, "max_length"))


def _rich_text(block, name, ctx):
    phrase = _phrase(block, name)
    if ctx.get("index") is not None:
        phrase = f"{phrase} {ctx['index'] + 1}"
    if _has(name, HEADING_WORDS):
        return f"<p>{phrase}</p>"
    first = (f"<p><b>{phrase}.</b> Replace this with a short paragraph of your own: what this "
             f"part of the page is about and why it matters to your visitors.</p>")
    if _has(name, BODY_WORDS):
        return first + ("<p>A second paragraph can add detail, an example or a next step. Keep "
                        "paragraphs short so the page is easy to scan.</p>")
    return first


# --------------------------------------------------------------------------- pages, links
_CACHE = {}
_STAMPS = {}
# How often (seconds) a server process asks the database whether site content changed —
# so a page loading 30 thumbnails at once asks once, not 30 times.
STAMP_EVERY = 2.0


def _content_stamp():
    """Changes when a page is published, unpublished or deleted (demo content only uses
    published pages; saving a draft doesn't matter)."""
    from django.db.models import Count, Max
    from wagtail.models import Page
    agg = Page.objects.filter(live=True).aggregate(n=Count("id"), last=Max("last_published_at"))
    return (agg["n"], str(agg["last"]))


def _seeded_stamp():
    from django.db.models import Count, Max

    from .models import SeededSection
    agg = SeededSection.objects.aggregate(n=Count("id"), last=Max("id"))
    return (agg["n"], agg["last"])


def _images_stamp():
    from django.db.models import Count, Max
    from wagtail.images import get_image_model
    agg = get_image_model().objects.aggregate(n=Count("id"), last=Max("id"))
    return (agg["n"], agg["last"])


def _documents_stamp():
    from django.db.models import Count, Max
    from wagtail.documents import get_document_model
    agg = get_document_model().objects.aggregate(n=Count("id"), last=Max("id"))
    return (agg["n"], agg["last"])


_STAMP_FNS = {"content": _content_stamp, "seeded": _seeded_stamp,
              "images": _images_stamp, "documents": _documents_stamp}


def _stamp(kind):
    """A cheap value that changes whenever ``kind`` of site data changes (one small query,
    at most every ``STAMP_EVERY`` seconds per process)."""
    now = time.time()
    hit = _STAMPS.get(kind)
    if hit is None or now - hit[0] >= STAMP_EVERY:
        try:
            value = _STAMP_FNS[kind]()
        except Exception:
            value = ("unknown", now)          # can't tell → rebuild
        hit = _STAMPS[kind] = (now, value)
    return hit[1]


def _cached(key, fn, depends=("content",)):
    """``fn()``, kept until the site data it ``depends`` on changes — no timer: nothing is
    rebuilt while nothing is published, unpublished, deleted or uploaded."""
    version = tuple(_stamp(k) for k in depends)
    hit = _CACHE.get(key)
    if hit is None or hit[0] != version:
        try:
            value = fn()
        except Exception:
            value = None
        hit = _CACHE[key] = (version, value)
        if key == "index":                     # validity checks of the old index's values
            for k in [k for k in _CACHE if isinstance(k, tuple) and k[0] == "valid"]:
                del _CACHE[k]
    return hit[1]


def reset_caches():
    """Forget cached site content (tests; after big imports)."""
    _CACHE.clear()
    _STAMPS.clear()


def _site_url(video=False):
    if video:
        return "https://www.youtube.com/watch?v=A8VRZd17stk"

    def root():
        from wagtail.models import Site
        site = Site.objects.filter(is_default_site=True).first() or Site.objects.first()
        return (site.root_url.rstrip("/") + "/") if site else None
    return _cached("site_url", root) or "https://example.com/"


def _page_for(block=None):
    """A real live page to link to: an inner page if there is one, else the home page."""
    model = None
    try:
        model = block.target_model if block is not None else None
    except Exception:
        model = None

    def find():
        from wagtail.models import Page
        qs = (model or Page).objects.live().public() if model else Page.objects.live().public()
        return qs.filter(depth__gt=2).order_by("path").first() or qs.filter(depth__gt=1).order_by("path").first()
    label = model._meta.label if model is not None else "page"
    return _cached(("page", label), find)


def _link_choice(block):
    """``(choice_field_name, {choice: destination_field})`` when ``block`` is a link-like
    StructBlock — a dropdown whose choices name its sibling fields (page / url / email…) —
    else ``None``. Covers the built-in LinkBlock and packages like wagtail-link-block."""
    if not isinstance(block, blocks.StructBlock):
        return None
    names = set(block.child_blocks)
    for cname, child in block.child_blocks.items():
        if not isinstance(child, blocks.ChoiceBlock):
            continue
        choices = [c[0] for c in (child.field.choices or []) if c[0]]
        mapping = {}
        for c in choices:
            if c in names and c in DESTINATION_FIELDS:
                mapping[c] = c
        if len(mapping) >= 2:
            return cname, mapping
    return None


def _gen_destination(field_block, field_name):
    """A value for one link destination field, or MISSING when we can't make a good one."""
    key = _key(field_name)
    if key == "page":
        page = _page_for(field_block)
        return page if page is not None else MISSING
    if key in ("url", "custom_url", "external_url", "link", "href"):
        return "/"
    if key in ("anchor",):
        return "top"
    if key in ("email",):
        return "name@example.com"
    if key in ("phone", "tel"):
        return "+1 555 0100"
    if key in ("document", "file", "doc"):
        doc = _document_for(field_block, required=True)
        return doc if doc is not None else MISSING
    return MISSING


# --------------------------------------------------------------------------- images
def _image_role(block, name):
    text = " ".join([_key(name), _label(block, name).lower(), str(_meta(block, "help_text") or "").lower()])
    if any(w in text for w in SQUARE_WORDS):
        return "square"
    if any(w in text for w in WIDE_WORDS):
        return "wide"
    return "photo"


def _image_catalog():
    """``[{id, w, h, vector, alpha}]`` for the site's images (placeholders excluded,
    missing files skipped), newest first, capped."""
    def build():
        from wagtail.images import get_image_model
        Image = get_image_model()
        out = []
        for img in Image.objects.exclude(title__startswith=PLACEHOLDER_PREFIX).order_by("-id")[:300]:
            name = (img.file.name or "").lower()
            try:
                if not img.file.storage.exists(img.file.name):
                    continue
            except Exception:
                continue
            vector = name.endswith(".svg")
            alpha = False
            if not vector and name.endswith((".png", ".webp", ".gif")):
                try:
                    from PIL import Image as PILImage
                    with img.open_file() as fh:
                        im = PILImage.open(fh)
                        alpha = im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info
                except Exception:
                    alpha = False
            out.append({"id": img.id, "w": img.width or 0, "h": img.height or 0,
                        "vector": vector, "alpha": alpha})
        return out
    return _cached("images", build, depends=("images",)) or []


def _fits(c, role):
    w, h = c["w"], c["h"]
    ratio = (w / h) if w and h else 0
    if role == "wide":
        return not c["vector"] and not c["alpha"] and w >= 1000 and ratio >= 1.3
    if role == "square":
        return c["vector"] or c["alpha"] or (0.75 <= ratio <= 1.34)
    return not c["vector"] and not c["alpha"] and w >= 400 and 0.6 <= ratio <= 2.2


ROLE_PLACEHOLDERS = {"wide": ("Banner", 1600, 900), "square": ("Logo / icon", 400, 400),
                     "photo": ("Photo", 1200, 800)}


def _image_for(block, name, seed, index=None):
    role = _image_role(block, name)
    fits = [c for c in _image_catalog() if _fits(c, role)]
    if fits:
        from wagtail.images import get_image_model
        # List items take the next image in turn, so they don't repeat while there are enough.
        base = re.sub(r"\.\d+(?=\.|$)", "", seed)
        start = int(hashlib.sha1(base.encode()).hexdigest(), 16)
        pick = fits[(start + (index or 0)) % len(fits)]
        img = get_image_model().objects.filter(id=pick["id"]).first()
        if img is not None:
            return img
    return placeholder_image(role)


def _placeholder_collection():
    from wagtail.models import Collection
    existing = Collection.objects.filter(name=PLACEHOLDER_COLLECTION).first()
    if existing:
        return existing
    return Collection.get_first_root_node().add_child(name=PLACEHOLDER_COLLECTION)


def placeholder_image(role="photo"):
    """A labelled placeholder Wagtail Image of the role's shape ("Banner · 1600×900"),
    created once in the "Builder placeholders" collection and reused. ``None`` when
    ``PRBLM_BUILDER_PLACEHOLDER_IMAGES`` is off."""
    if not cfg.placeholder_images():
        return None
    label, width, height = ROLE_PLACEHOLDERS.get(role, ROLE_PLACEHOLDERS["photo"])

    def make():
        from io import BytesIO

        from django.core.files.images import ImageFile
        from wagtail.images import get_image_model
        Image = get_image_model()
        title = f"{PLACEHOLDER_PREFIX} — {label} {width}x{height}"
        existing = Image.objects.filter(title=title).first()
        if existing:
            return existing
        from PIL import Image as PILImage
        from PIL import ImageDraw, ImageFont
        im = PILImage.new("RGB", (width, height), (229, 233, 240))
        draw = ImageDraw.Draw(im)
        for y in range(height):
            t = y / max(1, height - 1)
            draw.line([(0, y), (width, y)], fill=(int(229 - 30 * t), int(233 - 24 * t), int(240 - 12 * t)))
        text = f"{label} · {width}×{height}"
        try:
            font = ImageFont.load_default(size=max(14, width // 24))
        except Exception:
            font = ImageFont.load_default()
        box = draw.textbbox((0, 0), text, font=font)
        draw.text(((width - (box[2] - box[0])) / 2, (height - (box[3] - box[1])) / 2), text,
                  fill=(110, 118, 134), font=font)
        buf = BytesIO()
        im.save(buf, "PNG")
        buf.seek(0)
        img = Image(title=title, collection=_placeholder_collection())
        slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
        img.file.save(f"builder-placeholder-{slug}-{width}x{height}.png", ImageFile(buf), save=False)
        img.width, img.height = width, height
        img.file_size = img.file.size
        img.save()
        return img
    return _cached(("placeholder", role), make, depends=("images",))


# --------------------------------------------------------------------------- documents
def _document_for(block, required=False):
    """A document for a chooser: optional fields stay empty; a required one gets a PDF
    from the library if any, else any document, else a small "Example document"."""
    if not required:
        return None

    def find():
        from wagtail.documents import get_document_model
        Document = get_document_model()
        doc = Document.objects.filter(file__iendswith=".pdf").order_by("id").first() or \
            Document.objects.order_by("id").first()
        if doc is not None or not cfg.placeholder_images():
            return doc
        from django.core.files.base import ContentFile
        doc = Document(title=f"{PLACEHOLDER_PREFIX} — Example document", collection=_placeholder_collection())
        doc.file.save("builder-example-document.txt",
                      ContentFile(b"Example document - replace it with your own file.\n"), save=False)
        doc.save()
        return doc
    return _cached("document", find, depends=("documents",))


# --------------------------------------------------------------------------- generation
def _list_count(block):
    """3 items, or more if ``min_num`` asks for more, never above ``max_num``."""
    min_num = getattr(block.meta, "min_num", None) or 0
    max_num = getattr(block.meta, "max_num", None)
    count = max(min_num, 3)
    if max_num is not None:
        count = min(count, max_num)
    return max(0, count)


def _default(block):
    try:
        value = block.get_default()
    except Exception:
        return MISSING
    if isinstance(block, (blocks.StructBlock, blocks.StreamBlock)):
        return MISSING                        # handled field by field
    if isinstance(block, blocks.ListBlock):
        # Only a default the developer set: Wagtail makes one up itself (an item full of
        # empty fields).
        return MISSING if _all_blank(value) else value
    return MISSING if _is_empty(value) else value


def generate(block, name, ctx):
    """Step 4: a generated value for a leaf block (struct/list/stream recurse in _pick)."""
    seed = ctx.get("seed", name or "")
    required = getattr(block, "required", False) or getattr(getattr(block, "field", None), "required", False)
    if isinstance(block, ImageChooserBlock):
        return _image_for(block, name, seed, ctx.get("index"))
    if isinstance(block, DocumentChooserBlock):
        return _document_for(block, required=required)
    if isinstance(block, blocks.PageChooserBlock):
        return _page_for(block)
    if isinstance(block, blocks.ChooserBlock):
        try:
            return block.model_class.objects.first()
        except Exception:
            return None
    if isinstance(block, blocks.ChoiceBlock):
        choices = [c[0] for c in (block.field.choices or []) if c[0] not in ("", None)]
        return choices[0] if choices else None
    if isinstance(block, blocks.MultipleChoiceBlock):
        choices = [c[0] for c in (block.field.choices or []) if c[0] not in ("", None)]
        return choices[:1]
    if isinstance(block, blocks.RichTextBlock):
        return _rich_text(block, name, ctx)
    if isinstance(block, blocks.BooleanBlock):
        return bool(block.get_default())
    if isinstance(block, (blocks.IntegerBlock, blocks.FloatBlock, blocks.DecimalBlock)):
        low = _meta(block, "min_value")
        return low if low is not None else 3
    if isinstance(block, blocks.URLBlock):
        return _site_url(video=_has(name, VIDEO_WORDS))
    if isinstance(block, blocks.EmailBlock):
        return "name@example.com"
    if isinstance(block, blocks.DateTimeBlock):
        from django.utils import timezone
        return timezone.now() + timedelta(days=12, hours=5)
    if isinstance(block, blocks.DateBlock):
        return date.today() + timedelta(days=12)
    if isinstance(block, blocks.TimeBlock):
        return "10:00"
    if isinstance(block, (blocks.TextBlock, blocks.BlockQuoteBlock)):
        return _long_text(block, name, ctx)
    if isinstance(block, blocks.RawHTMLBlock):
        return ""
    if isinstance(block, blocks.CharBlock) or isinstance(block, blocks.RegexBlock):
        return _char_text(block, name, ctx)
    try:
        from wagtail.embeds.blocks import EmbedBlock
        if isinstance(block, EmbedBlock):
            return "https://www.youtube.com/watch?v=A8VRZd17stk"
    except Exception:
        pass
    try:
        return block.get_default()
    except Exception:
        return None


def _pick(block, name, preview, real, ctx, depth=0):
    """The value for one block/field: preview → real → default → generated."""
    if depth > 8:
        return None
    if isinstance(block, blocks.StructBlock):
        return _pick_struct(block, name, preview, real, ctx, depth)
    if isinstance(block, blocks.ListBlock):
        if preview is not MISSING:
            return list(preview)
        child = block.child_block
        if real is not MISSING:
            return [_pick(child, name, MISSING, _item(v), dict(ctx, seed=f"{ctx.get('seed', '')}.{i}"), depth + 1)
                    for i, v in enumerate(real)]
        default = _default(block)
        if default is not MISSING:          # the developer's items, gaps filled
            return [_pick(child, name, _item(v), MISSING, dict(ctx, index=i, seed=f"{ctx.get('seed', '')}.{i}"),
                          depth + 1) for i, v in enumerate(default)]
        return [_pick(child, name, MISSING, MISSING,
                      dict(ctx, index=i, seed=f"{ctx.get('seed', '')}.{i}"), depth + 1)
                for i in range(_list_count(block))]
    if isinstance(block, blocks.StreamBlock):
        if preview is not MISSING:
            return preview
        if real is not MISSING:
            return real
        min_num = getattr(block.meta, "min_num", None) or 0
        kinds = list(block.child_blocks.items())[: max(min_num, 2)]
        return [(cn, _pick(c, cn, MISSING, MISSING, dict(ctx, seed=f"{ctx.get('seed', '')}.{cn}"), depth + 1))
                for cn, c in kinds]
    if preview is not MISSING:
        return preview
    if real is not MISSING:
        return real
    default = _default(block)
    if default is not MISSING:
        return default
    return generate(block, name, ctx)


def _item(value):
    """A list item's value (ListValue items may be bound blocks)."""
    return getattr(value, "value", value)


def _pick_struct(block, name, preview, real, ctx, depth):
    link = _link_choice(block)
    out = {}
    link_fields = set()
    if link is not None:
        choice_name, mapping = link
        link_fields = {choice_name, *mapping.values()}
        out.update(_pick_link(block, choice_name, mapping, preview, real))
    for cname, child in block.child_blocks.items():
        if cname in link_fields:
            continue
        sub = dict(ctx, seed=f"{ctx.get('seed', '')}.{cname}")
        if link is not None:
            sub["link"] = True
            sub["button"] = _has(name, ("button", "cta", "action"))
        else:
            sub.pop("link", None)
        out[cname] = _pick(child, cname, _get(preview, cname), _get(real, cname), sub, depth + 1)
    return out


def _pick_link(block, choice_name, mapping, preview, real):
    """One consistent link: the type and only its destination field."""
    choice_block = block.child_blocks[choice_name]
    empty = {}
    for field_name in set(mapping.values()):
        child = block.child_blocks[field_name]
        empty[field_name] = None if isinstance(child, blocks.ChooserBlock) else ""
    for source in (preview, real):
        kind = _get(source, choice_name)
        if kind is not MISSING and kind in mapping and _get(source, mapping[kind]) is not MISSING:
            return {**empty, choice_name: kind, mapping[kind]: _get(source, mapping[kind])}
    preferred = ["page", "url", "custom_url", "external_url", "anchor", "email", "phone", "document", "file"]
    order = [c for c in preferred if c in mapping] + [c for c in mapping if c not in preferred]
    for kind in order:
        field_name = mapping[kind]
        value = _gen_destination(block.child_blocks[field_name], field_name)
        if value is not MISSING:
            return {**empty, choice_name: kind, field_name: value}
    default = choice_block.get_default()
    return {**empty, choice_name: default if default else None}


# --------------------------------------------------------------------------- validation
def _first_error(err):
    if isinstance(err, (list, tuple)):
        data = err.as_data() if hasattr(err, "as_data") else list(err)
        return data[0] if data else None
    return err


def _repair(block, name, value, error, stage, ctx):
    """``value`` with the parts that failed validation replaced: stage 0 → generated
    content, stage 1 → empty, stage 2 → also reset a failing struct's dropdowns (in link
    blocks the dropdown decides which field is required)."""
    errs = getattr(_first_error(error), "block_errors", None)
    try:
        if isinstance(block, blocks.StructBlock) and isinstance(errs, dict) and errs:
            out = dict(value)
            for cname, cerr in errs.items():
                child = block.child_blocks.get(cname)
                if child is not None:
                    out[cname] = _repair(child, cname, out.get(cname), cerr, stage,
                                         dict(ctx, seed=f"{ctx.get('seed', '')}.{cname}"))
            if stage >= 2:
                for cname, child in block.child_blocks.items():
                    if isinstance(child, blocks.ChoiceBlock):
                        out[cname] = child.normalize(child.get_default())
            return block.normalize(out)
        if isinstance(block, blocks.ListBlock) and isinstance(errs, dict) and errs:
            items = [_item(v) for v in value]
            for i, cerr in errs.items():
                if isinstance(i, int) and 0 <= i < len(items):
                    items[i] = _repair(block.child_block, name, items[i], cerr, stage, ctx)
            return block.normalize(items)
    except Exception:
        pass
    if stage <= 1 and not isinstance(block, (blocks.StructBlock, blocks.ListBlock, blocks.StreamBlock)):
        if stage == 0:
            try:
                value = block.normalize(generate(block, name, ctx))
                block.clean(value)
                return value
            except Exception:
                pass
        shaped = _pattern_value(block)          # e.g. a field that must look like "/path/"
        if shaped is not MISSING:
            return shaped
    return block.normalize(block.get_default())


# Common shapes tried, in order, for text fields with a pattern (RegexBlock, validators).
PATTERN_CANDIDATES = ["/", "/page/", "https://example.com/", "example", "Example", "123",
                      "#section", "example-1", "name@example.com", "+10000000000", "2026"]


def _pattern_value(block):
    """The first common value that passes a text field's own validation, or MISSING."""
    if not isinstance(block, (blocks.CharBlock, blocks.RegexBlock, blocks.TextBlock, blocks.URLBlock,
                              blocks.FieldBlock)) or isinstance(block, (blocks.ChooserBlock, blocks.ChoiceBlock)):
        return MISSING
    for candidate in PATTERN_CANDIDATES:
        try:
            value = block.normalize(candidate)
            block.clean(value)
            return value
        except Exception:
            continue
    return MISSING


def validated(block, name, value):
    """``value`` made to pass ``block.clean()`` where possible (see ``_repair``)."""
    for stage in range(4):
        try:
            block.clean(value)
            return value
        except ValidationError as exc:
            value = _repair(block, name, value, exc, min(stage, 2), {"seed": name or ""})
        except Exception:
            return value
    return value


def problem(block, value):
    """Why ``value`` fails the block's validation (``"field: message"``), or ``None``."""
    try:
        block.clean(value)
        return None
    except ValidationError as exc:
        path, err = [], exc
        while True:
            errs = getattr(_first_error(err), "block_errors", None)
            if not isinstance(errs, dict) or not errs:
                break
            key, err = next(iter(errs.items()))
            path.append(str(key))
        first = _first_error(err)
        message = "; ".join(getattr(first, "messages", None) or [str(first)])
        return f"{'.'.join(path) or 'value'}: {message}"
    except Exception as exc:
        return type(exc).__name__


# --------------------------------------------------------------------------- real content
def content_hash(block, prep):
    """A stable hash of a section's content — ⚙ settings left out (changing them doesn't
    "edit" a section), ids and rich-text keys normalised."""
    from .mixins import builder_setting_names
    from .previews import _canon
    data = _canon(prep)
    skip = set(builder_setting_names(block))
    if skip and isinstance(data, dict):
        data = {k: v for k, v in data.items() if k not in skip}
    return hashlib.sha1(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def record_seeded(section_id, block, prep):
    """Remember that the plugin filled section ``section_id`` with demo content, so it's
    never borrowed as real content and shows "Not edited yet" until someone changes it."""
    try:
        from .models import SeededSection
        SeededSection.objects.update_or_create(
            section_id=str(section_id), defaults={"value_hash": content_hash(block, prep)})
    except Exception:
        pass


def seeded_hashes():
    def load():
        from .models import SeededSection
        return dict(SeededSection.objects.values_list("section_id", "value_hash"))
    return _cached("seeded", load, depends=("seeded",)) or {}


def seeded_hash(section_id):
    """The hash a seeded section had when the plugin filled it, or ``None``."""
    if not section_id:
        return None
    try:
        from .models import SeededSection
        row = SeededSection.objects.filter(section_id=str(section_id)).values_list("value_hash", flat=True).first()
        return row
    except Exception:
        return None


def _score(block, prep):
    """How well-filled a real section is: (filled fields, images, stored length). Filled
    fields count nested lists and structs, so a section with every field set beats one
    with a single long text."""
    counts = [0, 0]

    def walk(b, v, depth=0):
        if depth > 10:
            return
        if isinstance(b, blocks.StructBlock):
            if isinstance(v, dict):
                for cname, child in b.child_blocks.items():
                    walk(child, v.get(cname), depth + 1)
            return
        if isinstance(b, blocks.ListBlock):
            for item in v or []:
                if isinstance(item, dict) and "value" in item and "type" in item:
                    item = item["value"]
                walk(b.child_block, item, depth + 1)
            return
        if isinstance(b, blocks.StreamBlock):
            for item in v or []:
                if isinstance(item, dict):
                    child = b.child_blocks.get(item.get("type"))
                    if child is not None:
                        walk(child, item.get("value"), depth + 1)
            return
        if _is_empty(v) or v is False:
            return
        if isinstance(b, blocks.RichTextBlock) and isinstance(v, str) and not strip_tags(v).strip():
            return
        counts[0] += 1
        if isinstance(b, ImageChooserBlock):
            counts[1] += 1

    try:
        walk(block, prep)
    except Exception:
        pass
    return (counts[0], counts[1], len(json.dumps(prep, default=str)))


def _index():
    """``{"candidates": {block_key: [(value, page), …]}, "usage": {block_key: {page_id: page}}}``
    from live pages (newest first, ``PRBLM_BUILDER_INDEX_SCAN_LIMIT`` per model). Candidates
    leave out sections still holding the plugin's demo content; best-filled first."""
    def build():
        from django.apps import apps
        from wagtail.fields import StreamField
        from wagtail.models import Page

        from .previews import legacy_unedited
        from .registry import block_key
        seeded = seeded_hashes()
        cands, usage = {}, {}
        for model in apps.get_models():
            if not (issubclass(model, Page) and model is not Page):
                continue
            sfs = [f.name for f in model._meta.get_fields() if isinstance(f, StreamField)]
            if not sfs:
                continue
            try:
                pages = list(model.objects.live().order_by("-pk")[: cfg.index_scan_limit()])
            except Exception:
                continue
            for page in pages:
                for fname in sfs:
                    try:
                        value = getattr(page, fname)
                    except Exception:
                        continue
                    for child in value:
                        key = block_key(child.block_type, child.block)
                        usage.setdefault(key, {})[page.pk] = page
                        try:
                            prep = child.block.get_prep_value(child.value)
                        except Exception:
                            continue
                        sid = str(child.id)
                        if sid in seeded:
                            if content_hash(child.block, prep) == seeded[sid]:
                                continue                      # the plugin's own, never edited
                        elif legacy_unedited(child.block, child.block_type, prep):
                            continue
                        score = _score(child.block, prep)
                        cands.setdefault(key, []).append((score, child.value, page))
        for key in cands:
            cands[key].sort(key=lambda t: t[0], reverse=True)
            cands[key] = [(v, p) for _s, v, p in cands[key][:8]]
        return {"candidates": cands, "usage": usage}
    return _cached("index", build, depends=("content", "seeded")) or {"candidates": {}, "usage": {}}


def real_instance(name, block):
    """``(value, page)``: the best-filled valid real instance of ``block`` on a live page, or
    ``(None, None)``. Built-in blocks never borrow (they show their own examples)."""
    from .registry import block_key, is_builtin
    if not name or block is None or is_builtin(block):
        return None, None
    key = block_key(name, block)
    for value, page in _index()["candidates"].get(key, []):
        ok = _cached(("valid", key, id(value)), lambda v=value: problem(block, v) is None,
                     depends=("content", "seeded"))
        if ok:
            return value, page
    return None, None


def usage(name, block, site=None):
    """``[page, …]`` live pages that use ``block`` (any name, same class) — only those of
    ``site`` (a Wagtail Site) when given."""
    from .registry import block_key
    pages = list(_index()["usage"].get(block_key(name, block), {}).values())
    if site is not None:
        root = getattr(site.root_page, "path", "") if site.root_page_id else ""
        pages = [p for p in pages if root and p.path.startswith(root)]
    return sorted(pages, key=lambda p: p.title.lower())


# --------------------------------------------------------------------------- entry point
def preview_value_raw(block):
    """The block's ``preview_value`` as the developer wrote it (may be partial), or MISSING."""
    value = getattr(block.meta, "preview_value", None)
    return MISSING if value is None else value


def build(block, name="", real=True):
    """``(value, page)``: demo content for a new section of ``block`` (see module docs) and
    the page the borrowed real content came from (context for blocks that read page
    fields), or ``None``."""
    from .registry import is_builtin
    if is_builtin(block) and preview_value_raw(block) is MISSING:
        return block.get_default(), None
    preview = preview_value_raw(block)
    real_value, page = real_instance(name, block) if real else (None, None)
    raw = _pick(block, name, preview, MISSING if real_value is None else real_value, {"seed": name or ""})
    try:
        value = block.normalize(raw)
    except Exception:
        value = block.normalize(block.get_default())
    return validated(block, name, value), page
