"""0.10: in-page publish question, padding bands, Content-tab cover, tab kept after save,
"Fill them in" hint. (The behaviour itself is browser-checked; these guard the wiring.)"""
import json
import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from wagtail.models import Page

from tests.testapp.models import StandardPage

STATIC = Path(__file__).resolve().parent.parent / "prblm_builder" / "static" / "prblm_builder"


class EditorWiringTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("v10", "v10@example.com", "pw"))
        body = json.dumps([{"type": "heading", "value": "Hi", "id": str(uuid.uuid4())}])
        self.page = Page.objects.get(depth=2).add_child(instance=StandardPage(title="T", slug="t10", body=body))

    def test_publish_question_is_in_the_page(self):
        html = self.client.get(reverse("wagtailadmin_pages:edit", args=[self.page.pk])).content.decode()
        self.assertIn("prblm-publish-ask", html)
        self.assertIn("Publish anyway", html)
        self.assertNotIn("window.confirm(", html)       # a browser can silently block it
        self.assertIn("showModal()", html)              # centred, blocks the page behind

    def test_tab_memory_and_content_cover(self):
        html = self.client.get(reverse("wagtailadmin_pages:edit", args=[self.page.pk])).content.decode()
        self.assertIn('"prblm-builder:tab"', html)
        self.assertIn("history.replaceState", html)
        self.assertIn("prblm-tab-cover", html)

    def test_content_tab_changes_update_the_canvas(self):
        html = self.client.get(reverse("wagtailadmin_pages:edit", args=[self.page.pk])).content.decode()
        self.assertIn("function formSig", html)          # what the Content tab changed
        self.assertIn("function rebuildCanvas", html)    # auto-save: rebuild from the draft
        self.assertIn("You changed the page in the Content tab", html)   # no auto-save

    def test_fill_hint_on_saved_pages_only(self):
        html = self.client.get(reverse("prblm_builder:builder", args=[self.page.pk]) + "?embed=1").content.decode()
        self.assertIn('id="pb-fill-hint"', html)
        html = self.client.get(reverse("prblm_builder:builder_new") + "?model=testapp.StandardPage&embed=1").content.decode()
        self.assertNotIn('id="pb-fill-hint"', html)


class CanvasTests(TestCase):
    def test_padding_bands(self):
        self.assertIn("pad: pad", (STATIC / "frames.js").read_text())
        js = (STATIC / "builder.js").read_text()
        self.assertIn('band(sec, "pad"', js)
        self.assertIn("function updateFillHint", js)
        self.assertIn(".pb-space-pad", (STATIC / "builder.css").read_text())


class DemoContentFreshnessTests(TestCase):
    """Real content for demos is rebuilt when published content changes — not on a timer."""

    def setUp(self):
        from unittest import mock

        from prblm_builder import demo
        self.demo = demo
        demo.reset_caches()
        patcher = mock.patch.object(demo, "STAMP_EVERY", 0)     # check on every call
        patcher.start()
        self.addCleanup(patcher.stop)

    def page(self, slug, text):
        body = json.dumps([{"type": "heading", "value": text, "id": str(uuid.uuid4())}])
        page = Page.objects.get(depth=2).add_child(instance=StandardPage(title=slug, slug=slug, body=body))
        page.save_revision().publish()
        return page

    def used_on(self):
        from tests.testapp.models import StandardPage as SP
        from prblm_builder import registry
        _f, sb = registry.stream_block_for(SP)
        return {p.slug for p in self.demo.usage("heading", sb.child_blocks["heading"])}

    def test_nothing_rebuilt_while_nothing_changes(self):
        self.page("one", "First")
        first = self.demo._index()
        self.assertIs(self.demo._index(), first)

    def test_publish_shows_at_once(self):
        self.page("one", "First")
        self.assertEqual(self.used_on(), {"one"})
        self.page("two", "Second")                         # no reset_caches, no waiting
        self.assertEqual(self.used_on(), {"one", "two"})

    def test_drafts_dont_rebuild_and_unpublish_removes(self):
        page = self.page("one", "First")
        first = self.demo._index()
        page.title = "Draft change"
        page.save_revision()                               # a draft: demo content ignores it
        self.assertIs(self.demo._index(), first)
        page.unpublish()
        self.assertEqual(self.used_on(), set())
