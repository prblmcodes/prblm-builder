from wagtail import blocks


class NoteBlock(blocks.CharBlock):
    """A site's own block, added to the Builder page via PRBLM_BUILDER_PAGE_EXTRA_BLOCKS."""

    class Meta:
        template = "testapp/blocks/heading.html"
        group = "Site extras"


from prblm_builder.mixins import BuilderSettingsMixin  # noqa: E402


class SettingsBannerBlock(BuilderSettingsMixin, blocks.StructBlock):
    """A site's own block that opts into the ⚙ settings popover."""

    title = blocks.CharBlock(default="Banner title")
    tone = blocks.ChoiceBlock(choices=[("calm", "Calm"), ("loud", "Loud")], default="calm")
    show_border = blocks.BooleanBlock(required=False)

    class Meta:
        template = "testapp/blocks/banner.html"
        builder_settings = ["tone", "show_border", "not_a_field"]
