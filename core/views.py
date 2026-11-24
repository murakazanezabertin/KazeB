import json

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils.translation import gettext as _

from listings.models import Listing


def _react_app_context():
    manifest_path = settings.BASE_DIR / "static" / "react" / ".vite" / "manifest.json"
    if not manifest_path.is_file():
        raise ImproperlyConfigured(
            "React dashboard assets are missing. Run the frontend production build."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest.get("index.html")
    if not isinstance(entry, dict) or not entry.get("file"):
        raise ImproperlyConfigured("The React production build manifest is invalid.")

    def static_url(path):
        url = staticfiles_storage.url(f"react/{path}")
        return url if url.startswith(("/", "http://", "https://")) else f"/{url}"

    return {
        "vite_js": static_url(entry["file"]),
        "vite_css": [static_url(path) for path in entry.get("css", [])],
    }


def _render_react_app(request, page_title, *, noindex):
    """Render the shared React application shell.

    Single source of truth for serving the Vite-built React bundle so the
    homepage, account pages, and admin dashboard never duplicate shell
    wiring. ``noindex`` controls the robots meta tag (public pages are
    indexable; authenticated/admin pages are not).
    """
    context = _react_app_context()
    context["page_title"] = page_title
    context["noindex"] = noindex
    return render(request, "core/react_app.html", context)


def react_home(request):
    """Production homepage: serves the same React app verified locally.

    The React ``App`` component fetches real data from ``/api/home/`` and
    the other Django API routes, so this view only supplies the built
    bundle via the Vite manifest. Kept separate from the legacy
    ``home`` template view so that template remains available.
    """
    return _render_react_app(request, "KazeB", noindex=False)


def admin_dashboard_page(request):
    if not request.user.is_authenticated:
        return HttpResponse("Authentication is required.", status=401)
    if not request.user.is_staff or not request.user.has_perm("trust.view_admin_dashboard"):
        return HttpResponseForbidden("You do not have permission to access this page.")

    return _render_react_app(request, "KazeB Administrator", noindex=True)


def account_profile_page(request):
    return _render_react_app(request, f'{_("Umwirondoro wanjye")} · KazeB', noindex=True)


def home(request):
    """
    The landing page: "Welcome to KazeB" hero, the tagline, and
    the "find by category" icon grid. Categories come from the
    nav_categories context processor; this view only adds a handful
    of recent listings so the page isn't empty on a fresh install.
    """
    recent_listings = Listing.objects.filter(
        is_active=True,
        moderation_status=Listing.ModerationStatus.VISIBLE,
    ).select_related("category")[:8]
    return render(request, "core/home.html", {"recent_listings": recent_listings})


def how_it_works(request):
    return render(request, "core/how_it_works.html")


def terms(request):
    return render(request, "core/terms.html")


def privacy(request):
    return render(request, "core/privacy.html")


def about(request):
    """About Us: who KazeB is, how the site works, and its terms of
    service, gathered on one page linked from the orange footer
    section on every page."""
    return render(request, "core/about.html")


def contact(request):
    """Contact Us page, linked from the orange footer section."""
    return render(request, "core/contact.html")


def faq(request):
    """Frequently asked questions, linked from the orange footer."""
    return render(request, "core/faq.html")


def anti_scam(request):
    """Safety / anti-scam tips, linked from the orange footer."""
    return render(request, "core/anti_scam.html")
