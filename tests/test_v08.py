"""0.8: preview marker + reduce motion, <html>/<body> attributes, site matching by name and
wildcards, margin merging and release workflow wiring."""
import json
import uuid
from pathlib import Path

from django.test import TestCase, override_settings
from wagtail.models import Page, Site

from prblm_builder import previews, sites
from prblm_builder import settings as cfg

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "prblm_builder" / "static" / "prblm_builder"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


class SettingsTests(TestCase):
    def test_defaults(self):
        self.assertEqual((cfg.preview_body_attrs(), cfg.preview_html_attrs(), cfg.reduce_motion()),
                         ({}, {}, True))

    @override_settings(PRBLM_BUILDER_PREVIEW_BODY_ATTRS="x-data", PRBLM_BUILDER_REDUCE_MOTION=False)
    def test_bad_values(self):
        self.assertEqual(cfg.preview_body_attrs(), {})
        self.assertFalse(cfg.reduce_motion())


@override_settings(PRBLM_BUILDER_PREVIEW_BODY_ATTRS={"x-data": "{ open: false }", "class": "extra",
                                                     "bad name": "x", "data-x": '"<q>'},
                   PRBLM_BUILDER_PREVIEW_HTML_ATTRS={"data-theme": "light"},
                   PRBLM_BUILDER_PREVIEW_BODY_CLASS="font-body")
class PreviewShellTests(TestCase):
    def test_marker_and_attributes(self):
        html = previews.frame("<p>x</p>", None)
        self.assertIn('<html class="prblm-canvas" data-theme="light">', html)
        self.assertIn('<body class="font-body extra" x-data="{ open: false }"', html)
        self.assertIn('data-x="&quot;&lt;q&gt;"', html)          # escaped
        self.assertNotIn("bad name", html)                         # invalid names dropped
        self.assertIn("animation-duration:0s", html)

    @override_settings(PRBLM_BUILDER_REDUCE_MOTION=False)
    def test_reduce_motion_off(self):
        html = previews.frame("<p>x</p>", None)
        self.assertIn('class="prblm-canvas"', html)                # the marker always
        self.assertNotIn("animation-duration:0s", html)

    @override_settings(PRBLM_BUILDER_PREVIEW_TEMPLATE="testapp/preview_shell.html")
    def test_template_mode_marks_the_document(self):
        html = previews.frame("<p>x</p>", None)
        self.assertIn('classList.add("prblm-canvas")', html)
        self.assertIn('<meta name="prblm-preview" content="True">', html)
        self.assertIn('<body x-data="{ open: false }">', html)     # the template's own body
        self.assertNotIn("data-theme", html)                       # attrs settings ignored


class SiteMatchingTests(TestCase):
    def setUp(self):
        home = Page.objects.get(depth=2)
        self.landing = Site.objects.create(hostname="landing.localhost", port=8000, root_page=home,
                                           site_name="Landing")
        self.other = Site.objects.create(hostname="other.test", root_page=home, site_name="Other")

    def entry(self, site, conf):
        with override_settings(PRBLM_BUILDER_PREVIEW_SITES=conf):
            return sites.entry_for(site)

    def test_order(self):
        conf = {"landing.localhost:8000": {"n": 1}, "landing.localhost": {"n": 2},
                "Landing": {"n": 3}, "landing.*": {"n": 4}}
        self.assertEqual(self.entry(self.landing, conf)["n"], 1)
        del conf["landing.localhost:8000"]
        self.assertEqual(self.entry(self.landing, conf)["n"], 2)
        del conf["landing.localhost"]
        self.assertEqual(self.entry(self.landing, conf)["n"], 3)   # site name
        del conf["Landing"]
        self.assertEqual(self.entry(self.landing, conf)["n"], 4)   # wildcard
        self.assertIsNone(self.entry(self.other, conf))

    @override_settings(PRBLM_BUILDER_PREVIEW_SITES={"landing.*": {"css": ["landing.css"]}},
                       PRBLM_BUILDER_PREVIEW_CSS=["global.css"])
    def test_fallback_warns_once_and_shows_in_switcher(self):
        sites._WARNED.clear()
        with self.assertLogs("prblm_builder", level="WARNING") as logs:
            self.assertEqual(sites.config(site=self.other)["css"], ["global.css"])
            sites.config(site=self.other)
        self.assertEqual(len(logs.output), 1)
        labels = dict(sites.choices())
        self.assertIn("uses the default preview settings", labels["other.test"])
        self.assertNotIn("default preview settings", labels["landing.localhost"])
        self.assertEqual(sites.config(site=self.landing)["css"], ["landing.css"])


@override_settings(STORAGES=STORAGES, PRBLM_BUILDER_HEADER_TEMPLATE="testapp/header.html",
                   PRBLM_BUILDER_PREVIEW_BODY_ATTRS={"x-data": "{ showModal: false }"},
                   PRBLM_BUILDER_PREVIEW_HTML_ATTRS={"data-theme": "dark"})
class BuilderPageAttrsTests(TestCase):
    def page(self, **kw):
        from prblm_builder.blocks.models import BuilderPage
        page = Page.objects.get(depth=2).add_child(instance=BuilderPage(
            title="A", slug="a-" + uuid.uuid4().hex[:5], body=json.dumps([]), **kw))
        page.save_revision().publish()
        return self.client.get(page.url).content.decode()

    def test_attrs_when_site_assets_are_used(self):
        html = self.page(header_choice="site")
        self.assertIn('data-theme="dark"', html)
        self.assertIn('x-data="{ showModal: false }"', html)
        self.assertNotIn("prblm-canvas", html)                     # a live page, not a preview

    def test_no_attrs_on_self_contained_page(self):
        self.assertNotIn("showModal", self.page())


class WiringTests(TestCase):
    def test_margin_merging(self):
        frames = (STATIC / "frames.js").read_text()
        self.assertIn("function edgeMargin", frames)
        self.assertIn("collapse: collapse", frames)
        js = (STATIC / "builder.js").read_text()
        self.assertIn("function applyGaps", js)
        self.assertIn("Math.min(prev._pbM.mb, m.mt)", js)

    def test_release_workflow(self):
        wf = (ROOT / ".github" / "workflows" / "release.yml").read_text()
        self.assertIn('tags: ["v*"]', wf)
        self.assertIn("gh release upload", wf)


# --------------------------------------------------------------------------- part 2
class InertLinksTests(TestCase):
    def test_shell_and_template_mode(self):
        self.assertIn('closest("a[href],area[href]")', previews.frame("<a href='/x'>x</a>", None))
        with self.settings(PRBLM_BUILDER_PREVIEW_TEMPLATE="testapp/preview_shell.html"):
            self.assertIn('closest("a[href],area[href]")', previews.frame("<a href='/x'>x</a>", None))


@override_settings(STORAGES=STORAGES, PRBLM_BUILDER_HEADER_TEMPLATE="testapp/header.html")
class ChromeSourceTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_superuser("cs", "cs@example.com", "pw"))
        from tests.testapp.models import StandardPage
        self.page = Page.objects.get(depth=2).add_child(instance=StandardPage(title="Own", slug="own-cs", body="[]"))

    def header_info(self):
        from django.urls import reverse
        r = self.client.get(reverse("prblm_builder:builder", args=[self.page.id]) + "?embed=1")
        return [o for o in r.context["page_options"] if o["name"] == "header"][0]

    def test_site_template(self):
        from prblm_builder import chrome
        self.assertEqual(chrome.source("header", None, self.page), ("template", "testapp/header.html"))
        info = self.header_info()
        self.assertIn("shared header", info["info"])
        self.assertIn("testapp/header.html", info["hint"])

    def test_page_type_decides_in_code(self):
        from wagtail import hooks
        from prblm_builder import chrome

        def own(kind, request, page, model):
            return "<header>Landing header</header>" if kind == "header" else ""
        with hooks.register_temporarily("prblm_builder_chrome_for_page", own):
            self.assertEqual(chrome.source("header", None, self.page), ("page", True))
            self.assertEqual(chrome.source("footer", None, self.page), ("page", False))
            info = self.header_info()
            self.assertIn("its own header", info["info"])
            self.assertNotIn("testapp/header.html", info["info"] + info["hint"])


class SiteUsageTests(TestCase):
    def test_usage_per_site_and_all_sites_choice(self):
        from prblm_builder import demo
        from tests.examples.blocks import CardBlock
        from tests.examples.models import LandingPage
        root = Page.get_first_root_node()
        other_home = root.add_child(instance=Page(title="Other home", slug="other-home"))
        other = Site.objects.create(hostname="other.test", root_page=other_home, site_name="Other")
        card = {"type": "card", "value": {"title": "T", "text": "", "link": {"label": "", "link_type": "url", "url": ""}}}
        for parent in (Page.objects.get(depth=2, slug="home"), other_home):
            parent.add_child(instance=LandingPage(title="L", slug="l-" + uuid.uuid4().hex[:5],
                                                  body=json.dumps([dict(card, id=str(uuid.uuid4()))])))
        demo.reset_caches()
        self.assertEqual(len(demo.usage("card", CardBlock())), 2)
        self.assertEqual(len(demo.usage("card", CardBlock(), other)), 1)
        self.assertEqual(sites.choices()[-1], ("all", "All sites"))


@override_settings(STORAGES=STORAGES)
class LibraryAndPaletteMarkupTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_superuser("lm", "lm@example.com", "pw"))

    def test_library_cards_and_pills(self):
        from django.urls import reverse
        html = self.client.get(reverse("prblm_builder:demo")).content.decode()
        self.assertIn('class="bl-card-side"', html)
        self.assertIn("data-kind-filter", html)
        self.assertIn('data-kind-block="builtin"', html)
        self.assertIn("background:#e9ecf1", html)

    def test_layout_palette_pills(self):
        from django.urls import reverse
        from prblm_builder.blocks.models import BuilderPage
        page = Page.objects.get(depth=2).add_child(instance=BuilderPage(title="B", slug="b-pills", body="[]"))
        html = self.client.get(reverse("prblm_builder:builder", args=[page.id]) + "?embed=1").content.decode()
        self.assertIn('data-kind="site"', html)
        self.assertIn('data-kind-block="builtin"', html)

    def test_canvas_js(self):
        js = (STATIC / "builder.js").read_text()
        self.assertIn("function drawSpace", js)
        self.assertIn("function filterPalette", js)
