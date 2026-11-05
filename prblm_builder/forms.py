"""Page form that applies the Layout tab's arrangement on Wagtail's own Save.

Set it as a builder-enabled page model's ``base_form_class`` and the Layout tab's
drag / reorder / add / delete ride along with the editor's Save draft / Publish —
there's no separate save step in the tab.

The Layout tab writes two hidden inputs into the page edit form:

- ``_pb_layout``   the desired sections, in order: ``[{type, id, new?, copy_from?}]``
- ``_pb_initial``  the ids present when the tab loaded (see ``layout.reconcile``)

On clean we rebuild the target StreamField from the submitted content (the Content
tab is the source of truth for each block's *value*) in the Layout tab's order.
If the hidden fields are absent (the editor never opened the Layout tab), nothing
changes — the native body is saved exactly as submitted.
"""
import json

from wagtail.admin.forms import WagtailAdminPageForm

from . import registry
from .layout import reconcile


class LayoutBuilderForm(WagtailAdminPageForm):
    def clean(self):
        cleaned = super().clean()
        raw = self.data.get("_pb_layout")
        if not raw:
            return cleaned
        field_name, stream_block = registry.stream_block_for(type(self.instance))
        if not stream_block or field_name not in cleaned:
            return cleaned
        try:
            layout = json.loads(raw)
            initial = json.loads(self.data.get("_pb_initial") or "[]")
        except (ValueError, TypeError):
            return cleaned
        if not isinstance(layout, list):
            return cleaned
        current_raw = list(cleaned[field_name].raw_data)
        new_raw = reconcile(stream_block, current_raw, layout, initial)
        cleaned[field_name] = stream_block.to_python(new_raw)
        return cleaned
