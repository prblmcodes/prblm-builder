"""Admin wiring for the built-in blocks. Theme, Headers and Footers live in the plugin's
"Page builder" sidebar section instead of Wagtail's Settings / Snippets menus."""
from django.urls import reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.contrib.settings.registry import SettingMenuItem, registry
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from prblm_builder.wagtail_hooks import MENU_HOOK

from . import chrome
from .models import SiteFooter, SiteHeader, ThemeSettings

PREFIX = "prblm-builder-"

# Registered as Wagtail site settings (gives the edit view, per-site values and
# permissions); the Settings-menu entry this adds is removed below.
registry.register(ThemeSettings, icon="sliders", name=PREFIX + "theme")


class SiteHeaderViewSet(SnippetViewSet):
    model = SiteHeader
    icon = "arrow-up"
    menu_label = "Headers"
    add_to_admin_menu = False
    list_display = ["name", "is_default"]


class SiteFooterViewSet(SnippetViewSet):
    model = SiteFooter
    icon = "arrow-down"
    menu_label = "Footers"
    add_to_admin_menu = False
    list_display = ["name", "is_default"]


register_snippet(SiteHeaderViewSet)
register_snippet(SiteFooterViewSet)


@hooks.register("construct_settings_menu")
def hide_from_settings_menu(request, menu_items):
    menu_items[:] = [i for i in menu_items if not i.name.startswith(PREFIX)]


@hooks.register(MENU_HOOK)
def theme_menu_item():
    return SettingMenuItem(ThemeSettings, icon="sliders", name=PREFIX + "theme-page", order=200)


def _snippet_list_url(model):
    return reverse(f"wagtailsnippets_{model._meta.app_label}_{model._meta.model_name}:list")


@hooks.register(MENU_HOOK)
def headers_menu_item():
    return MenuItem("Headers", _snippet_list_url(SiteHeader), name=PREFIX + "headers",
                    icon_name="arrow-up", order=300)


@hooks.register(MENU_HOOK)
def footers_menu_item():
    return MenuItem("Footers", _snippet_list_url(SiteFooter), name=PREFIX + "footers",
                    icon_name="arrow-down", order=310)


@hooks.register("prblm_builder_chrome_for_page")
def builder_page_chrome(kind, request, page, model):
    """A Builder page decides its own header/footer (see chrome.for_page)."""
    return chrome.for_page(kind, request, page, model)


@hooks.register("prblm_builder_chrome")
def site_default_chrome(kind, request, page):
    """Other pages: the site-default header/footer on the canvas."""
    return chrome.render(kind, request, page)


@hooks.register("prblm_builder_page_options")
def builder_page_options(request, page, model):
    """The Layout sidebar's "Page" tab for Builder pages: Header and Footer dropdowns."""
    from .models import BuilderPage
    cls = type(page) if page is not None else model
    if cls is None or not isinstance(cls, type):
        return []
    if issubclass(cls, BuilderPage):
        return [chrome.page_option("header", page), chrome.page_option("footer", page)]
    # The site's own page types: information only (their template decides).
    return [info for info in (chrome.page_info("header"), chrome.page_info("footer")) if info]


@hooks.register("prblm_builder_swatch_colors")
def theme_swatch_colors(request):
    """The ⚙ background swatches show this site's Theme colours."""
    from . import theme
    values = theme.values_for(request)
    return {
        "light": values["background_color"],
        "muted": values["muted_background_color"],
        "dark": values["dark_background_color"],
        "brand": values["brand_color"],
    }
