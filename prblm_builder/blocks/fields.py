"""The Builder page's body field: built-in blocks + the site's extra blocks.

``PRBLM_BUILDER_PAGE_EXTRA_BLOCKS`` adds a site's own blocks to the Builder page at
runtime. The field describes itself to migrations as *built-ins only*, so a site's extra
blocks never make Django want a new migration inside the installed plugin. (StreamField
data is JSON; the migration's block list is informational.)
"""
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from wagtail.blocks import Block
from wagtail.fields import StreamField


def _block(path, name):
    try:
        obj = import_string(path)
    except ImportError as exc:
        raise ImproperlyConfigured(
            f"PRBLM_BUILDER_PAGE_EXTRA_BLOCKS: can't import {path!r} for block {name!r} ({exc}).")
    if isinstance(obj, type) and issubclass(obj, Block):
        return obj()
    if isinstance(obj, Block):
        return obj
    raise ImproperlyConfigured(
        f"PRBLM_BUILDER_PAGE_EXTRA_BLOCKS: {path!r} is not a Wagtail block class or instance.")


def extra_blocks(setting):
    """``[(name, block)]`` from the setting. It may be a list of ``("name", "dotted.Block")``
    pairs, or the dotted path of a function returning ``[(name, block), …]``."""
    if not setting:
        return []
    if isinstance(setting, str):
        try:
            return list(import_string(setting)())
        except ImportError as exc:
            raise ImproperlyConfigured(f"PRBLM_BUILDER_PAGE_EXTRA_BLOCKS: can't import {setting!r} ({exc}).")
    out = []
    for item in setting:
        try:
            name, path = item
        except (TypeError, ValueError):
            raise ImproperlyConfigured(
                "PRBLM_BUILDER_PAGE_EXTRA_BLOCKS entries must be (\"name\", \"dotted.path.Block\") pairs; "
                f"got {item!r}.")
        out.append((name, _block(path, name) if isinstance(path, str) else path))
    return out


def body_blocks(builtins, setting):
    """Built-ins + extras; a name used twice is a configuration error."""
    extras = extra_blocks(setting)
    taken = {n for n, _ in builtins}
    clash = sorted(n for n, _ in extras if n in taken)
    if clash:
        raise ImproperlyConfigured(
            f"PRBLM_BUILDER_PAGE_EXTRA_BLOCKS: {clash} clash with built-in block names. "
            "Give your blocks different names.")
    return list(builtins) + extras


class BuilderBodyField(StreamField):
    """A StreamField whose migration description is fixed to ``migration_blocks``."""

    def __init__(self, block_types, *args, migration_blocks=None, **kwargs):
        self._migration_blocks = migration_blocks
        super().__init__(block_types, *args, **kwargs)

    def deconstruct(self):
        name, _path, args, kwargs = super().deconstruct()
        if self._migration_blocks is not None:
            plain = StreamField(self._migration_blocks, blank=self.blank)
            _n, _p, args, kwargs = plain.deconstruct()
        return name, "wagtail.fields.StreamField", args, kwargs
