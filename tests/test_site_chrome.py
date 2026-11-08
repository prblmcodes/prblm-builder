"""Phase 5: the site-wide Header & footer — admin page, canvas, template tags."""
import json
import uuid

from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from wagtail.models import Page, Site

from prblm_builder.blocks.models import SiteChrome
from prblm_builder.blocks.sections.site import FooterBlock, HeaderBlock
from tests.testapp.models import StandardPage

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def set_chrome(header_name="Acme Header", footer_text="Acme Footer text"):
    site = Site.objects.get(is_default_site=True)
    h, f = HeaderBlock(), FooterBlock()
    header = {**h.get_prep_value(h.get_default()), "site_name": header_name}
    footer = {**f.get_prep_value(f.get_default()), "description": footer_text}
    obj = SiteChrome.for_site(site)
    obj.header = json.dumps([{"type": "header", "value": header}])
    obj.footer = json.dumps([{"type": "footer", "value": footer}])
    obj.save()
    return obj


@override_settings(STORAGES=STORAGES)
class SiteChromeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser("chrome-admin", "c@example.com", "pw")
        cls.page = StandardPage(title="Chrome page", slug="chrome-" + uuid.uuid4().hex[:5])
        cls.page.body = json.dumps([{"type": "heading", "value": "Hi", "id": "x1"}])
        Page.objects.get(depth=1).add_child(instance=cls.page)

    def setUp(self):
        self.client.force_login(self.admin)

    def builder(self):
        return self.client.get(reverse("prblm_builder:builder", args=[self.page.id]) + "?embed=1")

    def test_no_chrome_by_default(self):
        r = self.builder()
        self.assertEqual(r.context["header_src"], "")
        self.assertEqual(r.context["footer_src"], "")

    def test_site_chrome_shows_on_canvas(self):
        set_chrome()
        r = self.builder()
        self.assertTrue(r.context["header_src"])
        self.assertTrue(r.context["footer_src"])
        html = self.client.get(r.context["header_src"]).content.decode()
        self.assertIn("Acme Header", html)
        self.assertIn("blocks.css", html)
        footer = self.client.get(r.context["footer_src"]).content.decode()
        self.assertIn("Acme Footer text", footer)

    def test_new_page_builder_also_gets_chrome(self):
        set_chrome()
        r = self.client.get(reverse("prblm_builder:builder_new") + "?model=testapp.StandardPage")
        self.assertTrue(r.context["header_src"])

    @override_settings(PRBLM_BUILDER_HEADER_TEMPLATE="testapp/header.html")
    def test_template_setting_wins(self):
        set_chrome()
        src = self.builder().context["header_src"]
        html = self.client.get(src).content.decode()
        self.assertIn("Header for Chrome page", html)
        self.assertNotIn("Acme Header", html)

    def test_template_tags(self):
        set_chrome()
        request = RequestFactory().get("/")
        out = Template("{% load prblm_blocks %}{% prblm_header %}|{% prblm_footer %}").render(
            Context({"request": request}))
        self.assertIn("Acme Header", out)
        self.assertIn("Acme Footer text", out)
        self.assertEqual(out.count("blocks.css"), 1)   # assets once across both

    def test_template_tags_empty_without_chrome(self):
        out = Template("{% load prblm_blocks %}[{% prblm_header %}]").render(Context({}))
        self.assertEqual(out, "[]")

    def test_menu_item_and_edit_page(self):
        html = self.client.get(reverse("wagtailadmin_home")).content.decode()
        self.assertIn('"prblm-builder-chrome-page"', html)
        self.assertNotIn('"prblm-builder-chrome"', html)
        site = Site.objects.get(is_default_site=True)
        url = reverse("wagtailsettings:edit", args=["prblm_builder_blocks", "sitechrome", site.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
