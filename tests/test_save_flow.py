"""v0.4 Phase 1: the Layout tab's save banner, placeholder title and keeping the
arrangement after a failed save."""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.models import Page

from tests.testapp.models import StandardPage

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=STORAGES)
class SaveFlowTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("sf", "sf@example.com", "pw"))
        self.home = Page.objects.get(depth=2)
        self.add_url = reverse("wagtailadmin_pages:add", args=["testapp", "standardpage", self.home.pk])

    def test_banner_and_placeholder_title_on_new_page(self):
        r = self.client.get(self.add_url)
        self.assertContains(r, "prblm-save-banner")
        self.assertContains(r, "data-pb-save-now")
        self.assertContains(r, f'data-placeholder-title="Untitled page {Page.objects.count() + 1}"')
        self.assertNotContains(r, 'id="pb-restore"')

    def _post(self, title):
        layout = [{"type": "heading", "id": "n1", "new": True},
                  {"type": "rich_text", "id": "n2", "new": True}]
        data = {"title": title, "slug": "untitled-x" if title else "", "body-count": "0",
                "_pb_layout": json.dumps(layout), "_pb_initial": "[]"}
        return self.client.post(self.add_url, data), layout

    def test_failed_save_keeps_the_arrangement(self):
        r, layout = self._post(title="")
        self.assertEqual(r.status_code, 200)                 # re-shown with errors
        html = r.content.decode()
        self.assertIn('id="pb-restore"', html)
        self.assertIn("The page wasn", html)
        self.assertIn('name="_pb_layout"', html)             # re-submitted with next save
        restore = json.loads(html.split('id="pb-restore" type="application/json">')[1].split("</script>")[0])
        self.assertEqual(json.loads(restore["layout"]), layout)

    def test_save_with_placeholder_title_creates_sections(self):
        r, _layout = self._post(title="Untitled page 9")
        self.assertEqual(r.status_code, 302)
        page = StandardPage.objects.get(title="Untitled page 9")
        body = page.get_latest_revision_as_object().body
        self.assertEqual([b.block_type for b in body], ["heading", "rich_text"])

    def test_builder_js_signals_changes(self):
        from django.contrib.staticfiles import finders
        js = open(finders.find("prblm_builder/builder.js")).read()
        self.assertIn("prblm-builder:dirty", js)
        self.assertIn("pb-restore", js)


@override_settings(STORAGES=STORAGES)
class FoldTests(TestCase):
    """v0.4 Phase 2: foldable kinds/groups in the palette and the Block library."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("fd", "fd@example.com", "pw"))

    def test_library_has_fold_controls_matching_sidebar_and_main(self):
        r = self.client.get(reverse("prblm_builder:demo"))
        html = r.content.decode()
        self.assertIn('data-fold-store="library"', html)
        self.assertIn("prblm_builder/fold.js", html)
        for kind in r.context["kinds"]:
            # one button in the sidebar + one in the preview column, same key
            self.assertEqual(html.count(f'data-fold="{kind["key"]}"'), 2)
            self.assertEqual(html.count(f'data-fold-body="{kind["key"]}"'), 2)
            for group in kind["groups"]:
                self.assertEqual(html.count(f'data-fold="{group["key"]}"'), 2)

    def test_palette_kinds_and_groups(self):
        from tests.testapp.models import BlocksPage
        page = Page.objects.get(depth=2).add_child(instance=BlocksPage(title="Fold", slug="fold-x"))
        r = self.client.get(reverse("prblm_builder:builder", args=[page.id]) + "?embed=1")
        self.assertTrue(r.context["show_kinds"])
        self.assertEqual([k["key"] for k in r.context["palette"]], ["builtin", "site"])
        self.assertContains(r, 'data-fold="builtin:page-openers"')
        self.assertContains(r, 'class="pb-pgroup-items" data-fold-body="builtin:page-openers"')
        self.assertContains(r, 'data-fold-store="palette"')
