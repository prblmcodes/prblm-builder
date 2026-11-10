"""The core app's one table: which sections the plugin filled with demo content."""
from django.db import models


class SeededSection(models.Model):
    """A section the Layout tab added with demo content, and a hash of that content.

    While a section's content still has this hash nobody has edited it: the canvas shows
    "Not edited yet", and it's never borrowed as real site content for other demos.
    Keyed by the section's id (a UUID, stable across saves).
    """

    section_id = models.CharField(max_length=64, unique=True)
    value_hash = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "seeded section"

    def __str__(self):
        return self.section_id
