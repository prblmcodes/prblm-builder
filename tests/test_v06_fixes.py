"""v0.6.0 fixes from real-site testing: site assets in Wagtail's preview, full text on the
canvas, blocks matched by class, demo values that pass the block's own validation."""
import json
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail import blocks
from wagtail.models import Page, Site

from prblm_builder import previews, registry

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=STORAGES, PRBLM_BUILDER_PREVIEW_CSS=["css/site.css", "https://cdn.example.com/x.css"],
                   PRBLM_BUILDER_PREVIEW_JS=["js/site.js"],
                   PRBLM_BUILDER_HEADER_TEMPLATE="testapp/header.html")
class SiteAssetsInWagtailPreviewTests(TestCase):
    """Wagtail's preview renders with a fake request using the Site's hostname / port; the
    site's CSS must not be tied to that host."""

    def test_asset_urls_are_root_relative(self):
        self.assertEqual(previews.asset_urls(["css/site.css", "https://cdn.example.com/x.css"]),
                         ["/static/css/site.css", "https://cdn.example.com/x.css"])

    def test_builder_page_preview_links_site_css_without_host(self):
        from prblm_builder.blocks.models import BuilderPage
        Site.objects.update(hostname="example.org", port=8123)
        page = Page.objects.get(depth=2).add_child(instance=BuilderPage(
            title="P", slug="p-" + uuid.uuid4().hex[:5], header_choice="site", body="[]"))
        request = page.make_preview_request()
        html = request.content.decode() if hasattr(request, "content") else str(request)
        self.assertIn('href="/static/css/site.css"', html)
        self.assertIn('src="/static/js/site.js"', html)
        self.assertNotIn("example.org:8123/static", html)


@override_settings(STORAGES=STORAGES)
class CanvasShowsFullTextTests(TestCase):
    """A new section on the canvas shows exactly what will be saved; only the Block library
    and thumbnails (``&trim=1``) shorten long text."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("ft", "ft@example.com", "pw"))
        from tests.testapp.models import StandardPage
        self.words = " ".join(f"word{i}" for i in range(200))
        Page.objects.get(depth=2).add_child(instance=StandardPage(
            title="Long", slug="long", body=json.dumps([
                {"type": "rich_text", "value": f"<p>{self.words}</p>", "id": "rt1"}])))
        previews._INDEX["data"] = None    # the real-content index is cached briefly

    def get(self, extra=""):
        url = reverse("prblm_builder:preview") + "?model=testapp.StandardPage&block=rich_text&demo=1" + extra
        return self.client.get(url).content.decode()

    def test_canvas_preview_is_not_trimmed(self):
        self.assertIn("word199", self.get())

    def test_thumbnail_preview_is_trimmed(self):
        html = self.get("&trim=1")
        self.assertIn("word0", html)
        self.assertNotIn("word199", html)

    def test_thumbnails_and_library_ask_for_trimmed_previews(self):
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent / "prblm_builder" / "templates" / "prblm_builder"
        self.assertIn("&demo=1&trim=1", (root / "builder.html").read_text())
        self.assertIn("&demo=1&trim=1", (root / "demo.html").read_text())


class MatchByClassTests(TestCase):
    """The site's own block on the Builder page under another name (``site_card`` =
    LandingPage's ``card``) is the same block."""

    def builder_block(self, name):
        from prblm_builder.blocks.models import BuilderPage
        return BuilderPage.body.field.stream_block.child_blocks[name]

    def test_block_key(self):
        from tests.examples.blocks import CardBlock
        self.assertEqual(registry.block_key("a", CardBlock()), registry.block_key("b", CardBlock()))
        self.assertEqual(registry.block_key("a", CardBlock()), ("class", "tests.examples.blocks.CardBlock"))
        # Wagtail's generic blocks say nothing about the content: matched by name.
        self.assertEqual(registry.block_key("intro", blocks.RichTextBlock()), ("name", "intro"))

    def test_shares_real_content_across_names(self):
        from tests.examples.models import LandingPage
        Page.objects.get(depth=2).add_child(instance=LandingPage(
            title="L", slug="l", body=json.dumps([{"type": "card", "id": "c1", "value": {
                "title": "Real card title", "text": "", "link": {"label": "Go", "link_type": "url",
                                                                 "url": "https://example.com"}}}])))
        previews._INDEX["data"] = None
        value, page = previews.real_instance_for("site_card", self.builder_block("site_card"))
        self.assertEqual(value["title"], "Real card title")
        self.assertEqual(page.title, "L")

    def test_library_lists_it_once_under_the_sites_name(self):
        names = [n for (n, builtin), b in registry.library_blocks().items()
                 if type(b).__name__ == "CardBlock"]
        self.assertEqual(names, ["card"])


class ValidDemoValueTests(TestCase):
    """Synthesised demo content passes the block's own validation, also for third-party
    blocks with rules we can't know about."""

    class ThirdPartyLink(blocks.StructBlock):
        # Shaped like wagtail-link-block's LinkBlock: a "link to" dropdown, one field per
        # type (with validators), and a clean() that requires the chosen type's field.
        link_to = blocks.ChoiceBlock(choices=[("page", "Page"), ("custom_url", "URL")], required=False)
        page = blocks.PageChooserBlock(required=False)
        custom_url = blocks.CharBlock(required=False, validators=[URLValidator()])
        destination = blocks.CharBlock(required=False, validators=[URLValidator()])

        def clean(self, value):
            value = super().clean(value)
            kind = value.get("link_to")
            if kind and not value.get(kind):
                from wagtail.blocks import StructBlockValidationError
                raise StructBlockValidationError(block_errors={kind: ValidationError("Required")})
            return value

    def block(self):
        b = blocks.StructBlock([("heading", blocks.CharBlock()), ("button", self.ThirdPartyLink())])
        b.set_name("hero_test")
        return b

    def test_demo_value_is_valid(self):
        b = self.block()
        value = previews.demo_value(b, "hero_test")
        b.clean(value)                                    # raises if invalid
        self.assertEqual(value["button"]["custom_url"], "https://example.com")
        self.assertTrue(value["heading"])                 # the rest of the demo stays

    def test_unknown_validated_field_is_emptied(self):
        b = self.block()
        value = previews.synth_demo(b, "hero_test")
        b.clean(value)
        self.assertFalse(value["button"]["destination"])

    def test_snippet_chooser_gets_a_snippet(self):
        from wagtail.snippets.blocks import SnippetChooserBlock
        from prblm_builder.blocks.models import SiteHeader
        SiteHeader.objects.create(name="Main")
        b = SnippetChooserBlock("prblm_builder_blocks.SiteHeader")
        self.assertEqual(previews.synth_value(b, "header").name, "Main")


class ChromeHeightWiringTests(TestCase):
    def test_header_frame_measures_visible_content(self):
        from pathlib import Path
        js = (Path(__file__).resolve().parent.parent / "prblm_builder" / "static" /
              "prblm_builder" / "builder.js").read_text()
        self.assertIn("function chromeHeight", js)
        self.assertIn("isChrome ? chromeHeight(d)", js)
        self.assertNotIn("el.offsetHeight) || d.documentElement.scrollHeight", js)
