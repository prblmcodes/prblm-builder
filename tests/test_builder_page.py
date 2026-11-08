"""Phase 6: the ready-made Builder page type."""
import json

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.models import Page, Site

from prblm_builder import registry
from prblm_builder.blocks import builder_blocks
from prblm_builder.blocks.models import BuilderPage
from prblm_builder.layout import reconcile
from tests.test_site_chrome import set_chrome

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=STORAGES)
class BuilderPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser("bp-admin", "bp@example.com", "pw")
        cls.home = Page.objects.get(depth=2)
        _f, sb = registry.stream_block_for(BuilderPage)
        body = reconcile(sb, [], [{"type": "hero", "id": "h1", "new": True},
                                  {"type": "faq", "id": "f1", "new": True}], [])
        cls.page = cls.home.add_child(instance=BuilderPage(
            title="Landing", slug="landing", body=json.dumps(body), search_description="Desc"))
        cls.page.save_revision().publish()

    def setUp(self):
        self.client.force_login(self.admin)

    def test_has_all_builtin_blocks_and_layout_tab(self):
        _f, sb = registry.stream_block_for(BuilderPage)
        self.assertEqual(list(sb.child_blocks), [n for n, _ in builder_blocks()])
        self.assertIn(BuilderPage, registry.enabled_page_models())
        headings = [getattr(c, "heading", "") for c in BuilderPage.get_edit_handler().children]
        self.assertIn("Layout", headings)

    def test_creatable_by_default(self):
        self.assertTrue(BuilderPage.is_creatable)
        self.assertIn(BuilderPage, self.home.specific_class.creatable_subpage_models())

    def test_renders_standalone_page(self):
        r = self.client.get(self.page.url)
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertTrue(html.lstrip().startswith("<!doctype html>"))
        self.assertIn("<title>Landing</title>", html)
        self.assertIn('content="Desc"', html)
        self.assertIn("Your main headline", html)
        self.assertIn("Frequently asked questions", html)
        self.assertEqual(html.count("blocks.css"), 1)

    def test_page_shows_site_chrome(self):
        set_chrome()
        html = self.client.get(self.page.url).content.decode()
        self.assertIn("Acme Header", html)
        self.assertIn("Acme Footer text", html)

    def test_add_page_form(self):
        url = reverse("wagtailadmin_pages:add", args=["prblm_builder_blocks", "builderpage", self.home.pk])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "layout-new")          # Layout tab on a new page

    @override_settings(PRBLM_BUILDER_PAGE_TYPE=False)
    def test_hide_setting(self):
        apps.get_app_config("prblm_builder_blocks").ready()
        try:
            self.assertFalse(BuilderPage.is_creatable)
            self.assertNotIn(BuilderPage, self.home.specific_class.creatable_subpage_models())
            self.assertEqual(self.client.get(self.page.url).status_code, 200)   # still served
        finally:
            BuilderPage.is_creatable = True
