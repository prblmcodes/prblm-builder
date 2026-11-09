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

    def test_builtin_blocks_always_two_columns(self):
        html = self.admin_html()
        self.assertIn("prblm_builder/form-columns.js", html)
        self.assertIn("prblm_builder/form-columns.css", html)
        self.assertIn('data-site-blocks="0"', html)
        self.assertNotIn("form-columns-site.css", html)

    @override_settings(PRBLM_BUILDER_SITE_BLOCK_COLUMNS=True)
    def test_site_blocks_opt_in(self):
        html = self.admin_html()
        self.assertIn("form-columns-site.css", html)
        self.assertIn('data-site-blocks="1"', html)

    @override_settings(PRBLM_BUILDER_SITE_BLOCK_COLUMNS=False)
    def test_site_blocks_off_keeps_builtins(self):
        html = self.admin_html()
        self.assertIn("prblm_builder/form-columns.css", html)
        self.assertNotIn("form-columns-site.css", html)

    def test_builtin_block_forms_are_marked(self):
        from prblm_builder.blocks.sections.base import LinkBlock
        from prblm_builder.blocks.sections.heroes import HeroBlock
        self.assertIn("pbk-form", HeroBlock().meta.form_classname)
        self.assertIn("pbk-form", LinkBlock().meta.form_classname)


class ThemeFormColumnsTests(TestCase):
    def test_theme_groups_marked_for_two_columns(self):
        from prblm_builder.blocks.models import ThemeSettings
        self.assertTrue(all("pbk-form" in p.classname for p in ThemeSettings.panels))


@override_settings(STORAGES=STORAGES, PRBLM_BUILDER_PREVIEW_CSS=["css/site.css"],
                   PRBLM_BUILDER_PREVIEW_JS=["js/site.js"], PRBLM_BUILDER_PREVIEW_BODY_CLASS="site-body",
                   PRBLM_BUILDER_HEADER_TEMPLATE="testapp/header.html")
class BuilderPageSiteAssetsTests(TestCase):
    """A live Builder page loads the site's CSS / JS only when it shows the site's own
    header / footer or contains the site's own blocks."""

    def make(self, body=(), **kw):
        import json
        import uuid
        from wagtail.models import Page
        from prblm_builder.blocks.models import BuilderPage
        page = Page.objects.get(depth=2).add_child(instance=BuilderPage(
            title="SA", slug="sa-" + uuid.uuid4().hex[:5], body=json.dumps(list(body)), **kw))
        page.save_revision().publish()
        return self.client.get(page.url).content.decode()

    HERO = {"type": "hero", "id": "h1", "value": {"heading": "Hi"}}
    NOTE = {"type": "note", "id": "n1", "value": "A site block"}

    def assert_site_assets(self, html, present):
        check = self.assertIn if present else self.assertNotIn
        check("css/site.css", html)
        check("js/site.js", html)
        check("site-body", html)

    def test_builtin_only_page_stays_self_contained(self):
        self.assert_site_assets(self.make([self.HERO]), False)

    def test_site_header_loads_site_assets(self):
        html = self.make([self.HERO], header_choice="site")
        self.assert_site_assets(html, True)
        # the site's CSS comes before the blocks' CSS, so built-in styles win ties
        self.assertLess(html.index("css/site.css"), html.index("blocks/blocks.css"))

    @override_settings(PRBLM_BUILDER_FOOTER_TEMPLATE="testapp/header.html")
    def test_site_footer_loads_site_assets(self):
        self.assert_site_assets(self.make([self.HERO], footer_choice="site"), True)

    def test_site_block_loads_site_assets(self):
        self.assert_site_assets(self.make([self.HERO, self.NOTE]), True)

    @override_settings(PRBLM_BUILDER_HEADER_TEMPLATE="")
    def test_site_choice_without_template_stays_self_contained(self):
        self.assert_site_assets(self.make([self.HERO], header_choice="site"), False)


class SidebarTabTests(TestCase):
    def test_sidebar_always_opens_on_sections(self):
        from pathlib import Path
        js = (Path(__file__).resolve().parents[1] / "prblm_builder/static/prblm_builder/builder.js").read_text()
        self.assertNotIn('"prblm-builder:tab"', js)


@override_settings(STORAGES=STORAGES)
class VersionedAssetsTests(TestCase):
    def test_canvas_assets_are_versioned(self):
        from django.template.loader import render_to_string
        from prblm_builder.assets import version
        html = render_to_string("prblm_builder/demo.html", {"groups": [], "kinds": []})
        self.assertIn("prblm_builder/builder.css?v=" + version(), html)
