"""v0.4 Phase 4: where Builder pages can be added, and the site's own blocks on them."""
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail import blocks
from wagtail.models import Page

from prblm_builder import registry
from prblm_builder.blocks import builder_blocks
from prblm_builder.blocks.fields import BuilderBodyField, body_blocks, extra_blocks
from prblm_builder.blocks.models import BuilderPage
from tests.testapp.models import RestrictedHome, StandardPage

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


class PageParentsTests(TestCase):
    def test_builder_page_allowed_under_listed_parent(self):
        self.assertIn(BuilderPage, RestrictedHome.clean_subpage_models())
        self.assertIn(StandardPage, RestrictedHome.clean_subpage_models())   # own rules kept
        home = Page.objects.get(depth=2).add_child(instance=RestrictedHome(title="RH", slug="rh"))
        self.assertIn(BuilderPage, home.specific.creatable_subpage_models())

    def test_unrestricted_parents_untouched(self):
        self.assertIsNone(getattr(StandardPage, "subpage_types", None))

    def test_unknown_parent_warns(self):
        from prblm_builder.blocks.checks import page_parents
        with override_settings(PRBLM_BUILDER_PAGE_PARENTS=["nope.Missing", "testapp.RestrictedHome"]):
            ids = [w.id for w in page_parents(None)]
        self.assertEqual(ids, ["prblm_builder_blocks.W001"])


@override_settings(STORAGES=STORAGES)
class ExtraBlocksTests(TestCase):
    def test_builder_page_has_site_block(self):
        _f, sb = registry.stream_block_for(BuilderPage)
        self.assertIn("note", sb.child_blocks)
        self.assertEqual(len(sb.child_blocks), len(builder_blocks()) + 1)
        kinds = {k: [n for _g, items in groups for (n, _b, _l) in items]
                 for k, groups in registry.palette_sections(sb)}
        self.assertEqual(kinds[registry.KIND_SITE], ["note"])        # shown as a site block

    def test_no_migration_inside_the_plugin(self):
        out = StringIO()
        call_command("makemigrations", "prblm_builder_blocks", "--check", "--dry-run", stdout=out)
        self.assertIn("No changes detected", out.getvalue())

    def test_field_describes_itself_as_builtins_only(self):
        field = BuilderPage._meta.get_field("body")
        _name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "wagtail.fields.StreamField")
        plain = BuilderBodyField(builder_blocks(), blank=True)
        self.assertEqual((args, kwargs), plain.deconstruct()[2:])

    def test_setting_forms_and_errors(self):
        self.assertEqual(extra_blocks(None), [])
        [(name, block)] = extra_blocks([("note", "tests.testapp.blocks.NoteBlock")])
        self.assertIsInstance(block, blocks.CharBlock)
        with self.assertRaises(ImproperlyConfigured):
            extra_blocks([("x", "no.such.Block")])
        with self.assertRaises(ImproperlyConfigured):
            extra_blocks(["just-a-string-entry"])
        with self.assertRaises(ImproperlyConfigured):
            body_blocks(builder_blocks(), [("hero", "tests.testapp.blocks.NoteBlock")])

    def test_layout_palette_offers_site_block(self):
        admin = get_user_model().objects.create_superuser("po", "po@example.com", "pw")
        self.client.force_login(admin)
        page = Page.objects.get(depth=2).add_child(instance=BuilderPage(title="BP", slug="bp-po"))
        r = self.client.get(reverse("prblm_builder:builder", args=[page.id]) + "?embed=1")
        self.assertContains(r, 'data-type="note"')
        self.assertContains(r, "Your site&#x27;s blocks")
