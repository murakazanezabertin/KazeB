from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from chat.models import Message
from kazeb.imaging import compress_uploaded_image
from .forms import ListingForm, ListingSearchForm
from .models import Category, Favorite, Listing, ListingImage

User = get_user_model()

SORT_OPTIONS = {
    "newest": ("-created_at", "-pk"),
    "oldest": ("created_at", "pk"),
    "most_viewed": ("-views_count", "-created_at", "-pk"),
}


def _apply_search(qs, form):
    """Shared filtering logic for the category page and the general
    search page: an immediate free-text search over listing name,
    district and sector."""
    if not form.is_valid():
        return qs

    q = form.cleaned_data.get("q")
    if q:
        qs = qs.filter(Q(district__icontains=q) | Q(sector__icontains=q) | Q(name__icontains=q))

    return qs


def _apply_filters_and_sort(request, qs):
    """Extra buyer controls beyond the free-text box: filter by
    condition (new/used), and sort. Sorting is two independent
    dropdowns rather than one combined list: "sort" (newest / oldest /
    most viewed) and a separate "price_sort" (low-to-high /
    high-to-low). Choosing a price sort takes priority over the date
    sort, since picking one is a deliberate choice to sort by price
    instead."""
    condition = request.GET.get("condition")
    if condition in dict(Listing.Condition.choices):
        qs = qs.filter(condition=condition)

    price_sort = request.GET.get("price_sort")
    if price_sort == "asc":
        qs = qs.order_by("price", "pk")
    elif price_sort == "desc":
        qs = qs.order_by("-price", "-pk")
    else:
        sort = request.GET.get("sort")
        qs = qs.order_by(*SORT_OPTIONS.get(sort, SORT_OPTIONS["newest"]))

    return qs


def category_detail(request, slug):
    """Buyer view: all active listings inside one category, with the
    search box, plus condition filter and sorting, above the grid."""
    category = get_object_or_404(Category, slug=slug)
    search_form = ListingSearchForm(request.GET or None)

    listings_qs = Listing.objects.filter(category=category, is_active=True).select_related("seller")
    listings_qs = _apply_search(listings_qs, search_form)
    listings_qs = _apply_filters_and_sort(request, listings_qs)

    paginator = Paginator(listings_qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "listings/category_list.html",
        {
            "category": category,
            "search_form": search_form,
            "page_obj": page_obj,
        },
    )


def search(request):
    """The general search results page, reached by typing in the nav
    bar search box -- same text filter, condition filter and sorting
    as a category page, but across every category."""
    search_form = ListingSearchForm(request.GET or None)
    listings_qs = Listing.objects.filter(is_active=True).select_related("seller")
    listings_qs = _apply_search(listings_qs, search_form)
    listings_qs = _apply_filters_and_sort(request, listings_qs)

    paginator = Paginator(listings_qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "listings/category_list.html",
        {
            "category": None,
            "search_form": search_form,
            "page_obj": page_obj,
        },
    )


def listing_detail(request, pk):
    """The full detail page: photos, description, price, and the three
    contact options -- in-site message, WhatsApp, and copy phone
    number."""
    listing = get_object_or_404(
        Listing.objects.select_related("seller"), pk=pk, is_active=True
    )
    if request.user != listing.seller:
        Listing.objects.filter(pk=listing.pk).update(views_count=F("views_count") + 1)
        listing.views_count += 1

    from trust.models import Review

    seller_reviews = Review.objects.filter(seller=listing.seller)
    seller_rating = None
    if seller_reviews:
        seller_rating = sum(r.rating for r in seller_reviews) / len(seller_reviews)

    is_favorited = (
        request.user.is_authenticated
        and Favorite.objects.filter(user=request.user, listing=listing).exists()
    )

    return render(
        request,
        "listings/listing_detail.html",
        {
            "listing": listing,
            "seller_rating": seller_rating,
            "seller_review_count": len(seller_reviews),
            "is_favorited": is_favorited,
        },
    )


def seller_profile(request, username):
    """Public seller page with only that seller's currently active listings."""
    seller = get_object_or_404(User, username=username)
    listings_qs = (
        Listing.objects.filter(seller=seller, is_active=True)
        .select_related("seller")
        .prefetch_related("images")
    )
    active_listings_count = listings_qs.count()
    contact_listing = listings_qs.first()
    page_obj = Paginator(listings_qs, 12).get_page(request.GET.get("page"))

    return render(
        request,
        "listings/seller_profile.html",
        {
            "seller": seller,
            "display_name": seller.get_full_name() or seller.username,
            "active_listings_count": active_listings_count,
            "contact_listing": contact_listing,
            "page_obj": page_obj,
        },
    )


def seller_profile_api(request, username):
    """Return a limited public profile payload, never authentication or email data."""
    try:
        seller = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({"detail": "Seller not found."}, status=404)

    listings_qs = (
        Listing.objects.filter(seller=seller, is_active=True)
        .prefetch_related("images")
        .order_by("-created_at")
    )
    active_listings_count = listings_qs.count()
    page_obj = Paginator(listings_qs, 12).get_page(request.GET.get("page"))

    listings = []
    for listing in page_obj:
        cover_image = listing.cover_image
        image_url = (
            request.build_absolute_uri(cover_image.image.url) if cover_image else None
        )
        listings.append(
            {
                "id": listing.pk,
                "title": listing.name,
                "image": image_url,
                "price": str(listing.price),
                "currency": listing.currency,
                "location": listing.location,
                "url": listing.get_absolute_url(),
            }
        )

    return JsonResponse(
        {
            "username": seller.username,
            "display_name": seller.get_full_name() or seller.username,
            "profile_picture": (
                request.build_absolute_uri(seller.profile_picture.url)
                if seller.profile_picture
                else None
            ),
            "location": seller.location,
            "bio": seller.bio,
            "date_joined": seller.date_joined.date().isoformat(),
            "is_phone_verified": seller.is_phone_verified,
            "active_listings_count": active_listings_count,
            "listings": listings,
            "pagination": {
                "page": page_obj.number,
                "pages": page_obj.paginator.num_pages,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            },
        }
    )


@login_required
def toggle_favorite(request, pk):
    """Save/un-save a listing to the signed-in user's favourites.
    POST only, redirects back to wherever the request came from."""
    listing = get_object_or_404(Listing, pk=pk, is_active=True)
    if request.method == "POST":
        favorite, created = Favorite.objects.get_or_create(user=request.user, listing=listing)
        if not created:
            favorite.delete()
            messages.info(request, _("Wavanyeho iki gicuruzwa ku bya kwibuka."))
        else:
            messages.success(request, _("Igicuruzwa cyongewe ku bya kwibuka."))
    return redirect(request.POST.get("next") or listing.get_absolute_url())


@login_required
def favorites(request):
    """The signed-in user's saved/favourited listings."""
    favorite_qs = (
        Favorite.objects.filter(user=request.user)
        .select_related("listing", "listing__seller")
        .prefetch_related("listing__images")
    )
    return render(request, "listings/favorites.html", {"favorites": favorite_qs})


@login_required
def listing_create(request):
    """Seller flow: category, name, photos, details, condition,
    location and price. Requires login, per the spec."""
    if request.method == "POST":
        form = ListingForm(request.POST)
        images = request.FILES.getlist("images")
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = request.user
            listing.save()

            for index, image_file in enumerate(images):
                ListingImage.objects.create(
                    listing=listing,
                    image=compress_uploaded_image(image_file),
                    is_cover=(index == 0),
                )

            messages.success(request, _("Icyo ugurisha cyashyizwe ahagaragara."))
            return redirect(listing.get_absolute_url())
    else:
        form = ListingForm()

    return render(request, "listings/listing_form.html", {"form": form})


@login_required
def listing_edit(request, pk):
    """Let a seller edit their own product: same form as creating one,
    pre-filled, plus the ability to remove existing photos and add new
    ones."""
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)

    if request.method == "POST":
        form = ListingForm(request.POST, instance=listing)
        new_images = request.FILES.getlist("images")
        remove_ids = request.POST.getlist("remove_images")
        if form.is_valid():
            form.save()

            if remove_ids:
                listing.images.filter(pk__in=remove_ids).delete()

            has_cover = listing.images.filter(is_cover=True).exists()
            for index, image_file in enumerate(new_images):
                ListingImage.objects.create(
                    listing=listing,
                    image=compress_uploaded_image(image_file),
                    is_cover=(not has_cover and index == 0),
                )

            messages.success(request, _("Impinduka zabitswe."))
            return redirect(listing.get_absolute_url())
    else:
        form = ListingForm(instance=listing)

    return render(
        request,
        "listings/listing_form.html",
        {"form": form, "listing": listing, "editing": True},
    )


@login_required
def listing_delete(request, pk):
    """Delete a seller's own product. GET shows a confirmation page;
    the actual deletion only happens on POST."""
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)

    if request.method == "POST":
        listing.delete()
        messages.success(request, _("Igicuruzwa cyasibwe."))
        return redirect("listings:dashboard")

    return render(request, "listings/listing_confirm_delete.html", {"listing": listing})


@login_required
def dashboard(request):
    """
    The seller's control panel -- deliberately a different view from
    what a buyer sees browsing the site. Shows the listings this user
    has published (with per-listing views and message counts) plus the
    most recent messages customers sent them about those listings.
    """
    listings_qs = (
        Listing.objects.filter(seller=request.user)
        .annotate(thread_count=Count("messages__buyer", distinct=True))
        .prefetch_related("images")
        .order_by("-created_at")
    )

    recent_messages = (
        Message.objects.filter(listing__seller=request.user)
        .exclude(sender=request.user)
        .select_related("listing", "sender")
        .order_by("-created_at")[:10]
    )

    unread_count = Message.objects.filter(
        listing__seller=request.user, is_read=False
    ).exclude(sender=request.user).count()

    return render(
        request,
        "listings/dashboard.html",
        {
            "listings": listings_qs,
            "recent_messages": recent_messages,
            "total_views": sum(listing.views_count for listing in listings_qs),
            "unread_count": unread_count,
        },
    )
