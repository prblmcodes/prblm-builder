from django.apps import AppConfig


class PrblmBuilderConfig(AppConfig):
    name = "prblm_builder"
    label = "prblm_builder"
    verbose_name = "Page builder"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Auto-attach the Layout tab + save wiring to every builder-enabled page
        # model, so host sites don't wire each model by hand.
        from . import checks, integration  # noqa: F401  (checks registers on import)
        integration.autoenable()
        # Forget the demo-content records of a deleted page's sections.
        from django.db.models.signals import pre_delete

        from . import cleanup
        pre_delete.connect(cleanup.page_deleted, dispatch_uid="prblm_builder_page_deleted")
