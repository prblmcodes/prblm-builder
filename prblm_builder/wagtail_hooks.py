from django.urls import include, path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from . import views

app_name = "prblm_builder"
# Layout editing lives in the page editor's "Layout" tab (see panels.LayoutBuilderPanel),
# so there's no standalone-builder menu item or explorer/header "Edit layout" button.
# The ``builder`` view stays — the Layout tab embeds it (``?embed=1``).
urlpatterns = [
    path("layout-new/", views.builder_new, name="builder_new"),
    path("demo/", views.demo, name="demo"),
    path("preview/", views.preview, name="preview"),
    path("page/<int:page_id>/", views.builder, name="builder"),
    path("page/<int:page_id>/save/", views.save, name="save"),
    path("page/<int:page_id>/preview/", views.page_preview, name="page_preview"),
]


@hooks.register("register_admin_urls")
def register_builder_urls():
    return [path("page-builder/", include((urlpatterns, app_name), namespace=app_name))]


@hooks.register("register_settings_menu_item")
def register_demo_menu_item():
    """A discoverable 'Block library' entry in the admin Settings menu (admin-only)."""
    from . import settings as cfg
    if not cfg.demo_enabled():
        return None
    return MenuItem(
        "Block library",
        reverse("prblm_builder:demo"),
        name="prblm-builder-demo",
        icon_name="grip",
        order=950,
    )
