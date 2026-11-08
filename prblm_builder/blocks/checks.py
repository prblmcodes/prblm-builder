"""System checks for the optional built-in blocks app."""
from django.apps import apps
from django.core.checks import Error, register


@register()
def requirements(app_configs, **kwargs):
    errors = []
    if not apps.is_installed("wagtail.contrib.settings"):
        errors.append(Error(
            "prblm_builder.blocks needs 'wagtail.contrib.settings' in INSTALLED_APPS.",
            hint="It stores the Theme and the site-wide Header & footer.",
            id="prblm_builder_blocks.E001",
        ))
    if not apps.is_installed("prblm_builder"):
        errors.append(Error(
            "prblm_builder.blocks needs 'prblm_builder' in INSTALLED_APPS.",
            id="prblm_builder_blocks.E002",
        ))
    return errors
