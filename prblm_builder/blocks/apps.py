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
