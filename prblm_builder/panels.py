"""A Wagtail panel that embeds the builder in a page editor tab.

Add it to a page model's ``edit_handler`` to get a "Layout" tab:

    from wagtail.admin.panels import ObjectList, TabbedInterface
    from prblm_builder.panels import LayoutBuilderPanel

    edit_handler = TabbedInterface([
        ObjectList(content_panels, heading="Content"),
        ObjectList([LayoutBuilderPanel()], heading="Layout"),
        …
    ])

Also set the model's ``base_form_class = prblm_builder.forms.LayoutBuilderForm`` so the
arrangement rides along with Wagtail's own Save draft / Publish — the Layout tab has no
Save of its own. The Content tab stays the native content editor.
"""
from django.urls import reverse
from wagtail.admin.panels import Panel


class LayoutBuilderPanel(Panel):
    class BoundPanel(Panel.BoundPanel):
        template_name = "prblm_builder/layout_panel.html"

        def get_context_data(self, parent_context=None):
            from . import settings as cfg
            ctx = super().get_context_data(parent_context)
            ctx["demo_url"] = reverse("prblm_builder:demo") if cfg.demo_enabled() else ""
            pk = getattr(self.instance, "pk", None)
            if pk:
                ctx["builder_url"] = reverse("prblm_builder:builder", args=[pk]) + "?embed=1"
            else:
                # Brand-new, unsaved page — scope the builder to the model so you can
                # lay it out before the first save; the sections save with the page.
                model = type(self.instance)
                label = f"{model._meta.app_label}.{model.__name__}"
                ctx["builder_url"] = (
                    reverse("prblm_builder:builder_new") + f"?model={label}&embed=1"
                )
            return ctx
