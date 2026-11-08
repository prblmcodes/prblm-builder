"""Optional built-in section blocks for prblm-builder.

Enable by adding ``"prblm_builder.blocks"`` (and ``"wagtail.contrib.settings"``) to
``INSTALLED_APPS``. Use the blocks in a page model with :func:`builder_blocks`::

    from prblm_builder.blocks import builder_blocks

    class LandingPage(Page):
        body = StreamField(builder_blocks() + [("my_block", MyBlock())], blank=True)

Kept import-light on purpose: block classes are imported inside the function, so this
package can be listed in ``INSTALLED_APPS`` before Django's app registry is ready.
"""


def builder_blocks(exclude=(), only=None):
    """The built-in blocks as ``[(name, block), …]`` for a StreamField.

    ``exclude`` drops blocks by name (e.g. to avoid clashing with your own ``hero``);
    ``only`` keeps just the named ones. Both are lists of names.
    """
    from .sections import all_blocks

    unknown = set(exclude) | set(only or ())
    known = {name for name, _ in all_blocks()}
    if unknown - known:
        raise ValueError(
            "builder_blocks(): unknown block name(s) %s. Available: %s"
            % (sorted(unknown - known), ", ".join(sorted(known))))
    return [(name, block) for name, block in all_blocks()
            if name not in exclude and (only is None or name in only)]
