"""Integration tests for the page builder, run against whatever builder-enabled
page model the project provides. In this repo that's ``tests.testapp.StandardPage``
(run ``python runtests.py``); inside a host site, ``manage.py test prblm_builder``.
The page model's StreamField needs a ``rich_text`` block."""
import json
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.models import Page

from prblm_builder import registry


def _enabled_model():
    """The first builder-enabled page model whose StreamField has a ``rich_text`` block
    (the tests build content with it)."""
    for model in registry.enabled_page_models():
        _field, stream_block = registry.stream_block_for(model)
        if stream_block is not None and "rich_text" in stream_block.child_blocks:
            return model
    return None


# Tests render templates with {% static %}; use plain static storage so they don't
# require a collectstatic run (production collects assets at deploy time).
@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class BuilderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.model = _enabled_model()
        cls.parent = Page.objects.filter(depth=2).first() or Page.objects.get(depth=1)
        User = get_user_model()
        cls.admin = User.objects.create_superuser("pb-admin", "pb@example.com", "pw")
        if cls.model:
            cls.field = registry.target_field_name(cls.model)
            page = cls.model(title="Builder test", slug="builder-test-%s" % uuid.uuid4().hex[:6], live=False)
            setattr(page, cls.field, json.dumps([
                {"type": "rich_text", "value": "<p>ALPHA</p>", "id": "a1"},
                {"type": "rich_text", "value": "<p>BETA</p>", "id": "b2"},
            ]))
            cls.parent.add_child(instance=page)
            page.save_revision()
            cls.page = page

    def setUp(self):
        if not self.model:
            self.skipTest("no builder-enabled page model in this project")
        self.client.force_login(self.admin)

    def test_enabled_models_discovered(self):
        self.assertTrue(registry.enabled_page_models())

    def test_builder_page_renders(self):
        r = self.client.get(reverse("prblm_builder:builder", args=[self.page.id]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "pb-canvas")
        self.assertContains(r, "pb-pitem")  # palette has blocks

    def test_autoenable_adds_layout_tab(self):
        """The plugin injects a Layout tab + save wiring into enabled page models."""
        from prblm_builder.forms import LayoutBuilderForm
        headings = [getattr(c, "heading", "") for c in self.model.get_edit_handler().children]
        self.assertIn("Layout", headings)
        self.assertTrue(issubclass(self.model.base_form_class, LayoutBuilderForm))

    def test_builder_new_renders_for_a_model(self):
        """A brand-new (unsaved) page can be laid out via the model-scoped builder."""
        label = f"{self.model._meta.app_label}.{self.model.__name__}"
        r = self.client.get(reverse("prblm_builder:builder_new") + f"?model={label}")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "pb-pitem")   # palette present
        self.assertContains(r, f"model={label}")  # scoped to the model, no page id

    def test_preview_demo_and_real(self):
        base = reverse("prblm_builder:preview")
        self.assertEqual(self.client.get(f"{base}?page={self.page.id}&block=rich_text&demo=1").status_code, 200)
        sid = getattr(self.page, self.field)[0].id
        self.assertEqual(self.client.get(f"{base}?page={self.page.id}&section={sid}&block=rich_text").status_code, 200)

    def test_block_library_and_every_block_preview(self):
        """The Block library renders, and every block gets a demo preview (synthesised
        content, incl. placeholder images) without erroring."""
        r = self.client.get(reverse("prblm_builder:demo"))
        self.assertEqual(r.status_code, 200)
        skipped = {b["name"] for b in r.context["unpreviewable"]}  # listed separately
        base = reverse("prblm_builder:preview")
        for _group, items in registry.grouped_all_blocks():
            for name, _block, _label in items:
                if name in skipped:
                    continue
                r = self.client.get(f"{base}?block={name}")
                self.assertEqual(r.status_code, 200, name)
                self.assertNotContains(r, "Preview unavailable", msg_prefix=name)

    def test_preview_bad_params_are_404(self):
        base = reverse("prblm_builder:preview")
        for qs in ("model=nodot&block=rich_text", "model=no.Such&block=rich_text",
                   "page=abc&block=rich_text", "block=no_such_block"):
            self.assertEqual(self.client.get(f"{base}?{qs}").status_code, 404, qs)

    def test_preview_of_page_needs_edit_permission(self):
        User = get_user_model()
        nobody = User.objects.create_user("pb-nobody", "n@example.com", "pw")
        self.client.force_login(nobody)
        sid = getattr(self.page, self.field)[0].id
        r = self.client.get(reverse("prblm_builder:preview") + f"?page={self.page.id}&section={sid}")
        self.assertNotEqual(r.status_code, 200)

    def test_reorder_preserves_content(self):
        url = reverse("prblm_builder:save", args=[self.page.id])
        r = self.client.post(url, data=json.dumps({"sections": [
            {"type": "rich_text", "id": "b2"}, {"type": "rich_text", "id": "a1"}]}),
            content_type="application/json")
        self.assertTrue(r.json()["ok"])
        body = self.page.__class__.objects.get(id=self.page.id).get_latest_revision_as_object()
        body = getattr(body, self.field)
        self.assertIn("BETA", str(body[0].value))
        self.assertIn("ALPHA", str(body[1].value))

    def test_add_block_and_publish(self):
        url = reverse("prblm_builder:save", args=[self.page.id])
        r = self.client.post(url, data=json.dumps({"sections": [
            {"type": "rich_text", "id": "a1"},
            {"type": "rich_text", "id": str(uuid.uuid4()), "new": True}],
            "publish": True}), content_type="application/json")
        self.assertTrue(r.json()["published"])
        live = self.page.__class__.objects.get(id=self.page.id)
        self.assertTrue(live.live)
        self.assertEqual(len(getattr(live, self.field)), 2)


class ReconcileTests(TestCase):
    """Unit-test the Layout-tab reconciler — the part that could lose content if
    wrong (dropping or resurrecting blocks). No HTTP, just the pure function."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        model = _enabled_model()
        cls.model = model
        if model:
            cls.field, cls.sb = registry.stream_block_for(model)

    def setUp(self):
        if not self.model:
            self.skipTest("no builder-enabled page model in this project")

    def _raw(self, *ids):
        return [{"type": "rich_text", "value": "<p>%s</p>" % i, "id": i} for i in ids]

    def _reconcile(self, current, layout, initial):
        from prblm_builder.layout import reconcile
        return reconcile(self.sb, current, layout, initial)

    def test_reorder_keeps_content(self):
        out = self._reconcile(self._raw("a", "b"),
                              [{"type": "rich_text", "id": "b"}, {"type": "rich_text", "id": "a"}],
                              ["a", "b"])
        self.assertEqual([d["id"] for d in out], ["b", "a"])
        self.assertIn("a", out[1]["value"])  # content preserved, not reset

    def test_layout_delete_drops_block(self):
        out = self._reconcile(self._raw("a", "b"),
                              [{"type": "rich_text", "id": "a"}], ["a", "b"])
        self.assertEqual([d["id"] for d in out], ["a"])

    def test_new_block_seeded_not_dropped(self):
        out = self._reconcile(self._raw("a"),
                              [{"type": "rich_text", "id": "a"},
                               {"type": "rich_text", "id": "new1", "new": True}], ["a"])
        self.assertEqual([d["id"] for d in out], ["a", "new1"])

    def test_native_add_is_kept(self):
        # 'x' was added in the Content tab after the Layout tab loaded (not in initial)
        # and the layout doesn't mention it → it must survive, not be dropped.
        out = self._reconcile(self._raw("a", "x"),
                              [{"type": "rich_text", "id": "a"}], ["a"])
        self.assertIn("x", [d["id"] for d in out])

    def test_native_delete_not_resurrected(self):
        # 'b' was deleted in the Content tab (gone from content) but is still listed in
        # a stale layout as an existing block → it must stay gone, not come back.
        out = self._reconcile(self._raw("a"),
                              [{"type": "rich_text", "id": "a"}, {"type": "rich_text", "id": "b"}],
                              ["a", "b"])
        self.assertEqual([d["id"] for d in out], ["a"])

    def test_absent_layout_is_noop_upstream(self):
        # No layout fields → the form leaves body untouched (tested here as: an empty
        # layout list drops everything, which is why the form guards on presence).
        self.assertEqual(self._reconcile(self._raw("a"), [], ["a"]), [])
