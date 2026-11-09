"""The examples in docs/EXAMPLES.md really work (the code lives in tests/examples/)."""
import json
import uuid

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from wagtail.models import Page

from prblm_builder import previews, registry
from prblm_builder.blocks import builder_blocks
from prblm_builder.blocks.fields import body_blocks
from tests.examples.blocks import PromoBlock
from tests.examples.models import ArticlePage, LandingPage

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def palette(model):
    _f, sb = registry.stream_block_for(model)
    return {n for _k, groups in registry.palette_sections(sb) for _g, items in groups for (n, _b, _l) in items}


@override_settings(STORAGES=STORAGES)
class ExamplesTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("ex", "ex@example.com", "pw"))

    def test_a_own_blocks_page_gets_the_layout_tab(self):
        headings = [c.heading for c in ArticlePage.get_edit_handler().children]
        self.assertEqual(headings[:2], ["Layout", "Content"])

    def test_a_palette_hides_the_nested_button(self):
        self.assertEqual(palette(ArticlePage), {"heading", "paragraph", "promo"})

    def test_heading_uses_its_preview_value_and_description(self):
        _f, sb = registry.stream_block_for(ArticlePage)
        heading = sb.child_blocks["heading"]
        self.assertEqual(previews.demo_value(heading, "heading"), "A heading for the next part of the page")
        self.assertEqual(registry.block_description(heading), "A large heading that starts a new part of the page.")

    def test_promo_settings_panel_and_content_tab(self):
        block = PromoBlock()
        self.assertEqual([f["name"] for f in registry.settings_schema(block)], ["background", "anchor_id"])
        self.assertEqual(block.meta.form_layout.settings, ["background", "anchor_id"])

    def test_promo_template_uses_the_settings(self):
        block = PromoBlock()
        value = block.to_python({"title": "Hi", "background": "dark", "anchor_id": "offer",
                                 "button": {"label": "Go", "url": "#go"}})
        html = block.render(value, context={"request": RequestFactory().get("/")})
        self.assertIn('class="promo promo--dark" id="offer"', html)
        self.assertIn('href="#go"', html)

    def test_new_promo_section_starts_with_its_preview_value(self):
        from prblm_builder.layout import reconcile
        _f, sb = registry.stream_block_for(ArticlePage)
        out = reconcile(sb, [], [{"type": "promo", "id": "p1", "new": True}], [])
        self.assertEqual(out[0]["value"]["title"], "Spring sale: 20% off everything")

    def test_b_landing_page_mixes_builtins_and_own_blocks(self):
        names = palette(LandingPage)
        self.assertIn("promo", names)
        self.assertIn("hero", names)
        self.assertNotIn("text", names)                     # excluded
        _f, sb = registry.stream_block_for(LandingPage)
        kinds = [k for k, _g in registry.palette_sections(sb)]
        self.assertEqual(kinds, [registry.KIND_BUILTIN, registry.KIND_SITE])

    def test_c_promo_on_the_builder_page_via_setting(self):
        blocks = body_blocks(builder_blocks(), [("promo", "tests.examples.blocks.PromoBlock")])
        self.assertEqual(blocks[-1][0], "promo")

    def test_builder_view_for_an_example_page(self):
        page = Page.objects.get(depth=2).add_child(instance=ArticlePage(
            title="Ex", slug="ex-" + uuid.uuid4().hex[:5],
            body=json.dumps([{"type": "promo", "id": "p1", "value": {"title": "Saved promo", "background": "light"}}])))
        r = self.client.get(reverse("prblm_builder:builder", args=[page.id]) + "?embed=1")
        self.assertEqual(r.status_code, 200)
        self.assertIn("promo", r.context["settings_schema"])
        self.assertEqual(r.context["sections"][0]["settings"]["background"], "light")
