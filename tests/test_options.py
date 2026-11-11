"""Tests for the v0.2 options and Block library behaviour. They rely on the edge-case
blocks in ``tests.testapp`` (an opted-out block, a broken one, an empty one, a link
fragment used only nested / in a non-page model), so they live outside the package."""
import json
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.images import get_image_model
from wagtail.models import Page

from prblm_builder import previews, registry
from prblm_builder.layout import reconcile
from tests.testapp.models import StandardPage

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def palette_names():
    _f, sb = registry.stream_block_for(StandardPage)
    return {n for _g, items in registry.grouped_blocks(sb) for (n, _b, _l) in items}


@override_settings(STORAGES=STORAGES)
class OptionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser("opt-admin", "o@example.com", "pw")
        cls.page = StandardPage(title="Options", slug="options-" + uuid.uuid4().hex[:6])
        cls.page.body = json.dumps([{"type": "heading", "value": "Hello", "id": "h1"}])
        Page.objects.get(depth=1).add_child(instance=cls.page)

    def setUp(self):
        self.client.force_login(self.admin)

    def library(self):
        r = self.client.get(reverse("prblm_builder:demo"))
        self.assertEqual(r.status_code, 200)
        shown = {b["name"] for g in r.context["groups"] for b in g["blocks"]}
        skipped = {b["name"]: b["reason"] for b in r.context["unpreviewable"]}
        return shown, skipped

    # --- Block library scope -------------------------------------------------
    def test_library_matches_palette_by_default(self):
        shown, skipped = self.library()
        palettes = set()
        for model in registry.enabled_page_models():
            _f, sb = registry.stream_block_for(model)
            palettes |= {n for _g, items in registry.grouped_blocks(sb) for (n, _b, _l) in items}
        # The same block under two names is listed once (Builder page "site_card" = "card").
        self.assertEqual(shown | set(skipped), palettes - {"site_card"})
        self.assertNotIn("footer_link", shown | set(skipped))  # non-page StreamField

    @override_settings(PRBLM_BUILDER_LIBRARY_SCOPE="all")
    def test_library_scope_all_is_page_types_only(self):
        shown, skipped = self.library()
        self.assertIn("own_heading", shown | set(skipped))      # a page type's StreamField
        # A non-page model's StreamField (menus, settings, snippets) isn't page sections.
        self.assertNotIn("footer_link", shown | set(skipped))

    # --- hiding blocks -------------------------------------------------------
    def test_meta_builder_false_hides_block(self):
        self.assertNotIn("internal_note", palette_names())
        shown, skipped = self.library()
        self.assertNotIn("internal_note", shown | set(skipped))

    @override_settings(PRBLM_BUILDER_EXCLUDE_BLOCKS=["spacer"])
    def test_exclude_by_name(self):
        self.assertNotIn("spacer", palette_names())
        self.assertIn("heading", palette_names())

    @override_settings(PRBLM_BUILDER_EXCLUDE_BLOCKS=["wagtail.blocks.RichTextBlock"])
    def test_exclude_by_class(self):
        self.assertNotIn("rich_text", palette_names())
        self.assertIn("heading", palette_names())

    @override_settings(PRBLM_BUILDER_EXCLUDE_BLOCKS=["no.such.Block"])
    def test_bad_class_path_is_ignored(self):
        self.assertIn("rich_text", palette_names())

    # --- blocks that can't preview ---------------------------------------------
    def test_unpreviewable_blocks_listed_separately(self):
        shown, skipped = self.library()
        self.assertIn("Error", skipped["broken"])
        self.assertIn("no text", skipped["spacer"])
        self.assertIn("heading", shown)
        self.assertIn("broken", palette_names())  # still draggable in the Layout tab
        r = self.client.get(reverse("prblm_builder:demo"))
        self.assertContains(r, "preview 2 blocks on their own")

    # --- removed seed setting ---------------------------------------------------
    def test_new_block_always_seeded(self):
        _f, sb = registry.stream_block_for(StandardPage)
        out = reconcile(sb, [], [{"type": "heading", "id": "n1", "new": True}], [])
        self.assertTrue(out[0]["value"])

    @override_settings(PRBLM_BUILDER_SEED_NEW_BLOCKS=False)
    def test_removed_seed_setting_warns(self):
        from prblm_builder.checks import removed_settings
        ids = [w.id for w in removed_settings(None)]
        self.assertEqual(ids, ["prblm_builder.W001"])

    def test_no_warning_without_removed_setting(self):
        from prblm_builder.checks import removed_settings
        self.assertEqual(removed_settings(None), [])

    # --- "Not edited yet" -----------------------------------------------------------
    def _sections(self, page):
        r = self.client.get(reverse("prblm_builder:builder", args=[page.id]) + "?embed=1")
        return {s["id"]: s for s in r.context["sections"]}

    def test_seeded_section_is_unedited_until_changed(self):
        _f, sb = registry.stream_block_for(StandardPage)
        seeded = reconcile(sb, [], [{"type": "heading", "id": "s1", "new": True}], [])
        page = StandardPage(title="Seeded", slug="seeded-" + uuid.uuid4().hex[:6])
        page.body = json.dumps(seeded + [{"type": "heading", "value": "Written by a person", "id": "s2"}])
        Page.objects.get(depth=1).add_child(instance=page)
        secs = self._sections(page)
        self.assertTrue(secs["s1"]["unedited"])     # still the demo text
        self.assertFalse(secs["s2"]["unedited"])    # real content

    def test_real_source_section_is_not_flagged(self):
        """The section the demo content is *taken from* must not count as unedited."""
        __import__("prblm_builder.demo").demo.reset_caches()              # rebuild the real-content index
        secs = self._sections(self.page)            # 'h1' is the only heading on the site
        self.assertFalse(secs["h1"]["unedited"])

    def test_badge_markup_in_builder_js(self):
        from django.contrib.staticfiles import finders
        js = open(finders.find("prblm_builder/builder.js")).read()
        self.assertIn("Not edited yet", js)

    # --- admin menu ------------------------------------------------------------------
    def test_page_builder_menu_has_block_library(self):
        r = self.client.get(reverse("wagtailadmin_home"))
        html = r.content.decode()
        self.assertIn("Page builder", html)
        self.assertIn("Block library", html)

    @override_settings(PRBLM_BUILDER_DEMO=False)
    def test_block_library_menu_item_hidden_when_disabled(self):
        r = self.client.get(reverse("wagtailadmin_home"))
        self.assertNotIn('"prblm-builder-library"', r.content.decode())

    # --- canvas width ------------------------------------------------------------
    @override_settings(PRBLM_BUILDER_CANVAS_WIDTH=1440)
    def test_canvas_width_reaches_builder(self):
        r = self.client.get(reverse("prblm_builder:builder", args=[self.page.id]) + "?embed=1")
        self.assertContains(r, 'data-canvas-width="1440"')

    def test_canvas_width_default(self):
        r = self.client.get(reverse("prblm_builder:builder", args=[self.page.id]) + "?embed=1")
        self.assertContains(r, 'data-canvas-width="1280"')

    # --- placeholder images --------------------------------------------------------
    @override_settings(PRBLM_BUILDER_PLACEHOLDER_IMAGES=False)
    def test_no_placeholder_images_when_off(self):
        previews._IMG_CACHE.clear()
        self.assertIsNone(previews.placeholder_image())
        self.assertFalse(get_image_model().objects.filter(
            title__startswith=previews.PLACEHOLDER_PREFIX).exists())

    def test_placeholder_image_created_when_on(self):
        previews._IMG_CACHE.clear()
        self.assertIsNotNone(previews.placeholder_image())

    # --- admin tweaks ---------------------------------------------------------------
    def _edit_html(self):
        r = self.client.get(reverse("wagtailadmin_pages:edit", args=[self.page.id]))
        self.assertEqual(r.status_code, 200)
        return r.content.decode()

    def test_admin_tweaks_on_by_default(self):
        html = self._edit_html()
        self.assertIn("w-form-width:has(.prblm-layout-panel)", html)
        self.assertIn("pb-lib-link", html)

    @override_settings(PRBLM_BUILDER_ADMIN_TWEAKS=False)
    def test_admin_tweaks_off(self):
        html = self._edit_html()
        self.assertNotIn("w-form-width:has(.prblm-layout-panel)", html)
        self.assertNotIn("pb-lib-link", html)
        self.assertIn("prblm-layout-panel", html)  # the Layout tab itself still works

    # --- header/footer get the page -----------------------------------------------------
    @override_settings(PRBLM_BUILDER_HEADER_TEMPLATE="testapp/header.html")
    def test_header_gets_page_context(self):
        base = reverse("prblm_builder:preview")
        self.assertContains(self.client.get(f"{base}?page={self.page.id}&chrome=header"),
                            "Header for Options")
        self.assertContains(self.client.get(f"{base}?model=testapp.StandardPage&chrome=header"),
                            "Header for no page")



class SiteBlockColumnsSettingTests(TestCase):
    def test_default_off(self):
        from prblm_builder import settings as cfg
        self.assertFalse(cfg.site_block_columns())

    @override_settings(PRBLM_BUILDER_SITE_BLOCK_COLUMNS=True)
    def test_on(self):
        from prblm_builder import settings as cfg
        self.assertTrue(cfg.site_block_columns())


class PreviewOptions08Tests(TestCase):
    """0.8 settings (the full behaviour is tested in tests/test_v08.py)."""

    def test_readers(self):
        from prblm_builder import settings as cfg
        self.assertEqual(cfg.preview_body_attrs(), {})
        self.assertEqual(cfg.preview_html_attrs(), {})
        self.assertTrue(cfg.reduce_motion())
        with self.settings(PRBLM_BUILDER_PREVIEW_HTML_ATTRS={"lang": "en"}, PRBLM_BUILDER_REDUCE_MOTION=0):
            self.assertEqual(cfg.preview_html_attrs(), {"lang": "en"})
            self.assertFalse(cfg.reduce_motion())


class Options09Tests(TestCase):
    """0.9 settings (the full behaviour is tested in tests/test_v09.py)."""

    def test_readers(self):
        from prblm_builder import settings as cfg
        self.assertTrue(cfg.canvas_overlap())
        self.assertEqual(cfg.block_order(), "usage")
        with self.settings(PRBLM_BUILDER_CANVAS_OVERLAP=False, PRBLM_BUILDER_BLOCK_ORDER="ALPHA"):
            self.assertFalse(cfg.canvas_overlap())
            self.assertEqual(cfg.block_order(), "alpha")
        with self.settings(PRBLM_BUILDER_BLOCK_ORDER="random"):
            self.assertEqual(cfg.block_order(), "usage")
