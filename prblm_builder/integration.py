"""Auto-attach the Layout tab + save wiring to every builder-enabled page model.

Called from the app's ``ready()``. For each page model with a buildable StreamField
that doesn't already have a Layout tab, this inserts a **Layout** tab as the first tab of its editor
and composes :class:`~prblm_builder.forms.LayoutBuilderForm` onto its base form, so a
host site gets the builder on all its block-based page types with no per-model code.

Defensive by design: any failure for a model just means that model doesn't get the
tab — never a broken admin.
"""
from .forms import LayoutBuilderForm
from .panels import LayoutBuilderPanel


def _has_layout(handler):
    try:
        for tab in getattr(handler, "children", []):
            for panel in getattr(tab, "children", []):
                if isinstance(panel, LayoutBuilderPanel):
                    return True
    except Exception:
        pass
    return False


def enable_model(model):
    from wagtail.admin.forms import WagtailAdminPageForm
    from wagtail.admin.panels import ObjectList, TabbedInterface

    existing = getattr(model, "edit_handler", None)
    if existing is not None and _has_layout(existing):
        return
    # A model may add panels to the Layout tab (``builder_layout_panels``) — fields that the
    # builder's "Page" sidebar tab edits (e.g. the Builder page's header/footer). They're
    # rendered hidden; the sidebar writes into them so they save like any other field.
    extra = list(getattr(model, "builder_layout_panels", None) or [])
    layout = ObjectList([LayoutBuilderPanel(), *extra], heading="Layout")
    if existing is not None and getattr(existing, "children", None):
        children = list(existing.children)
        children.insert(0, layout)  # first tab: Wagtail opens it by default
        model.edit_handler = TabbedInterface(children)
    else:
        model.edit_handler = TabbedInterface([
            layout,
            ObjectList(model.content_panels, heading="Content"),
            ObjectList(model.promote_panels, heading="Promote"),
            ObjectList(model.settings_panels, heading="Settings"),
        ])
    # Compose the save wiring onto whatever base form the model already uses, so a
    # model with its own base_form_class (e.g. a form page) keeps it.
    orig = getattr(model, "base_form_class", None) or WagtailAdminPageForm
    if not issubclass(orig, LayoutBuilderForm):
        model.base_form_class = type(
            f"Layout{model.__name__}Form", (LayoutBuilderForm, orig), {})
    # Drop any cached edit handler so the new one takes effect.
    for attr in ("_edit_handler", "get_edit_handler"):
        try:
            getattr(model, attr).cache_clear()
        except Exception:
            pass


def autoenable():
    from . import registry
    try:
        models = registry.enabled_page_models()
    except Exception:
        return
    for model in models:
        try:
            enable_model(model)
        except Exception:
            continue
