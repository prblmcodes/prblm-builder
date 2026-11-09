"""v0.5: preview values, descriptions, link block, section settings, page options."""
import json
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.models import Page

from prblm_builder import previews, registry
from prblm_builder.layout import reconcile
from tests.testapp.models import StandardPage

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def stream():
    return registry.stream_block_for(StandardPage)[1]


@override_settings(STORAGES=STORAGES)
class PreviewValueTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("pv", "pv@example.com", "pw"))

    def test_explicit_preview_value_only_when_set(self):
        sb = stream()
        self.assertEqual(previews.explicit_preview_value(sb.child_blocks["promo"])["title"],
                         "Preview promo title")
        self.assertIsNone(previews.explicit_preview_value(sb.child_blocks["heading"]))

    def test_preview_value_used_for_new_sections_and_previews(self):
        sb = stream()
        seeded = reconcile(sb, [], [{"type": "promo", "id": "p1", "new": True}], [])
        self.assertEqual(seeded[0]["value"]["title"], "Preview promo title")
        r = self.client.get(reverse("prblm_builder:preview") + "?block=promo&demo=1")
        self.assertContains(r, "Preview promo title")

    def test_preview_value_beats_real_site_content(self):
        page = StandardPage(title="Real", slug="real-" + uuid.uuid4().hex[:5])
        page.body = json.dumps([{"type": "promo", "value": {"title": "Real site promo", "text": ""}, "id": "r1"}])
        Page.objects.get(depth=1).add_child(instance=page)
        previews._INDEX["data"] = None
        self.assertEqual(previews.demo_value(stream().child_blocks["promo"], "promo")["title"],
                         "Preview promo title")

    def test_seeded_preview_value_counts_as_unedited(self):
        sb = stream()
        seeded = reconcile(sb, [], [{"type": "promo", "id": "p1", "new": True}], [])
        self.assertTrue(previews.is_unedited(sb.child_blocks["promo"], "promo", seeded[0]["value"]))

    def test_descriptions_in_library_and_palette(self):
        r = self.client.get(reverse("prblm_builder:demo"))
        self.assertContains(r, "A promo band with a title and text.")
        self.assertContains(r, "Big page opener")                     # built-in description
        page = Page.objects.get(depth=1).add_child(
            instance=StandardPage(title="D", slug="d-" + uuid.uuid4().hex[:5]))
        r = self.client.get(reverse("prblm_builder:builder", args=[page.id]) + "?embed=1")
        self.assertContains(r, 'title="A promo band with a title and text. — Drag onto the page')
