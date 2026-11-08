"""Django system checks — warn about settings that no longer do anything."""
from django.conf import settings
from django.core.checks import Warning, register

REMOVED_SETTINGS = {
    "PRBLM_BUILDER_SEED_NEW_BLOCKS": (
        "Removed in prblm-builder 0.3.0: new blocks always start with content, and the "
        "canvas marks sections that haven't been edited yet. Delete this setting."
    ),
}


@register()
def removed_settings(app_configs, **kwargs):
    return [
        Warning(f"{name} is no longer used.", hint=hint, id="prblm_builder.W001")
        for name, hint in REMOVED_SETTINGS.items()
        if hasattr(settings, name)
    ]
