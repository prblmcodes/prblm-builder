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


class LinkBlockTests(TestCase):
    def link(self, **value):
        from prblm_builder.blocks.sections.base import LinkBlock
        block = LinkBlock()
        return block, block.to_python({"label": "Go", **value})

    def test_href_per_type(self):
        page = Page.objects.get(depth=2)
        cases = [
            ({"link_type": "page", "page": page.pk}, page.url),
            ({"link_type": "url", "url": "https://example.com"}, "https://example.com"),
            ({"link_type": "anchor", "anchor": "#pricing"}, "#pricing"),
            ({"link_type": "anchor", "anchor": "pricing"}, "#pricing"),
            ({"link_type": "email", "email": "a@b.com"}, "mailto:a@b.com"),
            ({"link_type": "phone", "phone": "+44 20 1234-5678"}, "tel:+442012345678"),
        ]
        for value, href in cases:
            with self.subTest(value=value):
                self.assertEqual(self.link(**value)[1].href, href)

    def test_document_link(self):
        from django.core.files.base import ContentFile
        from wagtail.documents import get_document_model
        doc = get_document_model()(title="Brochure")
        doc.file.save("brochure.pdf", ContentFile(b"%PDF-1.4"), save=False)
        doc.save()
        self.assertEqual(self.link(link_type="document", document=doc.pk)[1].href, doc.url)

    def test_links_saved_before_05_still_work(self):
        page = Page.objects.get(depth=2)
        self.assertEqual(self.link(page=page.pk, url="/x/")[1].href, page.url)       # page wins
        self.assertEqual(self.link(url="#contact")[1].href, "#contact")
        self.assertEqual(self.link(url="https://x.org")[1].link_type, "url")

    def test_missing_target_is_an_error_only_with_a_label(self):
        from django.core.exceptions import ValidationError
        block, _v = self.link()
        with self.assertRaises(ValidationError):
            block.clean(block.to_python({"label": "Go", "link_type": "email"}))
        block.clean(block.to_python({"label": "", "link_type": "email"}))         # hidden link: fine

    def test_every_builtin_default_is_valid(self):
        """Editors must be able to save an untouched built-in block."""
        from prblm_builder.blocks import builder_blocks
        for name, block in builder_blocks():
            with self.subTest(block=name):
                block.clean(block.get_default())

    def test_admin_script_registered(self):
        from prblm_builder.blocks.sections.base import LinkBlock
        from wagtail.admin.telepath import JSContext
        ctx = JSContext()
        ctx.pack(LinkBlock())
        self.assertIn("prblm_builder/blocks/link-block.js", str(ctx.media))


@override_settings(STORAGES=STORAGES)
class SectionSettingsTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("ss", "ss@example.com", "pw"))

    def make_page(self, body):
        page = StandardPage(title="S", slug="s-" + uuid.uuid4().hex[:5])
        page.body = json.dumps(body)
        Page.objects.get(depth=1).add_child(instance=page)
        return page

    def test_schema_for_site_block(self):
        fields = registry.settings_schema(stream().child_blocks["banner"])
        self.assertEqual([f["name"] for f in fields], ["tone", "show_border"])   # unknown name skipped
        self.assertEqual(fields[0]["kind"], "choice")
        self.assertFalse(fields[0]["swatches"])
        self.assertEqual(fields[1]["kind"], "boolean")
        self.assertEqual(registry.settings_schema(stream().child_blocks["heading"]), [])

    def test_builtin_schema_has_background_swatches_and_anchor(self):
        from prblm_builder.blocks.sections.heroes import HeroBlock
        fields = {f["name"]: f for f in registry.settings_schema(HeroBlock())}
        self.assertTrue(fields["background"]["swatches"])
        self.assertEqual(fields["anchor_id"]["kind"], "text")

    def test_content_tab_puts_settings_in_collapsed_area(self):
        from prblm_builder.blocks.sections.heroes import HeroBlock
        layout = HeroBlock().meta.form_layout
        self.assertEqual(layout.settings, ["background", "anchor_id"])
        self.assertNotIn("background", layout.children)
        self.assertEqual(stream().child_blocks["banner"].meta.form_layout.settings, ["tone", "show_border"])

    def test_builder_sends_schema_and_current_values(self):
        page = self.make_page([{"type": "banner", "id": "b1",
                                "value": {"title": "Hi", "tone": "loud", "show_border": True}}])
        r = self.client.get(reverse("prblm_builder:builder", args=[page.id]) + "?embed=1")
        self.assertEqual(r.context["sections"][0]["settings"], {"tone": "loud", "show_border": True})
        self.assertIn("banner", r.context["settings_schema"])
        self.assertEqual(r.context["settings_schema"]["banner"]["defaults"]["tone"], "calm")
        self.assertContains(r, 'id="pb-settings-schema"')

    def test_reconcile_applies_only_changed_settings(self):
        current = [{"type": "banner", "id": "b1", "value": {"title": "Edited in Content tab", "tone": "calm", "show_border": False}}]
        out = reconcile(stream(), current, [{"type": "banner", "id": "b1", "settings": {"tone": "loud"}},
                                            {"type": "banner", "id": "n1", "new": True, "settings": {"show_border": True}}], ["b1"])
        self.assertEqual(out[0]["value"], {"title": "Edited in Content tab", "tone": "loud", "show_border": False})
        self.assertTrue(out[1]["value"]["show_border"])
        self.assertEqual(current[0]["value"]["tone"], "calm")                  # input not mutated

    def test_reconcile_ignores_non_settings_fields(self):
        current = [{"type": "banner", "id": "b1", "value": {"title": "Keep", "tone": "calm", "show_border": False}}]
        out = reconcile(stream(), current, [{"type": "banner", "id": "b1", "settings": {"title": "Hacked"}}], ["b1"])
        self.assertEqual(out[0]["value"]["title"], "Keep")

    def test_invalid_setting_is_a_form_error_and_keeps_layout(self):
        from prblm_builder.blocks.models import BuilderPage
        home = Page.objects.get(depth=2)
        url = reverse("wagtailadmin_pages:add", args=["prblm_builder_blocks", "builderpage", home.pk])
        layout = [{"type": "hero", "id": "h1", "new": True, "settings": {"anchor_id": "1 bad id"}}]
        r = self.client.post(url, {"title": "T", "slug": "t-x", "body-count": "0",
                                   "header_choice": "default", "footer_choice": "default",
                                   "_pb_layout": json.dumps(layout), "_pb_initial": "[]"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Section settings: Hero")
        self.assertContains(r, 'id="pb-restore"')
        self.assertFalse(BuilderPage.objects.filter(slug="t-x").exists())

    def test_preview_shows_unsaved_settings(self):
        page = self.make_page([{"type": "banner", "id": "b1", "value": {"title": "Hi", "tone": "calm", "show_border": False}}])
        base = reverse("prblm_builder:preview") + f"?page={page.id}&block=banner&section=b1"
        self.assertContains(self.client.get(base), "tone-calm")
        r = self.client.get(base + "&settings=" + json.dumps({"tone": "loud", "title": "nope"}))
        self.assertContains(r, "tone-loud")
        self.assertNotContains(r, "nope")
        r = self.client.get(base + "&settings=" + json.dumps({"tone": "not-a-choice"}))
        self.assertContains(r, "tone-calm")                                    # invalid → ignored

    def test_changing_settings_keeps_not_edited_badge(self):
        from prblm_builder.blocks.sections.heroes import HeroBlock
        block = HeroBlock()
        value = block.get_prep_value(block.get_default())
        value["background"] = "dark"
        self.assertTrue(previews.is_unedited(block, "hero", value))

    def test_builder_js_has_settings_popover(self):
        from django.contrib.staticfiles import finders
        js = open(finders.find("prblm_builder/builder.js")).read()
        self.assertIn('data-act="settings"', js)
        self.assertIn("&settings=", js)


class CopyPasteTests(TestCase):
    def test_pasted_copy_gets_source_content_and_settings(self):
        current = [{"type": "banner", "id": "b1", "value": {"title": "Original", "tone": "calm", "show_border": False}}]
        layout = [{"type": "banner", "id": "b1"},
                  {"type": "banner", "id": "c1", "copy_from": "b1", "settings": {"tone": "loud"}}]
        out = reconcile(stream(), current, layout, ["b1"])
        self.assertEqual([d["id"] for d in out], ["b1", "c1"])
        self.assertEqual(out[1]["value"]["title"], "Original")
        self.assertEqual(out[1]["value"]["tone"], "loud")
        self.assertEqual(out[0]["value"]["tone"], "calm")

    def test_builder_js_has_copy_paste_and_menu(self):
        from django.contrib.staticfiles import finders
        js = open(finders.find("prblm_builder/builder.js")).read()
        for needle in ('data-act="copy"', '"paste-above"', "contextmenu", "prblm-builder:clip:"):
            self.assertIn(needle, js)


@override_settings(STORAGES=STORAGES)
class PageOptionsTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("po5", "po5@example.com", "pw"))
        from tests.test_site_chrome import set_chrome, header_json
        from prblm_builder.blocks.models import SiteHeader
        set_chrome()
        self.campaign = SiteHeader.objects.create(name="Campaign", content=header_json("Campaign Header"))

    def builder_page(self, **kw):
        from prblm_builder.blocks.models import BuilderPage
        return Page.objects.get(depth=2).add_child(
            instance=BuilderPage(title="BP", slug="bp-" + uuid.uuid4().hex[:5], **kw))

    def builder(self, page):
        return self.client.get(reverse("prblm_builder:builder", args=[page.id]) + "?embed=1")

    def test_builder_page_gets_header_and_footer_dropdowns(self):
        page = self.builder_page(header_choice="custom", header=self.campaign)
        r = self.builder(page)
        opts = {o["name"]: o for o in r.context["page_options"]}
        self.assertEqual(set(opts), {"header", "footer"})
        self.assertEqual(opts["header"]["value"], f"id:{self.campaign.pk}")
        values = [c["value"] for c in opts["header"]["choices"]]
        self.assertEqual(values[:2], ["default", "none"])
        self.assertIn(f"id:{self.campaign.pk}", values)
        self.assertIn("Site default (Main header)", [c["label"] for c in opts["header"]["choices"]])
        self.assertContains(r, 'role="tab"')
        self.assertContains(r, 'data-chrome="header"')

    @override_settings(PRBLM_BUILDER_HEADER_TEMPLATE="testapp/header.html")
    def test_site_template_choice_only_when_configured(self):
        r = self.builder(self.builder_page())
        header = [o for o in r.context["page_options"] if o["name"] == "header"][0]
        self.assertIn("site", [c["value"] for c in header["choices"]])

    def own_page(self):
        return Page.objects.get(depth=1).add_child(
            instance=StandardPage(title="S", slug="s-" + uuid.uuid4().hex[:5]))

    def test_own_page_types_get_information_only(self):
        r = self.builder(self.own_page())
        opts = {o["name"]: o for o in r.context["page_options"]}
        self.assertEqual(set(opts), {"header", "footer"})
        self.assertNotIn("choices", opts["header"])                       # nothing to choose
        self.assertIn("Main header", opts["header"]["info"])              # the site default
        self.assertIn("{% prblm_header %}", opts["header"]["info"])
        self.assertFalse(r.context["page_options_editable"])
        self.assertContains(r, 'role="tab"')
        self.assertContains(r, "pb-opt-info")
        self.assertNotContains(r, 'class="pb-opt-select"')
        self.assertNotContains(r, "Saved with the page (Save draft")

    @override_settings(PRBLM_BUILDER_HEADER_TEMPLATE="testapp/header.html")
    def test_information_names_the_template_setting(self):
        r = self.builder(self.own_page())
        header = [o for o in r.context["page_options"] if o["name"] == "header"][0]
        self.assertIn("testapp/header.html", header["info"])

    def test_information_without_any_header(self):
        from prblm_builder.blocks.models import SiteFooter, SiteHeader
        SiteHeader.objects.all().delete(); SiteFooter.objects.all().delete()
        r = self.builder(self.own_page())
        header = [o for o in r.context["page_options"] if o["name"] == "header"][0]
        self.assertIn("PRBLM_BUILDER_HEADER_TEMPLATE", header["info"])

    def test_fields_moved_from_content_tab_to_hidden_layout_panel(self):
        page = self.builder_page()
        html = self.client.get(reverse("wagtailadmin_pages:edit", args=[page.id])).content.decode()
        self.assertEqual(html.count("data-prblm-page-option"), 4 + 1)     # 4 panels + the CSS rule
        self.assertIn('name="header_choice"', html)

    def test_unsaved_choice_previewed_on_canvas(self):
        page = self.builder_page()
        base = reverse("prblm_builder:preview") + f"?page={page.id}&chrome=header"
        self.assertContains(self.client.get(base), "Acme Header")
        r = self.client.get(base + "&options=" + json.dumps({"header": f"id:{self.campaign.pk}"}))
        self.assertContains(r, "Campaign Header")
        r = self.client.get(base + "&options=" + json.dumps({"header": "none"}))
        self.assertEqual(r.status_code, 404)

    def test_choice_saves_through_the_edit_form(self):
        from prblm_builder.blocks.models import BuilderPage
        page = self.builder_page()
        url = reverse("wagtailadmin_pages:edit", args=[page.id])
        r = self.client.post(url, {"title": "BP", "slug": page.slug, "body-count": "0",
                                   "header_choice": "custom", "header": str(self.campaign.pk),
                                   "footer_choice": "none", "footer": ""})
        self.assertEqual(r.status_code, 302)
        saved = BuilderPage.objects.get(pk=page.pk).get_latest_revision_as_object()
        self.assertEqual((saved.header_choice, saved.header_id, saved.footer_choice),
                         ("custom", self.campaign.pk, "none"))


@override_settings(STORAGES=STORAGES)
class DraftNotLiveTests(TestCase):
    """The Layout tab shows the latest draft (like Wagtail's editor), not the published page."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("dr", "dr@example.com", "pw"))
        self.page = StandardPage(title="D", slug="d-" + uuid.uuid4().hex[:5])
        self.page.body = json.dumps([{"type": "heading", "value": "Published heading", "id": "p1"}])
        Page.objects.get(depth=2).add_child(instance=self.page)
        self.page.save_revision().publish()
        draft = StandardPage.objects.get(pk=self.page.pk)
        draft.body = json.dumps([{"type": "heading", "value": "Draft heading", "id": "p1"},
                                 {"type": "banner", "id": "d2",
                                  "value": {"title": "Draft only", "tone": "loud", "show_border": False}}])
        draft.save_revision()                                   # saved, not published

    def test_canvas_lists_draft_sections(self):
        r = self.client.get(reverse("prblm_builder:builder", args=[self.page.id]) + "?embed=1")
        self.assertEqual([s["id"] for s in r.context["sections"]], ["p1", "d2"])
        self.assertEqual(r.context["sections"][1]["settings"]["tone"], "loud")

    def test_section_preview_renders_draft_content(self):
        base = reverse("prblm_builder:preview") + f"?page={self.page.id}"
        self.assertContains(self.client.get(base + "&block=heading&section=p1"), "Draft heading")
        self.assertContains(self.client.get(base + "&block=banner&section=d2"), "Draft only")

    def test_published_page_unchanged(self):
        self.assertIn("Published heading", self.client.get(self.page.url).content.decode())


class UneditedAfterEditorSaveTests(TestCase):
    def test_editor_normalisation_is_not_an_edit(self):
        """Saving through Wagtail's form turns empty text into "" and adds data-block-key
        to rich text — the section is still unedited."""
        from prblm_builder.blocks.sections.conversion import FAQBlock
        block = FAQBlock()
        stored = json.loads(json.dumps(block.get_prep_value(block.get_default())))
        for item in stored["items"]:
            item["value"]["answer"] = item["value"]["answer"].replace("<p>", '<p data-block-key="ab12c">', 1)
        stored["anchor_id"] = ""
        self.assertTrue(previews.is_unedited(block, "faq", stored))
        stored["heading"] = "Really edited"
        self.assertFalse(previews.is_unedited(block, "faq", stored))
