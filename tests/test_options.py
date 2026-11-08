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
        self.assertEqual(shown | set(skipped), palette_names())
        self.assertNotIn("footer_link", shown | set(skipped))  # non-page StreamField

    @override_settings(PRBLM_BUILDER_LIBRARY_SCOPE="all")
    def test_library_scope_all_includes_other_streamfields(self):
        shown, skipped = self.library()
        self.assertIn("footer_link", shown | set(skipped))

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

    # --- new blocks: seeded or empty ---------------------------------------------
    def _add_heading(self):
        _f, sb = registry.stream_block_for(StandardPage)
        out = reconcile(sb, [], [{"type": "heading", "id": "n1", "new": True}], [])
        return out[0]["value"]

    def test_new_block_seeded_by_default(self):
        self.assertTrue(self._add_heading())

    @override_settings(PRBLM_BUILDER_SEED_NEW_BLOCKS=False)
    def test_new_block_empty_when_seeding_off(self):
        self.assertEqual(self._add_heading(), "")

    @override_settings(PRBLM_BUILDER_SEED_NEW_BLOCKS=False)
    def test_new_struct_block_has_no_none_text(self):
        _f, sb = registry.stream_block_for(StandardPage)
        value = reconcile(sb, [], [{"type": "hero", "id": "n2", "new": True}], [])[0]["value"]
        self.assertEqual(value["title"], "")
        self.assertEqual(value["cta"]["text"], "")
        html = sb.child_blocks["hero"].render(sb.child_blocks["hero"].to_python(value))
        self.assertNotIn("None", html)

    @override_settings(PRBLM_BUILDER_SEED_NEW_BLOCKS=False)
    def test_fresh_preview_shows_placeholder_when_seeding_off(self):
        url = reverse("prblm_builder:preview") + f"?page={self.page.id}&block=heading&demo=1&fresh=1"
        self.assertContains(self.client.get(url), "Add its content in the Content tab")

    def test_fresh_preview_shows_demo_when_seeding_on(self):
        url = reverse("prblm_builder:preview") + f"?page={self.page.id}&block=heading&demo=1&fresh=1"
        self.assertNotContains(self.client.get(url), "Add its content in the Content tab")

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
