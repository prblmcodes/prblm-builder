from wagtail import blocks


class NoteBlock(blocks.CharBlock):
    """A site's own block, added to the Builder page via PRBLM_BUILDER_PAGE_EXTRA_BLOCKS."""

    class Meta:
        template = "testapp/blocks/heading.html"
        group = "Site extras"
