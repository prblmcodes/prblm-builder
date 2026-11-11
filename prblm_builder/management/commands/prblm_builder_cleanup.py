"""Remove demo-content records of sections that no longer exist on any page."""
from django.core.management.base import BaseCommand

from prblm_builder import cleanup
from prblm_builder.models import SeededSection


class Command(BaseCommand):
    help = ("Remove the plugin's demo-content records (\"Not edited yet\" markers) of sections "
            "that no page or revision has any more. Safe to run any time.")

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Only say how many would be removed.")

    def handle(self, *args, **options):
        ids = cleanup.orphans()
        total = SeededSection.objects.count()
        if options["dry_run"]:
            self.stdout.write(f"{len(ids)} of {total} demo-content records would be removed.")
            return
        SeededSection.objects.filter(section_id__in=ids).delete()
        self.stdout.write(self.style.SUCCESS(f"Removed {len(ids)} of {total} demo-content records."))
