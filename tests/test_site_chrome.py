"""Headers & Footers (v0.4): reusable items, site default, Builder page choices, canvas,
template tags, and the migration from 0.3's single Header & footer page."""
import json
import uuid

from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from wagtail.models import Page

from prblm_builder.blocks.models import BuilderPage, SiteFooter, SiteHeader
from prblm_builder.blocks.sections.site import FooterBlock, HeaderBlock
from tests.testapp.models import StandardPage

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def header_json(site_name):
    h = HeaderBlock()
    return json.dumps([{"type": "header", "value": {**h.get_prep_value(h.get_default()), "site_name": site_name}}])


def footer_json(text):
    f = FooterBlock()
    return json.dumps([{"type": "footer", "value": {**f.get_prep_value(f.get_default()), "description": text}}])


def set_chrome(header_name="Acme Header", footer_text="Acme Footer text"):
    """Create a site-default header + footer (used by other test modules too)."""
    h = SiteHeader.objects.create(name="Main header", is_default=True, content=header_json(header_name))
    f = SiteFooter.objects.create(name="Main footer", is_default=True, content=footer_json(footer_text))
    return h, f


@override_settings(STORAGES=STORAGES)
class HeadersFootersTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser("chrome-admin", "c@example.com", "pw")
        cls.home = Page.objects.get(depth=2)
        cls.page = StandardPage(title="Chrome page", slug="chrome-" + uuid.uuid4().hex[:5])
        cls.page.body = json.dumps([{"type": "heading", "value": "Hi", "id": "x1"}])
        cls.home.add_child(instance=cls.page)

    def setUp(self):
        self.client.force_login(self.admin)

    def builder(self, page):
        return self.client.get(reverse("prblm_builder:builder", args=[page.id]) + "?embed=1")

    def chrome_html(self, page, kind="header"):
        src = self.builder(page).context[f"{kind}_src"]
        return self.client.get(src).content.decode() if src else ""

    # --- the items themselves ------------------------------------------------------
    def test_one_default_per_kind(self):
        a = SiteHeader.objects.create(name="A", is_default=True, content=header_json("A"))
        b = SiteHeader.objects.create(name="B", is_default=True, content=header_json("B"))
        a.refresh_from_db()
        self.assertFalse(a.is_default)
        self.assertTrue(b.is_default)
        self.assertEqual(str(b), "B (site default)")

    def test_new_header_starts_with_example_content(self):
        h = SiteHeader(name="New")
        self.assertEqual(len(h.content), 1)
        self.assertEqual(h.content[0].value["site_name"], "Your site name")

    def test_admin_lists_and_menu(self):
        html = self.client.get(reverse("wagtailadmin_home")).content.decode()
        self.assertIn('"prblm-builder-headers"', html)
        self.assertIn('"prblm-builder-footers"', html)
        self.assertNotIn("prblm-builder-chrome", html)            # 0.3 page is gone
        set_chrome()
        r = self.client.get(reverse("wagtailsnippets_prblm_builder_blocks_siteheader:list"))
        self.assertContains(r, "Main header")
        r = self.client.get(reverse("wagtailsnippets_prblm_builder_blocks_siteheader:add"))
        self.assertEqual(r.status_code, 200)

    # --- canvas ----------------------------------------------------------------------
    def test_no_chrome_without_default(self):
        r = self.builder(self.page)
        self.assertEqual(r.context["header_src"], "")

    def test_site_default_on_canvas_for_own_pages(self):
        set_chrome()
        self.assertIn("Acme Header", self.chrome_html(self.page))
        self.assertIn("Acme Footer text", self.chrome_html(self.page, "footer"))

    @override_settings(PRBLM_BUILDER_HEADER_TEMPLATE="testapp/header.html")
    def test_template_setting_wins_for_own_pages(self):
        set_chrome()
        html = self.chrome_html(self.page)
        self.assertIn("Header for Chrome page", html)
        self.assertNotIn("Acme Header", html)

    def test_new_page_canvas(self):
        set_chrome()
        r = self.client.get(reverse("prblm_builder:builder_new") + "?model=testapp.StandardPage")
        self.assertTrue(r.context["header_src"])
        r = self.client.get(reverse("prblm_builder:builder_new") + "?model=prblm_builder_blocks.BuilderPage")
        self.assertIn("Acme Header", self.client.get(r.context["header_src"]).content.decode())

    # --- Builder page choices ------------------------------------------------------------
    def make_builder(self, **kw):
        page = BuilderPage(title="BP", slug="bp-" + uuid.uuid4().hex[:5], **kw)
        self.home.add_child(instance=page)
        return page

    @override_settings(PRBLM_BUILDER_HEADER_TEMPLATE="testapp/header.html")
    def test_builder_page_choices(self):
        set_chrome()
        other = SiteHeader.objects.create(name="Campaign", content=header_json("Campaign Header"))
        cases = {
            "default": "Acme Header",           # Builder page: plugin default even with a template setting
            "custom": "Campaign Header",
            "site": "Header for BP",            # the site's own template
        }
        for choice, expected in cases.items():
            with self.subTest(choice=choice):
                page = self.make_builder(header_choice=choice, header=other if choice == "custom" else None)
                self.assertIn(expected, self.chrome_html(page))
                live = self.client.get(page.url).content.decode()
                self.assertIn(expected, live)
        page = self.make_builder(header_choice="none")
        self.assertEqual(self.builder(page).context["header_src"], "")
        self.assertNotIn("Acme Header", self.client.get(page.url).content.decode())

    def test_custom_choice_without_a_header_falls_back_to_default(self):
        # The fields are hidden (edited via the Layout sidebar), so no hidden-field error:
        # a chosen header that was deleted simply falls back to the site default.
        set_chrome()
        page = self.make_builder(header_choice="custom")
        self.assertIn("Acme Header", self.chrome_html(page))

    # --- template tags ---------------------------------------------------------------------
    def test_template_tags(self):
        set_chrome()
        SiteHeader.objects.create(name="Campaign", content=header_json("Campaign Header"))
        request = RequestFactory().get("/")
        out = Template('{% load prblm_blocks %}{% prblm_header %}|{% prblm_footer %}|{% prblm_header "Campaign" %}').render(
            Context({"request": request}))
        self.assertIn("Acme Header", out)
        self.assertIn("Acme Footer text", out)
        self.assertIn("Campaign Header", out)
        self.assertEqual(out.count("blocks.css"), 1)

    def test_template_tags_empty_without_items(self):
        out = Template("{% load prblm_blocks %}[{% prblm_header %}]").render(Context({}))
        self.assertEqual(out, "[]")


class MigrationFrom03Tests(TransactionTestCase):
    """The 0.3 Header & footer page (SiteChrome) becomes default SiteHeader/SiteFooter."""

    def test_site_chrome_migrated(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        app = "prblm_builder_blocks"
        executor = MigrationExecutor(connection)
        executor.migrate([(app, "0001_initial")])
        old_apps = executor.loader.project_state([(app, "0001_initial")]).apps
        Site = old_apps.get_model("wagtailcore", "Site")
        SiteChrome = old_apps.get_model(app, "SiteChrome")
        site = Site.objects.get(is_default_site=True)
        SiteChrome.objects.create(site=site, header=header_json("Old Header"),
                                  footer=footer_json("Old footer text"))

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

        header = SiteHeader.objects.get()
        self.assertTrue(header.is_default)
        self.assertEqual(header.content[0].value["site_name"], "Old Header")
        footer = SiteFooter.objects.get()
        self.assertTrue(footer.is_default)
        self.assertIn("Old footer text", footer.render())
