"""System checks for the optional built-in blocks app."""
from django.apps import apps
from django.core.checks import Error, Warning, register


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


@register()
def page_parents(app_configs, **kwargs):
    from django.conf import settings
    from wagtail.models import Page
    warnings = []
    for label in getattr(settings, "PRBLM_BUILDER_PAGE_PARENTS", []) or []:
        try:
            model = apps.get_model(label)
        except (LookupError, ValueError):
            model = None
        if model is None or not issubclass(model, Page):
            warnings.append(Warning(
                f"PRBLM_BUILDER_PAGE_PARENTS: {label!r} is not a page type.",
                hint='Use "app_label.ModelName", e.g. "home.HomePage".',
                id="prblm_builder_blocks.W001"))
    return warnings
