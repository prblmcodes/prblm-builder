"""Helpers for your own blocks.

``Meta.builder_settings = ["background", "anchor_id"]`` on a StructBlock makes those
fields editable from the ⚙ button on the section in the Layout tab. Add
:class:`BuilderSettingsMixin` to also tuck them into Wagtail's collapsed "settings" area
in the Content tab::

    from prblm_builder.mixins import BuilderSettingsMixin

    class PromoBlock(BuilderSettingsMixin, blocks.StructBlock):
        title = blocks.CharBlock()
        background = blocks.ChoiceBlock(choices=[...])

        class Meta:
            builder_settings = ["background"]
"""
from wagtail.blocks.struct_block import BlockGroup


def builder_setting_names(block):
    """The fields of ``block`` listed in ``Meta.builder_settings`` that actually exist."""
    names = getattr(getattr(block, "meta", None), "builder_settings", None) or []
    children = getattr(block, "child_blocks", {})
    return [n for n in names if n in children]


class BuilderSettingsMixin:
    """Put ``Meta.builder_settings`` fields in Wagtail's collapsed settings area (Wagtail
    8.1 ``form_layout``), unless the block sets its own ``form_layout``."""

    def get_form_layout(self):
        if self.meta.form_layout is None:
            names = builder_setting_names(self)
            if names:
                content = [n for n in self.child_blocks if n not in names]
                return BlockGroup(content, settings=names)
        return super().get_form_layout()
