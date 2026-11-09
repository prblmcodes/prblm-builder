"""Media and people: Gallery, Video, Team."""
import re

from django.core.exceptions import ValidationError
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

from .base import AnchorBlock, BackgroundBlock, LinkBlock, SectionBlock

T = "prblm_builder/blocks/"

_YT = re.compile(r"(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|live/)|youtu\.be/)([\w-]{11})")
_VIMEO = re.compile(r"vimeo\.com/(?:video/)?(\d+)")


def embed_url(url):
    """A privacy-friendly embed address for a YouTube or Vimeo link, or ``""``. Built
    from the URL itself — no call to the video site."""
    url = url or ""
    m = _YT.search(url)
    if m:
        return f"https://www.youtube-nocookie.com/embed/{m.group(1)}"
    m = _VIMEO.search(url)
    if m:
        return f"https://player.vimeo.com/video/{m.group(1)}?dnt=1"
    return ""


class VideoURLBlock(blocks.URLBlock):
    def clean(self, value):
        value = super().clean(value)
        if value and not embed_url(value):
            raise ValidationError("Paste a YouTube or Vimeo link.")
        return value


class VideoValue(blocks.StructValue):
    @property
    def embed_url(self):
        return embed_url(self.get("url"))


class GalleryImageBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=False)
    caption = blocks.CharBlock(required=False)


class GalleryBlock(SectionBlock):
    heading = blocks.CharBlock(required=False, default="A gallery of images")
    intro = blocks.TextBlock(required=False, default="Add photos in the Content tab. Captions are optional.")
    columns = blocks.ChoiceBlock(choices=[("2", "2"), ("3", "3"), ("4", "4")], default="3")
    images = blocks.ListBlock(GalleryImageBlock(), default=[
        {"caption": "An optional caption"}, {"caption": ""}, {"caption": ""},
        {"caption": ""}, {"caption": ""}, {"caption": ""},
    ])
    background = BackgroundBlock()
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "gallery.html"
        icon = "image"
        label = "Gallery"
        description = "A grid of images with optional captions."
        group = "Media & people"


class VideoBlock(SectionBlock):
    heading = blocks.CharBlock(required=False, default="A video worth watching")
    url = VideoURLBlock(required=False, label="Video link",
                        help_text="A YouTube or Vimeo link, e.g. https://www.youtube.com/watch?v=…")
    caption = blocks.CharBlock(required=False, default="Paste a YouTube or Vimeo link in the Content tab.")
    background = BackgroundBlock()
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "video.html"
        icon = "media"
        label = "Video"
        description = "A YouTube or Vimeo video, embedded privacy-friendly."
        group = "Media & people"
        value_class = VideoValue


class MemberBlock(blocks.StructBlock):
    photo = ImageChooserBlock(required=False)
    name = blocks.CharBlock()
    role = blocks.CharBlock(required=False)
    bio = blocks.TextBlock(required=False)
    link = LinkBlock(help_text="Optional, e.g. their LinkedIn profile.")


class TeamBlock(SectionBlock):
    eyebrow = blocks.CharBlock(required=False, default="Our team")
    heading = blocks.CharBlock(default="The people behind the work")
    intro = blocks.TextBlock(required=False, default="Faces build trust. Add a photo, name and role for each person.")
    columns = blocks.ChoiceBlock(choices=[("2", "2"), ("3", "3"), ("4", "4")], default="4")
    members = blocks.ListBlock(MemberBlock(), default=[
        {"name": "Person's name", "role": "Their role", "bio": "One sentence about them."},
        {"name": "Person's name", "role": "Their role", "bio": "Keep bios the same length."},
        {"name": "Person's name", "role": "Their role", "bio": "Use photos of the same shape."},
        {"name": "Person's name", "role": "Their role", "bio": "Add or remove people in the Content tab."},
    ])
    background = BackgroundBlock()
    anchor_id = AnchorBlock()

    class Meta:
        template = T + "team.html"
        icon = "group"
        label = "Team"
        description = "People with photo, name, role and a short bio."
        group = "Media & people"
