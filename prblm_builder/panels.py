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
            ctx["admin_tweaks"] = cfg.admin_tweaks()
            from . import registry
            ctx["field_name"] = registry.target_field_name(type(self.instance)) or ""
            # Title used by "Save draft now" when the editor hasn't typed one yet.
            from wagtail.models import Page
            ctx["placeholder_title"] = f"Untitled page {Page.objects.count() + 1}"
            # The form came back with errors (e.g. empty title): hand the submitted
            # arrangement back to the canvas so it isn't lost.
            form = getattr(self, "form", None)
            data = getattr(form, "data", None) if form is not None and form.is_bound else None
            if data and data.get("_pb_layout"):
                ctx["restore"] = {"layout": data.get("_pb_layout"),
                                  "initial": data.get("_pb_initial") or "[]"}
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
                # The parent page tells which Site the new page belongs to (per-site previews).
                request = getattr(self, "request", None)
                match = getattr(request, "resolver_match", None)
                parent = (match.kwargs.get("parent_page_id") if match else None)
                if parent:
                    ctx["builder_url"] += f"&parent={int(parent)}"
            return ctx
