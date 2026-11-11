"""0.9.1: demo-content records of deleted pages are removed; cleanup command."""
import json
import uuid
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from wagtail.models import Page

from prblm_builder import cleanup
from prblm_builder.models import SeededSection
from tests.testapp.models import StandardPage


def make_page(sid, slug, publish=True):
    body = json.dumps([{"type": "heading", "value": "Demo heading", "id": sid}])
    page = Page.objects.get(depth=2).add_child(instance=StandardPage(title=slug, slug=slug, body=body))
    rev = page.save_revision()
    if publish:
        rev.publish()
    return page


class DeletedPageTests(TestCase):
    def test_records_go_with_the_page(self):
        sid = str(uuid.uuid4())
        page = make_page(sid, "gone")
        SeededSection.objects.create(section_id=sid, value_hash="x")
        with self.captureOnCommitCallbacks(execute=True):
            page.delete()
        self.assertFalse(SeededSection.objects.filter(section_id=sid).exists())

    def test_kept_while_another_page_has_the_section(self):
        """Copy page keeps section ids: the copy's untouched section keeps its record."""
        sid = str(uuid.uuid4())
        page = make_page(sid, "original")
        make_page(sid, "copy")
        SeededSection.objects.create(section_id=sid, value_hash="x")
        with self.captureOnCommitCallbacks(execute=True):
            page.delete()
        self.assertTrue(SeededSection.objects.filter(section_id=sid).exists())

    def test_kept_while_a_draft_has_the_section(self):
        sid = str(uuid.uuid4())
        page = make_page(sid, "pub")
        other = make_page(str(uuid.uuid4()), "drafty")
        other.body = json.dumps([{"type": "heading", "value": "Draft", "id": sid}])
        other.save_revision()                       # only in the other page's draft
        SeededSection.objects.create(section_id=sid, value_hash="x")
        with self.captureOnCommitCallbacks(execute=True):
            page.delete()
        self.assertTrue(SeededSection.objects.filter(section_id=sid).exists())

    def test_child_pages_deleted_with_their_parent(self):
        parent_sid, child_sid = str(uuid.uuid4()), str(uuid.uuid4())
        parent = make_page(parent_sid, "parent")
        body = json.dumps([{"type": "heading", "value": "Child", "id": child_sid}])
        parent.add_child(instance=StandardPage(title="child", slug="child", body=body)).save_revision().publish()
        for sid in (parent_sid, child_sid):
            SeededSection.objects.create(section_id=sid, value_hash="x")
        with self.captureOnCommitCallbacks(execute=True):
            Page.objects.get(pk=parent.pk).delete()
        self.assertFalse(SeededSection.objects.exists())

    def test_section_ids_from_content_and_revisions(self):
        a, b = str(uuid.uuid4()), str(uuid.uuid4())
        page = make_page(a, "ids")
        page.body = json.dumps([{"type": "heading", "value": "New", "id": b}])
        page.save_revision()
        self.assertEqual(cleanup.page_section_ids(page), {a, b})


class CleanupCommandTests(TestCase):
    def test_removes_only_orphans(self):
        used = str(uuid.uuid4())
        make_page(used, "used")
        SeededSection.objects.create(section_id=used, value_hash="x")
        SeededSection.objects.create(section_id=str(uuid.uuid4()), value_hash="y")   # leftover
        out = StringIO()
        call_command("prblm_builder_cleanup", "--dry-run", stdout=out)
        self.assertIn("1 of 2", out.getvalue())
        self.assertEqual(SeededSection.objects.count(), 2)
        call_command("prblm_builder_cleanup", stdout=StringIO())
        self.assertEqual(list(SeededSection.objects.values_list("section_id", flat=True)), [used])
