from django.shortcuts import render

from listings.models import Listing


def home(request):
    """
    The landing page: "Welcome to KazeB" hero, the tagline, and
    the "find by category" icon grid. Categories come from the
    nav_categories context processor; this view only adds a handful
    of recent listings so the page isn't empty on a fresh install.
    """
    recent_listings = Listing.objects.filter(is_active=True).select_related("category")[:8]
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
