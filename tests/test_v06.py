"""v0.6: Layout tab first, tabs in sync, two-column forms, examples."""
import json
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.models import Page

from prblm_builder import registry
from tests.testapp.models import StandardPage

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=STORAGES)
class LayoutFirstTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("lf", "lf@example.com", "pw"))

    def test_layout_is_the_first_tab_for_every_builder_model(self):
        for model in registry.enabled_page_models():
            with self.subTest(model=model.__name__):
                headings = [getattr(c, "heading", "") for c in model.get_edit_handler().children]
                self.assertEqual(headings[0], "Layout")
                self.assertEqual(headings[1], "Content")

    def test_edit_and_create_views_open_layout(self):
        page = Page.objects.get(depth=2).add_child(
            instance=StandardPage(title="LF", slug="lf-" + uuid.uuid4().hex[:5]))
        for url in (reverse("wagtailadmin_pages:edit", args=[page.id]),
                    reverse("wagtailadmin_pages:add", args=["testapp", "standardpage", page.get_parent().id])):
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                # Wagtail opens the first tab; Layout must come before Content.
                self.assertLess(html.index('id="tab-label-layout"'), html.index('id="tab-label-content"'))
