"""The site-wide Header & footer (set once in Page builder → Header & footer)."""
from django.utils.safestring import mark_safe


def settings_for(request=None):
    """This site's SiteChrome settings, or ``None`` (no site, table missing, …)."""
    try:
        from wagtail.models import Site

        from .models import SiteChrome
        if request is not None:
            return SiteChrome.for_request(request)
        site = Site.objects.filter(is_default_site=True).first()
        return SiteChrome.for_site(site) if site else None
    except Exception:
        return None


def render(kind, request=None, page=None):
    """Rendered HTML of the site-wide ``header`` or ``footer`` block, or ``""``."""
    obj = settings_for(request)
    stream = getattr(obj, kind, None) if obj is not None else None
    if not stream:
        return ""
    context = {"request": request, "page": page, "self": page}
    return mark_safe(stream[0].render(context=context))
