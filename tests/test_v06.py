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


@override_settings(STORAGES=STORAGES)
class TabSyncWiringTests(TestCase):
    """The sync itself runs in the browser (checked with Playwright); these guard the wiring."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("ts", "ts@example.com", "pw"))
        self.page = Page.objects.get(depth=2).add_child(
            instance=StandardPage(title="TS", slug="ts-" + uuid.uuid4().hex[:5]))

    def test_panel_and_builder_know_the_stream_field(self):
        html = self.client.get(reverse("wagtailadmin_pages:edit", args=[self.page.id])).content.decode()
        self.assertIn('class="prblm-layout-panel" style="width:100%" data-field-name="body"', html)
        self.assertIn("w-autosave:success", html)                 # waits for Wagtail's auto-save
        self.assertIn('url.hash = "tab-content"', html)           # reloads onto the Content tab
        r = self.client.get(reverse("prblm_builder:builder", args=[self.page.id]) + "?embed=1")
        self.assertContains(r, 'data-field-name="body"')

    def test_builder_js_only_writes_layout_fields_after_a_change(self):
        from django.contrib.staticfiles import finders
        js = open(finders.find("prblm_builder/builder.js")).read()
        self.assertIn("if (!dirtied) return;", js)
        for needle in ("prblm-builder:structure", "window.prblmBuilder", "writeContentInput"):
            self.assertIn(needle, js)


@override_settings(STORAGES=STORAGES)
class FormColumnsTests(TestCase):
    """The layout itself runs in the browser (checked with Playwright); these guard the setup."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("fc", "fc@example.com", "pw"))

    def admin_html(self):
        return self.client.get(reverse("wagtailadmin_home")).content.decode()

    def test_loaded_for_builtin_blocks_by_default(self):
        html = self.admin_html()
        self.assertIn("prblm_builder/form-columns.js", html)
        self.assertIn('data-mode="builtin"', html)
        self.assertIn("prblm_builder/form-columns.css", html)

    @override_settings(PRBLM_BUILDER_FORM_COLUMNS="all")
    def test_all_mode(self):
        self.assertIn('data-mode="all"', self.admin_html())

    @override_settings(PRBLM_BUILDER_FORM_COLUMNS=False)
    def test_off(self):
        html = self.admin_html()
        self.assertNotIn("form-columns.js", html)
        self.assertNotIn("form-columns.css", html)

    def test_builtin_block_forms_are_marked(self):
        from prblm_builder.blocks.sections.base import LinkBlock
        from prblm_builder.blocks.sections.heroes import HeroBlock
        self.assertIn("pbk-form", HeroBlock().meta.form_classname)
        self.assertIn("pbk-form", LinkBlock().meta.form_classname)
