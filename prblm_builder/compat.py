"""Imports that differ between the Wagtail versions the plugin supports (7.0 – 8.x).

Keep every version-dependent import here, so a new Wagtail release needs changes in
one place only.
"""
import wagtail

WAGTAIL_VERSION = tuple(wagtail.VERSION[:2])

try:  # Wagtail 8.1+: collapsed "settings" area in block forms (Meta.form_layout)
    from wagtail.blocks.struct_block import BlockGroup
except ImportError:  # pragma: no cover - older Wagtail
    BlockGroup = None

HAS_FORM_LAYOUT = BlockGroup is not None

try:  # newer Wagtail
    from wagtail.admin.telepath import JSContext, register
except ImportError:  # pragma: no cover - Wagtail 7.0
    from wagtail.telepath import JSContext, register

__all__ = ["WAGTAIL_VERSION", "BlockGroup", "HAS_FORM_LAYOUT", "JSContext", "register"]
