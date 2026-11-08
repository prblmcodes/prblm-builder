"""The built-in section blocks: every block renders from its defaults, defaults explain
themselves, real values render correctly, and the builder treats them as built-ins."""
import json
import re
import uuid

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from wagtail.models import Page

from prblm_builder import previews, registry
from prblm_builder.blocks import builder_blocks
from prblm_builder.layout import reconcile
from tests.testapp.models import BlocksPage

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def render(block, value=None, **ctx):
    ctx.setdefault("request", RequestFactory().get("/"))
    return block.render(block.get_default() if value is None else value, context=ctx)


def visible_text(html):
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


@override_settings(STORAGES=STORAGES)
class EveryBlockTests(TestCase):
    def test_each_block_renders_its_defaults(self):
        for name, block in builder_blocks():
            with self.subTest(block=name):
                html = render(block)
                self.assertIn('class="pbk ', html)
                self.assertIn("blocks.css", html)                 # assets included
                text = visible_text(html)
                self.assertTrue(len(text) > 20, text)
                self.assertNotRegex(text, r"\bNone\b")

    def test_defaults_survive_save_and_load(self):
        """Seeding stores get_prep_value(default); it must load and render the same."""
        for name, block in builder_blocks():
            with self.subTest(block=name):
                stored = json.loads(json.dumps(block.get_prep_value(block.get_default())))
                again = block.to_python(stored)
                self.assertEqual(visible_text(render(block, again)),
                                 visible_text(render(block)))

    def test_assets_once_for_a_whole_page(self):
        request = RequestFactory().get("/")
        html = "".join(render(b, request=request) for _n, b in builder_blocks())
        self.assertEqual(html.count("blocks.css"), 1)

    def test_all_are_builtin_and_grouped(self):
        for name, block in builder_blocks():
            self.assertTrue(registry.is_builtin(block), name)
            self.assertTrue(getattr(block.meta, "group", ""), name)

    def test_helper_exclude_and_only(self):
        names = [n for n, _ in builder_blocks(exclude=["header", "footer"])]
        self.assertNotIn("header", names)
        self.assertEqual([n for n, _ in builder_blocks(only=["faq"])], ["faq"])


@override_settings(STORAGES=STORAGES)
class BlockDetailTests(TestCase):
    def block(self, name):
        return dict(builder_blocks())[name]

    def test_header_menu_dropdown_and_toggle(self):
        html = render(self.block("header"))
        self.assertIn('aria-label="Main"', html)
        self.assertIn("data-pbk-menu-toggle", html)
        nav_id = re.search(r'<nav class="pbk-nav" id="([^"]+)"', html).group(1)
        self.assertIn(f'aria-controls="{nav_id}"', html)
        self.assertIn("pbk-nav__sub", html)                   # Services dropdown
        self.assertIn("Get in touch", html)

    def test_header_sticky(self):
        b = self.block("header")
        v = b.to_python({**b.get_prep_value(b.get_default()), "sticky": True})
        self.assertIn("pbk-header--sticky", render(b, v))

    def test_footer_year_and_social(self):
        from datetime import date
        html = render(self.block("footer"))
        self.assertIn(f"© {date.today().year}", html)
        self.assertIn('aria-label="Linkedin"', html)

    def test_hero_positions(self):
        b = self.block("hero")
        base = b.get_prep_value(b.get_default())
        side = render(b)
        self.assertIn("pbk-hero__media", side)
        self.assertIn("Hero image · 1200×900", side)          # placeholder explains itself
        bg = render(b, b.to_python({**base, "image_position": "background"}))
        self.assertIn("pbk-hero__bg", bg)
        none = render(b, b.to_python({**base, "image_position": "none"}))
        self.assertNotIn("pbk-ph", none)
        self.assertIn("<h1", side)

    def test_page_banner_breadcrumbs_need_page(self):
        b = self.block("page_banner")
        self.assertNotIn("pbk-crumbs", render(b))
        home = Page.objects.get(depth=2)
        child = home.add_child(instance=BlocksPage(title="About us", slug="about-" + uuid.uuid4().hex[:5]))
        html = render(b, page=child)
        self.assertIn('aria-current="page">About us', html)
        self.assertIn(home.title, html)

    def test_text_image_side(self):
        b = self.block("text_image")
        v = b.to_python({**b.get_prep_value(b.get_default()), "image_side": "left"})
        self.assertIn("pbk-split--left", render(b, v))

    def test_features_columns_and_icons(self):
        html = render(self.block("features"))
        self.assertIn("--pbk-cols:3", html)
        self.assertEqual(html.count('class="pbk-icon"'), 3)

    def test_cta_hides_empty_secondary(self):
        html = render(self.block("call_to_action"))
        self.assertIn("pbk--brand", html)
        self.assertEqual(html.count("pbk-btn--"), 1)

    def test_faq_details(self):
        html = render(self.block("faq"))
        self.assertEqual(html.count("<details"), 3)
        self.assertEqual(html.count(" open>"), 1)

    def test_contact_links_and_anchor(self):
        html = render(self.block("contact_info"))
        self.assertIn('href="mailto:hello@example.com"', html)
        self.assertIn('href="tel:+00123456789"', html)
        self.assertIn('id="contact"', html)


@override_settings(STORAGES=STORAGES)
class BuilderIntegrationTests(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_superuser("blk-admin", "b@example.com", "pw")
        self.client.force_login(admin)

    def test_library_lists_builtins_first_with_no_preview_problems(self):
        r = self.client.get(reverse("prblm_builder:demo"))
        self.assertEqual(r.status_code, 200)
        kinds = [g["kind"] for g in r.context["groups"]]
        self.assertEqual(kinds[0], registry.KIND_BUILTIN)
        self.assertIn(registry.KIND_SITE, kinds)
        skipped = {b["name"] for b in r.context["unpreviewable"]}
        self.assertFalse(skipped & {n for n, _ in builder_blocks()})
        self.assertContains(r, "Built-in blocks")

    def test_builtin_preview_shows_explanatory_default(self):
        base = reverse("prblm_builder:preview")
        r = self.client.get(base + "?block=hero&demo=1&builtin=1")
        self.assertContains(r, "Your main headline")
        # Same name, site block: the test app's own hero, not the built-in one.
        r = self.client.get(base + "?block=hero&demo=1")
        self.assertNotContains(r, "Your main headline")

    def test_new_builtin_section_is_seeded_and_unedited(self):
        _f, sb = registry.stream_block_for(BlocksPage)
        seeded = reconcile(sb, [], [{"type": "faq", "id": "f1", "new": True}], [])
        self.assertEqual(seeded[0]["value"]["heading"], "Frequently asked questions")
        page = BlocksPage(title="Blocks", slug="blocks-" + uuid.uuid4().hex[:5])
        page.body = json.dumps(seeded)
        Page.objects.get(depth=1).add_child(instance=page)
        r = self.client.get(reverse("prblm_builder:builder", args=[page.id]) + "?embed=1")
        self.assertTrue(r.context["sections"][0]["unedited"])
        self.assertTrue(previews.is_unedited(sb.child_blocks["faq"], "faq",
                                             seeded[0]["value"], page.pk, "f1"))
