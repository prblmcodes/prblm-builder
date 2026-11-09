from django.urls import include, path, reverse
from wagtail import hooks
from wagtail.admin.menu import Menu, MenuItem, SubmenuMenuItem

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


# The plugin's own "Page builder" section in the admin sidebar. Its sub-items come from
# the ``register_prblm_builder_menu_item`` hook, so the optional blocks app can add its
# Theme / Header & footer pages. The section hides itself when it has no items.
MENU_HOOK = "register_prblm_builder_menu_item"


@hooks.register("register_admin_menu_item")
def register_page_builder_menu():
    return SubmenuMenuItem(
        "Page builder",
        Menu(register_hook_name=MENU_HOOK),
        name="prblm-builder",
        icon_name="grip",
        order=850,
    )


class BlockLibraryMenuItem(MenuItem):
    """Shown only while the Block library is enabled. Checked per request: Wagtail
    builds its menus once, so a ``return None`` in the hook would be cached forever."""

    def is_shown(self, request):
        from . import settings as cfg
        return cfg.demo_enabled() and super().is_shown(request)


@hooks.register(MENU_HOOK)
def register_block_library_menu_item():
    """The Block library — every block with a live demo preview (admin-only)."""
    return BlockLibraryMenuItem(
        "Block library",
        reverse("prblm_builder:demo"),
        name="prblm-builder-library",
        icon_name="grip",
        order=100,
    )


# Two-column block forms (PRBLM_BUILDER_FORM_COLUMNS): loaded on every admin page — the
# script only acts on block forms (built-in ones, or all with "all").
@hooks.register("insert_global_admin_css")
def form_columns_css():
    from django.templatetags.static import static
    from django.utils.html import format_html

    from . import settings as cfg
    if not cfg.form_columns():
        return ""
    return format_html('<link rel="stylesheet" href="{}">', static("prblm_builder/form-columns.css"))


@hooks.register("insert_global_admin_js")
def form_columns_js():
    from django.templatetags.static import static
    from django.utils.html import format_html

    from . import settings as cfg
    mode = cfg.form_columns()
    if not mode:
        return ""
    return format_html('<script src="{}" data-mode="{}" defer></script>',
                       static("prblm_builder/form-columns.js"), mode)
