"""Turn a Layout-tab *arrangement* into a page's StreamField raw blocks.

The Layout tab (and the standalone builder) describe only the desired **order and
membership** of top-level sections. Block **content** is edited in Wagtail's normal
editor. This module reconciles the two so one Save keeps both:

    new_raw = reconcile(stream_block, current_raw, layout, initial_ids)

- ``current_raw``  the content source of truth — the submitted/stored field's
  ``raw_data`` (a list of ``{"type", "value", "id"}`` dicts).
- ``layout``       the desired sections in order: ``[{"type", "id", "new"?, "copy_from"?}]``.
- ``initial_ids``  the ids the builder knew when it loaded. This is what lets us tell a
  section the editor *removed in the Layout tab* (a known id now missing → drop it) from
  one *added in the normal editor* that the Layout tab never saw (unknown id → keep it).
  Without it we'd either resurrect deleted sections or silently drop new ones.

Existing sections keep their stored content exactly; brand-new ones are seeded with
realistic demo content (so a built-and-published page is never blank); a duplicate copies its source's content.
"""
import uuid

from . import previews


def new_block_value(block, name):
    """Stored (prep) value for a block just added in the Layout tab: demo content (a real
    instance used on the site, else the block's defaults / synthesised content)."""
    return block.get_prep_value(previews.demo_value(block, name))


class SettingsError(ValueError):
    """Section settings from the Layout tab that don't validate (e.g. a bad anchor ID)."""

    def __init__(self, messages):
        super().__init__("; ".join(messages))
        self.messages = messages


def apply_settings(block, item, settings, errors, label):
    """Write Layout-tab section settings (only the changed ones) into a raw section
    ``item`` — validated by each field's own block."""
    from django.core.exceptions import ValidationError

    from .mixins import builder_setting_names
    allowed = set(builder_setting_names(block))
    if not settings or not allowed or not isinstance(item.get("value"), dict):
        return item
    item = dict(item)
    value = dict(item["value"])
    for name, raw in settings.items():
        if name not in allowed:
            continue
        child = block.child_blocks[name]
        try:
            cleaned = child.clean(child.to_python(raw))
        except ValidationError as exc:
            errors.append(f"{label} — {child.label or name}: {' '.join(exc.messages)}")
            continue
        value[name] = child.get_prep_value(cleaned)
    item["value"] = value
    return item


def reconcile(stream_block, current_raw, layout, initial_ids=None):
    raw_by_id = {str(d.get("id")): d for d in current_raw if d.get("id")}
    initial = {str(i) for i in (initial_ids or [])}
    result, used, errors = [], set(), []

    def add(item, block, layout_item, t):
        settings = layout_item.get("settings")
        if settings:
            from .registry import block_label
            item = apply_settings(block, item, settings, errors, block_label(t, block))
        result.append(item)

    for item in layout:
        t = item.get("type")
        block = stream_block.child_blocks.get(t)
        if block is None:
            continue
        sid = str(item.get("id") or "") or str(uuid.uuid4())

        # A duplicate copies its source's stored content (new id).
        copy_from = item.get("copy_from")
        if copy_from and str(copy_from) in raw_by_id:
            src = dict(raw_by_id[str(copy_from)])
            src["id"] = sid
            add(src, block, item, t)
            continue

        # An existing section still present in the content → keep it verbatim.
        existing = raw_by_id.get(sid)
        if existing and existing.get("type") == t:
            add(existing, block, item, t)
            used.add(sid)
            continue

        # Otherwise it's new (added in the builder, or a duplicate of an unsaved
        # section) → seed with demo content. A *known* id that has vanished from the
        # content was deleted elsewhere, so it falls through here only when flagged
        # new; an unflagged vanished id is simply dropped.
        if item.get("new") or copy_from:
            add({"type": t, "value": new_block_value(block, t), "id": sid}, block, item, t)

    # Sections added in the normal editor that the Layout tab never knew about are
    # kept (appended after the arranged ones). Ones the Layout tab *did* know and
    # dropped stay dropped.
    for d in current_raw:
        did = str(d.get("id") or "")
        if did and did not in used and did not in initial:
            result.append(d)

    if errors:
        raise SettingsError(errors)
    return result
