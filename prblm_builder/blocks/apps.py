from django.apps import AppConfig


class PrblmBuilderBlocksConfig(AppConfig):
    name = "prblm_builder.blocks"
    label = "prblm_builder_blocks"
    verbose_name = "Page builder blocks"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import checks  # noqa: F401  (registers system checks)
