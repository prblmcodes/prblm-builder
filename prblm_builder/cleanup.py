"""Removing demo-content records (``SeededSection``) whose section is gone.

A record is keyed by the section's id only. When a page is deleted, the ids of its sections
are collected (live content and every revision); once the delete is committed, the
records of those ids that no remaining page or revision still contains are removed — a
copied page keeps the same section ids, so its untouched sections stay "Not edited yet".
``manage.py prblm_builder_cleanup`` does the same for every record (old leftovers).
"""
import json

from django.db import transaction
from django.db.models import Q

CHUNK = 50


def _stream_ids(raw):
    """Top-level section ids in a StreamField's raw data (a list or its JSON text)."""
    if isinstance(raw, str):
        if not raw.lstrip().startswith("["):
            return set()
        try:
            raw = json.loads(raw)
        except ValueError:
            return set()
    if not isinstance(raw, list):
        return set()
    return {str(d["id"]) for d in raw if isinstance(d, dict) and d.get("id") and "type" in d}


def page_section_ids(page):
    """Every section id a page has: its StreamFields and all its revisions."""
    from wagtail.fields import StreamField
    ids = set()
    try:
        specific = page.specific
    except Exception:
        specific = page
    for field in type(specific)._meta.get_fields():
        if isinstance(field, StreamField):
            try:
                ids |= _stream_ids(list(getattr(specific, field.name).raw_data))
            except Exception:
                pass
    try:
        for content in page.revisions.values_list("content", flat=True):
            for value in (content or {}).values():
                ids |= _stream_ids(value)
    except Exception:
        pass
    return ids


def _stream_fields():
    from django.apps import apps
    from wagtail.fields import StreamField
    from wagtail.models import Page
    for model in apps.get_models():
        if issubclass(model, Page) and model is not Page:
            for field in model._meta.local_fields:
                if isinstance(field, StreamField):
                    yield model, field.name


def ids_in_use(ids):
    """The ids (of ``ids``) still found in a page's content or in any revision."""
    from wagtail.models import Revision
    ids = list(ids)
    found = set()
    for i in range(0, len(ids), CHUNK):
        chunk = [x for x in ids[i:i + CHUNK] if x not in found]
        if not chunk:
            continue
        sources = [(model._default_manager.all(), name) for model, name in _stream_fields()]
        sources.append((Revision.objects.all(), "content"))
        for qs, name in sources:
            query = Q()
            for sid in chunk:
                query |= Q(**{f"{name}__icontains": sid})
            try:
                for text in qs.filter(query).values_list(name, flat=True):
                    text = text if isinstance(text, str) else json.dumps(text, default=str)
                    found |= {sid for sid in chunk if sid in text}
            except Exception:
                found |= set(chunk)          # can't check → keep (never lose a record by error)
    return found


def forget(ids, dry_run=False):
    """Remove the records of ``ids`` that nothing uses any more; returns how many."""
    from .models import SeededSection
    ids = set(ids)
    if not ids:
        return 0
    unused = ids - ids_in_use(ids)
    qs = SeededSection.objects.filter(section_id__in=unused)
    count = qs.count()
    if not dry_run:
        qs.delete()
    return count


def orphans():
    """Ids of every record whose section no page or revision has any more."""
    from .models import SeededSection
    ids = set(SeededSection.objects.values_list("section_id", flat=True))
    return ids - ids_in_use(ids)


def page_deleted(sender, instance, **kwargs):
    """``pre_delete`` of a page: remember its section ids, forget them after the commit."""
    from wagtail.models import Page
    if not isinstance(instance, Page):
        return
    try:
        from .models import SeededSection
        if not SeededSection.objects.exists():
            return
        ids = page_section_ids(instance)
    except Exception:
        return
    if not ids:
        return

    def run():
        try:
            forget(ids)
        except Exception:
            pass
    # After the commit (the page and its revisions are gone by then); never on a rollback.
    transaction.on_commit(run)
