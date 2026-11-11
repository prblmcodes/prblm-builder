"""0.7: demo content field by field, no self-borrowing, per-site previews, preview template,
asset options, ⚙ checks, Block library usage, canvas measuring wiring."""
import json
import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page, Site

from prblm_builder import demo, layout, previews, registry
from prblm_builder import settings as cfg
from prblm_builder import sites

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
STATIC = Path(__file__).resolve().parent.parent / "prblm_builder" / "static" / "prblm_builder"


def home():
    return Page.objects.get(depth=2)


class Fresh(TestCase):
    def setUp(self):
        demo.reset_caches()
        previews._LEGACY.clear()


# --------------------------------------------------------------------------- A1
class PartialPreviewValueTests(Fresh):
    def block(self):
        class PromoHero(blocks.StructBlock):
            heading = blocks.CharBlock()
            background = ImageChooserBlock()            # required, left out of preview_value

            class Meta:
                preview_value = {"heading": "Hello"}
        b = PromoHero()
        b.set_name("promo_hero")
        return b

    @override_settings(STORAGES=STORAGES)
    def test_missing_required_field_is_filled_and_valid(self):
        b = self.block()
        value, _page = demo.build(b, "promo_hero")
        self.assertEqual(value["heading"], "Hello")       # the developer's value stays
        self.assertIsNotNone(value["background"])         # the gap is filled
        b.clean(value)                                    # and it saves

    def test_preview_value_still_wins_per_field(self):
        b = self.block()
        self.assertEqual(demo.build(b, "promo_hero")[0]["heading"], "Hello")


# --------------------------------------------------------------------------- A2
class NoSelfBorrowingTests(Fresh):
    def card_block(self):
        from tests.examples.blocks import CardBlock
        return CardBlock()

    def card(self, title, link=None):
        return {"type": "card", "id": str(uuid.uuid4()), "value": {
            "title": title, "text": "", "link": link or {"label": "Go", "link_type": "url", "url": "/x/"}}}

    def landing(self, *cards, live=True):
        from tests.examples.models import LandingPage
        page = home().add_child(instance=LandingPage(
            title="L", slug="l-" + uuid.uuid4().hex[:6], live=live, body=json.dumps(list(cards))))
        demo.reset_caches()
        return page

    def test_edited_published_content_is_borrowed(self):
        self.landing(self.card("Real card"))
        value, page = demo.real_instance("card", self.card_block())
        self.assertEqual(value["title"], "Real card")

    def test_draft_only_content_is_not_borrowed(self):
        self.landing(self.card("Draft card"), live=False)
        self.assertEqual(demo.real_instance("card", self.card_block()), (None, None))

    def test_invalid_content_is_not_borrowed(self):
        # A link label without a destination fails the built-in LinkBlock's validation.
        self.landing(self.card("Broken", {"label": "Go", "link_type": "url", "url": ""}))
        self.assertEqual(demo.real_instance("card", self.card_block()), (None, None))

    def test_seeded_unedited_section_is_not_borrowed(self):
        from tests.examples.models import LandingPage
        sb = LandingPage.body.field.stream_block
        raw = layout.reconcile(sb, [], [{"type": "card", "id": "seed-1", "new": True}], [])
        self.landing(raw[0])
        self.assertEqual(demo.real_instance("card", self.card_block()), (None, None))
        # …until someone edits it.
        raw[0]["value"]["title"] = "Edited by a person"
        self.landing(raw[0])
        self.assertEqual(demo.real_instance("card", self.card_block())[0]["title"], "Edited by a person")

    def test_seeded_section_is_unedited_until_changed(self):
        from tests.examples.models import LandingPage
        sb = LandingPage.body.field.stream_block
        raw = layout.reconcile(sb, [], [{"type": "card", "id": "seed-2", "new": True}], [])
        b = sb.child_blocks["card"]
        self.assertTrue(previews.is_unedited(b, "card", raw[0]["value"], section_id="seed-2"))
        changed = dict(raw[0]["value"], title="Mine")
        self.assertFalse(previews.is_unedited(b, "card", changed, section_id="seed-2"))

    def test_usage_counts_live_pages(self):
        self.landing(self.card("A"))
        self.landing(self.card("B"))
        self.landing(self.card("C"), live=False)
        self.assertEqual(len(demo.usage("card", self.card_block())), 2)


# --------------------------------------------------------------------------- C
class GeneratedContentTests(Fresh):
    def test_neutral_text_from_help_or_label(self):
        b = blocks.StructBlock([
            ("line_one", blocks.CharBlock(help_text="Section Heading Line One")),
            ("intro", blocks.TextBlock()),
            ("title", blocks.CharBlock(max_length=8)),
            ("code", blocks.CharBlock(help_text="Leave empty to hide it.")),
        ])
        v = demo.build(b, "x", real=False)[0]
        self.assertEqual(v["line_one"], "Section heading line one")
        self.assertIn("one or two sentences", v["intro"])
        self.assertLessEqual(len(v["title"]), 8)
        self.assertEqual(v["code"], "Code")                # instructions aren't used as text

    def test_rich_text_length_follows_the_field(self):
        b = blocks.StructBlock([("heading", blocks.RichTextBlock()), ("body", blocks.RichTextBlock()),
                                ("summary", blocks.RichTextBlock())])
        v = demo.build(b, "x", real=False)[0]
        self.assertEqual(v["heading"].source.count("<p>"), 1)
        self.assertNotIn("Replace", v["heading"].source)   # a heading is a few words
        self.assertEqual(v["body"].source.count("<p>"), 2)
        self.assertEqual(v["summary"].source.count("<p>"), 1)

    def test_list_sizes(self):
        child = blocks.StructBlock([("title", blocks.CharBlock())])
        cases = [(blocks.ListBlock(child), 3), (blocks.ListBlock(child, min_num=1), 3),
                 (blocks.ListBlock(child, min_num=5), 5), (blocks.ListBlock(child, max_num=2), 2)]
        for lb, n in cases:
            v = demo.build(blocks.StructBlock([("items", lb)]), "x", real=False)[0]["items"]
            self.assertEqual(len(v), n)
            titles = [item["title"] for item in v]
            self.assertEqual(len(set(titles)), len(titles))   # no repeats

    def test_one_consistent_link(self):
        from prblm_builder.blocks import LinkBlock
        b = blocks.StructBlock([("button", LinkBlock())])
        link = demo.build(b, "x", real=False)[0]["button"]
        kind = link["link_type"]
        fields = {"page", "url", "anchor", "document", "email", "phone"}
        target = {"url": "url"}.get(kind, kind)
        self.assertTrue(link[target])
        self.assertFalse(any(link[f] for f in fields - {target}))
        self.assertEqual(link["label"], "Button label")

    def test_default_is_used(self):
        b = blocks.StructBlock([("align", blocks.ChoiceBlock(choices=[("l", "L"), ("c", "C")], default="c")),
                                ("count", blocks.IntegerBlock(default=7))])
        v = demo.build(b, "x", real=False)[0]
        self.assertEqual((v["align"], v["count"]), ("c", 7))

    def test_image_roles_and_shapes(self):
        wide = {"w": 1600, "h": 900, "vector": False, "alpha": False}
        logo_png = {"w": 1600, "h": 900, "vector": False, "alpha": True}
        svg = {"w": 100, "h": 100, "vector": True, "alpha": False}
        self.assertTrue(demo._fits(wide, "wide"))
        self.assertFalse(demo._fits(svg, "wide"))
        self.assertFalse(demo._fits(logo_png, "wide"))       # transparent: not a banner
        self.assertTrue(demo._fits(svg, "square"))
        self.assertFalse(demo._fits(wide, "square"))
        role = lambda n: demo._image_role(ImageChooserBlock(), n)  # noqa: E731
        self.assertEqual((role("hero_background"), role("logo"), role("photo")), ("wide", "square", "photo"))

    @override_settings(STORAGES=STORAGES)
    def test_role_placeholder_image_in_its_collection(self):
        img = demo.placeholder_image("wide")
        self.assertEqual((img.width, img.height), (1600, 900))
        self.assertEqual(img.collection.name, demo.PLACEHOLDER_COLLECTION)
        self.assertEqual(demo.placeholder_image("wide").pk, img.pk)    # reused

    @override_settings(PRBLM_BUILDER_PLACEHOLDER_IMAGES=False)
    def test_no_placeholder_when_off(self):
        self.assertIsNone(demo.placeholder_image("square"))


# --------------------------------------------------------------------------- B
@override_settings(STORAGES=STORAGES, PRBLM_BUILDER_PREVIEW_CSS=["css/global.css"],
                   PRBLM_BUILDER_PREVIEW_SITES={"shop.example.com": {"css": ["shop/main.css"],
                                                                     "body_class": "shop"}})
class PerSitePreviewTests(TestCase):
    def setUp(self):
        self.shop = Site.objects.create(hostname="shop.example.com", root_page=home(), site_name="Shop")

    def test_config_falls_back_to_global(self):
        self.assertEqual(sites.config(site=Site.objects.get(is_default_site=True))["css"], ["css/global.css"])

    def test_site_entry_overrides(self):
        conf = sites.config(site=self.shop)
        self.assertEqual((conf["css"], conf["body_class"]), (["shop/main.css"], "shop"))
        self.assertEqual(conf["js"], [])                      # not set → global

    def test_frame_uses_the_sites_css(self):
        html = previews.frame("<p>x</p>", None, site=self.shop)
        self.assertIn('href="/static/shop/main.css"', html)
        self.assertNotIn("global.css", html)

    def test_library_has_a_site_switcher(self):
        self.client.force_login(get_user_model().objects.create_superuser("ps", "ps@example.com", "pw"))
        html = self.client.get(reverse("prblm_builder:demo") + "?site=shop.example.com").content.decode()
        self.assertIn('aria-label="Preview as site"', html)       # tabs (few sites)
        self.assertIn('href="?site=shop.example.com" aria-current="page"', html)
        self.assertIn("site=shop.example.com\"", html)


@override_settings(STORAGES=STORAGES, PRBLM_BUILDER_PREVIEW_TEMPLATE="testapp/preview_shell.html")
class PreviewTemplateTests(TestCase):
    def test_section_rendered_inside_the_sites_template(self):
        html = previews.frame('<section loading="lazy">Hi</section>', None)
        self.assertIn('<body x-data="{ open: false }">', html)
        self.assertIn(previews.SECTION_START + "<section", html)
        self.assertIn("</section>" + previews.SECTION_END, html)
        self.assertNotIn('loading="lazy"', html)


class AssetEntryTests(TestCase):
    def test_css_entries(self):
        html = previews.css_tags(["css/a.css", {"href": "https://cdn.x/b.css", "integrity": "sha-1",
                                                "crossorigin": "anonymous"}, {"inline": "p{color:red}"}])
        self.assertIn('<link rel="stylesheet" href="/static/css/a.css">', html)
        self.assertIn('href="https://cdn.x/b.css" integrity="sha-1" crossorigin="anonymous"', html)
        self.assertIn("<style>p{color:red}</style>", html)

    def test_js_entries_keep_order_and_options(self):
        html = previews.js_tags([{"inline": "window.X = 1"}, {"src": "js/app.js", "type": "module"},
                                 {"src": "js/alpine.js", "defer": True}, {"importmap": {"imports": {}}}])
        self.assertLess(html.index("window.X"), html.index("app.js"))
        self.assertIn('<script src="/static/js/app.js" type="module"></script>', html)
        self.assertIn('<script src="/static/js/alpine.js" defer></script>', html)
        self.assertIn('<script type="importmap">', html)


class NewSettingsTests(TestCase):
    def test_defaults(self):
        self.assertEqual((cfg.canvas_height(), cfg.preview_sites(), cfg.preview_template()), (900, {}, ""))

    @override_settings(PRBLM_BUILDER_CANVAS_HEIGHT="oops")
    def test_bad_canvas_height(self):
        self.assertEqual(cfg.canvas_height(), 900)

    @override_settings(PRBLM_BUILDER_CANVAS_HEIGHT=100)
    def test_canvas_height_minimum(self):
        self.assertEqual(cfg.canvas_height(), 300)


# --------------------------------------------------------------------------- E1
class SettingsPanelTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("sp", "sp@example.com", "pw"))

    def schema(self):
        b = blocks.StructBlock([
            ("size", blocks.IntegerBlock(min_value=1, max_value=4, required=False)),
            ("align", blocks.ChoiceBlock(choices=[("l", "L"), ("c", "C")], default="c", required=False)),
        ], builder_settings=["size", "align"])
        return b, {f["name"]: f for f in registry.settings_schema(b)}

    def test_number_and_default_choice(self):
        _b, f = self.schema()
        self.assertEqual((f["size"]["kind"], f["size"]["min"], f["size"]["max"], f["size"]["step"]),
                         ("number", 1.0, 4.0, "1"))
        self.assertTrue(f["align"]["required"])            # has a default → no empty choice

    def test_check_setting(self):
        b, _f = self.schema()
        self.assertIsNone(registry.check_setting(b, "size", "3"))
        self.assertIn("4", registry.check_setting(b, "size", "9"))

    def test_check_endpoint(self):
        url = reverse("prblm_builder:check_setting") + "?model=examples.ArticlePage&block=promo&name=anchor_id"
        self.assertEqual(self.client.get(url + "&value=pricing").json(), {"ok": True, "error": ""})


# --------------------------------------------------------------------------- A4 / A6 / E2 / wiring
@override_settings(STORAGES=STORAGES)
class BuilderPageAndChromeTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("bp", "bp@example.com", "pw"))

    def builder_page(self, **kw):
        from prblm_builder.blocks.models import BuilderPage
        page = home().add_child(instance=BuilderPage(title="B", slug="b-" + uuid.uuid4().hex[:5], body="[]", **kw))
        page.save_revision().publish()
        return page

    def test_fixed_header_offset(self):
        html = self.client.get(self.builder_page().url).content.decode()
        self.assertIn('class="prblm-header-slot"', html)
        self.assertIn("padding-top:var(--prblm-header-offset,0px)", html)

    @override_settings(PRBLM_BUILDER_HEADER_TEMPLATE="testapp/empty.html")
    def test_empty_header_takes_no_frame(self):
        page = self.builder_page(header_choice="site")
        html = self.client.get(reverse("prblm_builder:builder", args=[page.id]) + "?embed=1").content.decode()
        self.assertIn('data-chrome="header" data-chrome-base', html)
        self.assertIn('data-src="" scrolling="no" title="Site header"', html)

    def test_placeholder_title_warning_on_publish(self):
        from django.contrib.messages import get_messages
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage
        from prblm_builder.wagtail_hooks import warn_placeholder_title
        request = RequestFactory().get("/")
        request.session = {}
        request._messages = FallbackStorage(request)
        warn_placeholder_title(request, Page(title="Untitled page 12"))
        warn_placeholder_title(request, Page(title="About us"))
        self.assertEqual(len(list(get_messages(request))), 1)

    def test_library_usage_and_filter(self):
        html = self.client.get(reverse("prblm_builder:demo")).content.decode()
        self.assertIn('data-filter="unused"', html)
        self.assertIn('data-used="0"', html)


class WiringTests(TestCase):
    def test_canvas_js(self):
        js = (STATIC / "builder.js").read_text()
        self.assertIn("dragSig", js)                               # A3: drop in place isn't a change
        self.assertIn("CANVAS_H", js)                              # A5: vh viewport
        self.assertIn("pb-chrome-empty", js)                       # A6
        self.assertIn("d.fonts.ready", js)                         # A7
        frames = (STATIC / "frames.js").read_text()
        self.assertIn('cs.position === "fixed"', frames)           # A4a
        self.assertIn("data-prblm-start", frames)                  # B2 markers

    def test_two_column_breakpoint(self):
        self.assertIn("max-width: 719px", (STATIC / "form-columns.css").read_text())
