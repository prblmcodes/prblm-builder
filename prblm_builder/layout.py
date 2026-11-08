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
realistic demo content (or start empty with ``PRBLM_BUILDER_SEED_NEW_BLOCKS = False``);
a duplicate copies its source's content.
"""
import uuid

from . import previews
from . import settings as cfg


def empty_value(block):
    """A block's own defaults, with unset text fields as ``""`` rather than ``None`` —
    what Wagtail's editor saves for a blank field (``None`` would render as "None")."""
    from wagtail import blocks

    if isinstance(block, blocks.StructBlock):
        default = block.get_default()
        out = {}
        for name, child in block.child_blocks.items():
            value = default.get(name)
            # Recurse into nested structs (their own text fields may be None too).
            if value is None or isinstance(child, blocks.StructBlock):
                value = empty_value(child)
            out[name] = value
        return block.normalize(out)
    default = block.get_default()
    if default is None and isinstance(block, blocks.FieldBlock):
        try:
            return block.field.to_python("")
        except Exception:
            return None
    return default


def new_block_value(block, name):
    """Stored (prep) value for a block just added in the Layout tab: demo content, or
    the block's own empty defaults when ``PRBLM_BUILDER_SEED_NEW_BLOCKS`` is off."""
    if cfg.seed_new_blocks():
        return block.get_prep_value(previews.demo_value(block, name))
    return block.get_prep_value(empty_value(block))


def reconcile(stream_block, current_raw, layout, initial_ids=None):
    raw_by_id = {str(d.get("id")): d for d in current_raw if d.get("id")}
    initial = {str(i) for i in (initial_ids or [])}
    result, used = [], set()

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
            result.append(src)
            continue

        # An existing section still present in the content → keep it verbatim.
        existing = raw_by_id.get(sid)
        if existing and existing.get("type") == t:
            result.append(existing)
            used.add(sid)
            continue

        # Otherwise it's new (added in the builder, or a duplicate of an unsaved
        # section) → seed with demo content. A *known* id that has vanished from the
        # content was deleted elsewhere, so it falls through here only when flagged
        # new; an unflagged vanished id is simply dropped.
        if item.get("new") or copy_from:
            result.append({"type": t, "value": new_block_value(block, t), "id": sid})

    # Sections added in the normal editor that the Layout tab never knew about are
    # kept (appended after the arranged ones). Ones the Layout tab *did* know and
    # dropped stay dropped.
    for d in current_raw:
        did = str(d.get("id") or "")
        if did and did not in used and did not in initial:
            result.append(d)

    return result
