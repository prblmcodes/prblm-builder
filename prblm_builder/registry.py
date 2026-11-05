"""Introspect a site's page models and StreamField blocks — no site-specific code.

The builder asks the *models* what blocks exist rather than keeping a hand-list,
so it works unchanged on any Wagtail project.
"""
from django.apps import apps as django_apps
from wagtail.fields import StreamField
from wagtail.models import Page

from . import settings as cfg

UNGROUPED = "Other"


def _streamfields(model):
    return [f for f in model._meta.get_fields() if isinstance(f, StreamField)]


def target_field_name(model):
    """The StreamField name to build on this model — the first configured name
    (default ``body``) that the model actually has, else None."""
    names = {f.name for f in _streamfields(model)}
    for n in cfg.field_names():
        if n in names:
            return n
    return None


def enabled_page_models():
    """Page models the builder operates on: the configured ``PRBLM_BUILDER_PAGE_MODELS``
    list, or (unset) every Page subclass that has a target StreamField."""
    configured = cfg.page_models()
    out = []
    for model in django_apps.get_models():
        if not issubclass(model, Page) or model is Page:
            continue
        if target_field_name(model) is None:
            continue
        label = f"{model._meta.app_label}.{model.__name__}"
        if configured is not None and label not in configured:
            continue
        out.append(model)
    return out


def stream_block_for(model, field_name=None):
    """``(field_name, stream_block)`` for a model's target StreamField, or (None, None)."""
    field_name = field_name or target_field_name(model)
    if field_name is None:
        return None, None
    return field_name, model._meta.get_field(field_name).stream_block


def block_label(name, block):
    return getattr(block.meta, "label", None) or name.replace("_", " ").title()


def previewable(name, block):
    """A block worth showing: it has a template of its own and isn't excluded
    (e.g. newsletter email blocks)."""
    template = getattr(block.meta, "template", None)
    if not template:
        return False
    return not template.startswith(cfg.exclude_template_prefixes())


def _group(blocks_iter):
    """``[(group, [(name, block, label), …]), …]`` from an iterable of (name, block)."""
    groups = {}
    for name, block in blocks_iter:
        if not previewable(name, block):
            continue
        g = (getattr(block.meta, "group", "") or "").strip() or UNGROUPED
        groups.setdefault(g, []).append((name, block, block_label(name, block)))
    for v in groups.values():
        v.sort(key=lambda t: t[2].lower())
    ordered = sorted((g for g in groups if g != UNGROUPED), key=str.lower)
    if UNGROUPED in groups:
        ordered.append(UNGROUPED)
    return [(g, groups[g]) for g in ordered]


def grouped_blocks(stream_block):
    """Grouped previewable blocks a single StreamField allows (for the builder palette)."""
    return _group(stream_block.child_blocks.items())


def all_blocks():
    """``{name: block}`` for every previewable block anywhere in the project (deduped).

    Walks every model's StreamFields — the demo/block-library page shows the whole
    catalogue, not just one field's.
    """
    found = {}
    for model in django_apps.get_models():
        for field in model._meta.get_fields():
            if not isinstance(field, StreamField):
                continue
            for name, block in field.stream_block.child_blocks.items():
                if previewable(name, block):
                    found.setdefault(name, block)
    return found


def grouped_all_blocks():
    """Grouped previewable blocks across the whole project (for the demo page)."""
    return _group(all_blocks().items())


def find_block(name):
    """A previewable block by name, searched across the project (for demo previews)."""
    return all_blocks().get(name)
