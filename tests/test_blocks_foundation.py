"""Phase 2: the built-in blocks foundation — assets, theme, icons, images, links,
admin wiring. Individual blocks are tested in test_blocks.py."""
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from wagtail.models import Page, Site

from prblm_builder import previews, registry
from prblm_builder.blocks import theme
from prblm_builder.blocks.models import ThemeSettings
from prblm_builder.blocks.sections.base import AnchorBlock, BackgroundBlock, LinkBlock

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def render(src, **ctx):
    return Template("{% load prblm_blocks %}" + src).render(Context(ctx))


@override_settings(STORAGES=STORAGES)
class AssetsTests(TestCase):
    def test_assets_once_per_request(self):
        request = RequestFactory().get("/")
        first = render("{% prblm_assets %}", request=request)
        second = render("{% prblm_assets %}", request=request)
        self.assertIn("prblm_builder/blocks/blocks.css", first)
        self.assertIn("prblm_builder/blocks/blocks.js", first)
        self.assertIn("--pbk-c-brand:#2563eb", first)
        self.assertEqual(second, "")

    def test_assets_without_request_still_render(self):
        self.assertIn("blocks.css", render("{% prblm_assets %}"))

    def test_theme_settings_change_css(self):
        site = Site.objects.get(is_default_site=True)
        ThemeSettings.objects.update_or_create(
            site=site, defaults={"brand_color": "#ff0055", "radius": "large",
                                 "font_family": "Inter, sans-serif"})
        out = theme.css(theme.values_for())
        self.assertIn("--pbk-c-brand:#ff0055", out)
        self.assertIn("--pbk-radius:20px", out)
        self.assertIn("--pbk-font:Inter, sans-serif", out)

    def test_theme_css_rejects_unsafe_values(self):
        out = theme.css({**theme.DEFAULTS, "brand_color": "red;}</style><script>",
                         "font_family": "x;}</style>{"})
        self.assertIn("--pbk-c-brand:#2563eb", out)      # bad colour → default
        self.assertNotIn("<", out)
        self.assertNotIn("}</style", out)


class IconAndImageTests(TestCase):
    def test_icon(self):
        out = render('{% pbk_icon "phone" %}')
        self.assertTrue(out.startswith("<svg"))
        self.assertIn('aria-hidden="true"', out)
        self.assertEqual(render('{% pbk_icon "no-such-icon" %}'), "")

    def test_image_placeholder_when_empty(self):
        out = render('{% pbk_image None "fill-1600x900" "Hero image" %}')
        self.assertIn("pbk-ph", out)
        self.assertIn("Hero image · 1600×900", out)
        self.assertIn('role="img"', out)

    def test_image_renders_rendition(self):
        from django.core.files.images import ImageFile
        from io import BytesIO
        from PIL import Image as PILImage
        from wagtail.images import get_image_model
        buf = BytesIO()
        PILImage.new("RGB", (400, 300), (10, 20, 30)).save(buf, "PNG")
        img = get_image_model()(title="Test photo")
        img.file.save("t.png", ImageFile(buf, name="t.png"), save=False)
        img.save()
        out = render('{% pbk_image img "fill-200x100" "Photo" %}', img=img)
        self.assertIn("<img", out)
        self.assertIn('width="200"', out)
        self.assertIn('alt="Test photo"', out)


class SharedBlockTests(TestCase):
    def test_link_href_url_and_page(self):
        block = LinkBlock()
        v = block.to_python({"label": "Go", "page": None, "url": "#pricing"})
        self.assertEqual(v.href, "#pricing")
        page = Page.objects.get(depth=2)
        v = block.to_python({"label": "Home", "page": page.pk, "url": "/ignored/"})
        self.assertEqual(v.href, page.url)
        self.assertFalse(v.is_external)

    def test_anchor_validation(self):
        block = AnchorBlock()
        self.assertEqual(block.clean("pricing-table"), "pricing-table")
        with self.assertRaises(ValidationError):
            block.clean("1 bad id")

    def test_background_default(self):
        self.assertEqual(BackgroundBlock().get_default(), "light")
        self.assertEqual(BackgroundBlock(default="brand").get_default(), "brand")

    def test_builtin_detection_and_demo_uses_defaults(self):
        block = LinkBlock(default={"label": "Read more", "url": "#more"})
        self.assertTrue(registry.is_builtin(block))
        value = previews.demo_value(block, "link")
        self.assertEqual(value["label"], "Read more")

    def test_builder_blocks_rejects_unknown_names(self):
        from prblm_builder.blocks import builder_blocks
        with self.assertRaises(ValueError):
            builder_blocks(exclude=["nope"])


@override_settings(STORAGES=STORAGES)
class AdminTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("theme-admin", "t@example.com", "pw")
        self.client.force_login(self.admin)

    def test_theme_in_page_builder_menu_not_settings(self):
        html = self.client.get(reverse("wagtailadmin_home")).content.decode()
        self.assertIn('"prblm-builder-theme-page"', html)     # in Page builder
        self.assertNotIn('"prblm-builder-theme"', html)       # not in Settings

    def test_theme_edit_page_saves(self):
        site = Site.objects.get(is_default_site=True)
        url = reverse("wagtailsettings:edit", args=["prblm_builder_blocks", "themesettings", site.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        data = {**theme.DEFAULTS, "brand_color": "#123456"}
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(ThemeSettings.for_site(site).brand_color, "#123456")

    def test_requirements_check(self):
        from prblm_builder.blocks.checks import requirements
        self.assertEqual(requirements(None), [])
        with mock.patch("prblm_builder.blocks.checks.apps.is_installed", return_value=False):
            ids = {e.id for e in requirements(None)}
        self.assertEqual(ids, {"prblm_builder_blocks.E001", "prblm_builder_blocks.E002"})
