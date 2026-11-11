"""0.9: older Wagtail (7.0+), overlap on the canvas, pattern-shaped demo values, best-filled
real content, refresh of untouched demo sections, usage order, site tabs, scope "all"."""
import re
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page, Site

from prblm_builder import demo, mixins, registry, sites, views
from prblm_builder import settings as cfg

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "prblm_builder" / "static" / "prblm_builder"
OLDEST_WAGTAILCORE = 94     # wagtailcore.0094_alter_page_locale — in Wagtail 6.3, 7.0 and 8.x


class CompatibilityTests(TestCase):
    def test_migrations_depend_only_on_old_wagtailcore(self):
        """A migration made with the newest Wagtail must not depend on a wagtailcore
        migration older Wagtail doesn't have (lower it by hand before releasing)."""
        found = 0
        for path in list((ROOT / "prblm_builder").rglob("migrations/0*.py")):
            text = path.read_text()
            for number in re.findall(r"\('wagtailcore', '(\d{4})_", text):
                found += 1
                self.assertLessEqual(int(number), OLDEST_WAGTAILCORE, f"{path.name} depends on wagtailcore {number}")
            self.assertNotIn("to=settings.WAGTAIL_PAGE_MODEL", text, path.name)
        self.assertTrue(found)

    def test_mixin_is_a_no_op_without_the_settings_area(self):
        class Promo(mixins.BuilderSettingsMixin, blocks.StructBlock):
            title = blocks.CharBlock()
            background = blocks.CharBlock()

            class Meta:
                builder_settings = ["background"]

        block = Promo()
        with mock.patch.object(mixins, "BlockGroup", None), \
                mock.patch.object(blocks.StructBlock, "get_form_layout", create=True, return_value="wagtail's"):
            self.assertEqual(block.get_form_layout(), "wagtail's")

    def test_one_supported_range(self):
        toml = (ROOT / "pyproject.toml").read_text()
        self.assertIn('"wagtail>=7.0,<9"', toml)
        self.assertNotIn('"Django>=', toml)


class DemoContentTests(TestCase):
    def setUp(self):
        demo.reset_caches()

    def test_pattern_field_gets_a_value_that_validates(self):
        block = blocks.StructBlock([
            ("title", blocks.CharBlock()),
            ("link", blocks.RegexBlock(regex=r"^/[a-z0-9/-]*$", required=True)),
        ])
        value = demo.validated(block, "menu_item", block.to_python({"title": "Menu", "link": "Some words"}))
        self.assertIsNone(demo.problem(block, value))
        self.assertEqual(value["link"], "/")

    def test_score_counts_filled_fields_before_length(self):
        block = blocks.StructBlock([
            ("title", blocks.CharBlock()), ("text", blocks.TextBlock()),
            ("image", ImageChooserBlock(required=False)),
            ("items", blocks.ListBlock(blocks.CharBlock())),
        ])
        long_one = {"title": "", "text": "x" * 5000, "image": None, "items": []}
        full_one = {"title": "Hi", "text": "Short", "image": 7, "items": ["a", "b"]}
        self.assertGreater(demo._score(block, full_one), demo._score(block, long_one))
        no_image = {"title": "Hi", "text": "Short", "image": None, "items": ["a", "b", "c"]}
        self.assertEqual(demo._score(block, no_image)[0], demo._score(block, full_one)[0])
        self.assertEqual(demo._score(block, full_one)[1], 1)


class OrderTests(TestCase):
    def groups(self):
        a, b, c = blocks.CharBlock(), blocks.CharBlock(), blocks.CharBlock()
        return [("Alpha", [("a1", a, "A one"), ("a2", b, "A two")]), ("Beta", [("b1", c, "B one")])]

    def test_usage_order(self):
        counts = {"a1": 0, "a2": 3, "b1": 5}
        out = registry.order_by_usage(self.groups(), lambda n, b: counts[n])
        self.assertEqual([g for g, _ in out], ["Beta", "Alpha"])
        self.assertEqual([n for n, _b, _l in out[1][1]], ["a2", "a1"])

    def test_ties_alphabetical_and_alpha_setting(self):
        out = registry.order_by_usage(self.groups(), lambda n, b: 0)
        self.assertEqual([g for g, _ in out], ["Alpha", "Beta"])
        with override_settings(PRBLM_BUILDER_BLOCK_ORDER="alpha"):
            out = registry.order_by_usage(self.groups(), lambda n, b: {"b1": 9}.get(n, 0))
            self.assertEqual([g for g, _ in out], ["Alpha", "Beta"])


class SiteTabsTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("st", "st@example.com", "pw"))

    @override_settings(PRBLM_BUILDER_PREVIEW_SITES={"localhost": {"css": ["x.css"]}})
    def test_hidden_with_one_site_whatever_the_settings(self):
        self.assertEqual(Site.objects.count(), 1)
        self.assertEqual(sites.choices(), [])
        html = self.client.get(reverse("prblm_builder:demo")).content.decode()
        self.assertNotIn('aria-label="Preview as site"', html)
        self.assertNotIn('<select class="bl-site"', html)

    def test_tabs_with_several_sites(self):
        Site.objects.create(hostname="landing.example.com", root_page=Page.objects.get(depth=2), site_name="Landing")
        html = self.client.get(reverse("prblm_builder:demo")).content.decode()
        self.assertIn('class="bl-sites" aria-label="Preview as site"', html)
        self.assertIn(">All sites</a>", html)

    def test_dropdown_beyond_five_sites(self):
        for i in range(6):
            Site.objects.create(hostname=f"s{i}.example.com", root_page=Page.objects.get(depth=2))
        html = self.client.get(reverse("prblm_builder:demo")).content.decode()
        self.assertIn('<select class="bl-site"', html)


class OverlapTests(TestCase):
    def test_setting_and_per_site_profile(self):
        self.assertTrue(cfg.canvas_overlap())
        landing = Site.objects.create(hostname="landing.example.com", root_page=Page.objects.get(depth=2))
        with override_settings(PRBLM_BUILDER_PREVIEW_SITES={"landing.*": {"canvas_overlap": False}}):
            self.assertFalse(sites.config(site=landing)["canvas_overlap"])
            self.assertTrue(sites.config(site=Site.objects.get(is_default_site=True))["canvas_overlap"])
        with override_settings(PRBLM_BUILDER_CANVAS_OVERLAP=False):
            self.assertFalse(sites.config(site=landing)["canvas_overlap"])

    def test_canvas_wiring(self):
        frames = (STATIC / "frames.js").read_text()
        for needle in ("function edgeMargins", "function pokes", "function overlayHeader", "function measureFrame"):
            self.assertIn(needle, frames)
        js = (STATIC / "builder.js").read_text()
        self.assertIn('wrap.dataset.canvasOverlap !== "0"', js)
        self.assertIn("p.overlay", js)
        css = (STATIC / "builder.css").read_text()
        self.assertIn(".pb-sec.pb-pokes-down", css)

    def test_builder_gets_the_setting(self):
        from tests.testapp.models import StandardPage
        page = Page.objects.get(depth=2).add_child(instance=StandardPage(title="O", slug="o9", body="[]"))
        self.client.force_login(get_user_model().objects.create_superuser("ov", "ov@example.com", "pw"))
        url = reverse("prblm_builder:builder", args=[page.pk]) + "?embed=1"
        self.assertIn('data-canvas-overlap="1"', self.client.get(url).content.decode())
        with override_settings(PRBLM_BUILDER_CANVAS_OVERLAP=False):
            self.assertIn('data-canvas-overlap="0"', self.client.get(url).content.decode())


class CanvasCleanupTests(TestCase):
    def test_no_refresh_of_existing_sections(self):
        """Sections already on a page may hold real content: nothing refills them."""
        js = (STATIC / "builder.js").read_text()
        self.assertNotIn('data-act="refresh"', js)
        from tests.testapp.models import StandardPage
        page = Page.objects.get(depth=2).add_child(instance=StandardPage(title="R", slug="r9", body="[]"))
        self.client.force_login(get_user_model().objects.create_superuser("rf", "rf@example.com", "pw"))
        html = self.client.get(reverse("prblm_builder:builder", args=[page.pk]) + "?embed=1").content.decode()
        self.assertNotIn("pb-refresh-all", html)

    def test_no_standalone_save(self):
        from django.urls import NoReverseMatch
        for name in ("prblm_builder:save", "prblm_builder:page_preview"):
            with self.assertRaises(NoReverseMatch):
                reverse(name, args=[1])

    def test_canvas_calls_only_functions_it_has(self):
        """builder.js gets measuring from frames.js as ``measureFrame`` — a leftover call
        to another name fails silently inside try/catch (sidebar thumbnails broke so)."""
        js = (STATIC / "builder.js").read_text()
        self.assertIsNone(re.search(r"[^.\w]measure\(", js))
        self.assertIn("measureFrame(f, false)", js)            # thumbnails

    def test_library_back_button(self):
        self.client.force_login(get_user_model().objects.create_superuser("bb", "bb@example.com", "pw"))
        html = self.client.get(reverse("prblm_builder:demo")).content.decode()
        self.assertIn('class="pb-back" href="%s"' % reverse("wagtailadmin_home"), html)
        self.assertIn('<path d="M15 18l-6-6 6-6"/>', html)


class FlagTests(TestCase):
    def test_preview_requests_are_flagged(self):
        request = RequestFactory().get("/")
        views._render_block(blocks.CharBlock(), "Hi", request)
        self.assertTrue(request.is_prblm_preview)
