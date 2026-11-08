"""Admin wiring for the built-in blocks: Theme (and later Header & footer) live in the
plugin's "Page builder" sidebar section instead of Wagtail's Settings menu."""
from wagtail import hooks
from wagtail.contrib.settings.registry import SettingMenuItem, registry

from prblm_builder.wagtail_hooks import MENU_HOOK

from .models import ThemeSettings

PREFIX = "prblm-builder-"

# Registered as Wagtail site settings (gives the edit view, per-site values and
# permissions); the Settings-menu entry this adds is removed below.
registry.register(ThemeSettings, icon="sliders", name=PREFIX + "theme")


@hooks.register("construct_settings_menu")
def hide_from_settings_menu(request, menu_items):
    menu_items[:] = [i for i in menu_items if not i.name.startswith(PREFIX)]


@hooks.register(MENU_HOOK)
def theme_menu_item():
    return SettingMenuItem(ThemeSettings, icon="sliders", name=PREFIX + "theme-page", order=200)
