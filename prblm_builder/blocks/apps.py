from django.apps import AppConfig


class PrblmBuilderBlocksConfig(AppConfig):
    name = "prblm_builder.blocks"
    label = "prblm_builder_blocks"
    verbose_name = "Page builder blocks"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from prblm_builder import settings as cfg

        from . import checks  # noqa: F401  (registers system checks)
        from .models import BuilderPage

        # Read once at startup: hide the page type from "Add page" if switched off.
        BuilderPage.is_creatable = cfg.page_type_enabled()
        allow_builder_page_under(cfg.page_parents())


BUILDER_PAGE = "prblm_builder_blocks.BuilderPage"


def allow_builder_page_under(labels):
    """PRBLM_BUILDER_PAGE_PARENTS: let editors add Builder pages under these page types,
    even when the type limits its children with ``subpage_types``. Unknown names are
    reported by a system check, never a crash."""
    from django.apps import apps
    for label in labels:
        try:
            model = apps.get_model(label)
        except (LookupError, ValueError):
            continue
        allowed = getattr(model, "subpage_types", None)
        if allowed is None:
            continue  # no restriction: Builder pages are already allowed
        resolved = [a if isinstance(a, str) else a._meta.label for a in allowed]
        if any(a.lower() == BUILDER_PAGE.lower() for a in resolved):
            continue
        model.subpage_types = list(allowed) + [BUILDER_PAGE]
        # Wagtail caches the resolved list on each class (None = "work it out again").
        model._clean_subpage_models = None
