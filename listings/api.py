from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from trust.models import Review

from .forms import ListingForm, ListingSearchForm
from .image_uploads import (
    cleanup_uploaded_listing_images,
    ensure_listing_cover,
    save_listing_images,
    validate_listing_images,
)
from .models import Category, Favorite, Listing
from .templatetags.category_extras import get_category_display_name
from .views import _apply_filters_and_sort, _apply_search

User = get_user_model()


class ListingCategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    url = serializers.CharField()


class ListingCardSellerSerializer(serializers.Serializer):
    username = serializers.CharField()
    name = serializers.CharField()
    url = serializers.CharField()
    image = serializers.CharField(allow_null=True)


class ListingCardSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    url = serializers.CharField()
    image = serializers.CharField(allow_null=True)
    price = serializers.CharField()
    location = serializers.CharField()
    seller = ListingCardSellerSerializer()


class ListingPaginationSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    pages = serializers.IntegerField()
    has_next = serializers.BooleanField()
    has_previous = serializers.BooleanField()
    count = serializers.IntegerField()


class ListingBrowseSerializer(serializers.Serializer):
    category = ListingCategorySerializer(allow_null=True)
    categories = ListingCategorySerializer(many=True)
    results = ListingCardSerializer(many=True)
    pagination = ListingPaginationSerializer()
    filters = serializers.DictField(child=serializers.CharField(allow_blank=True))


class ListingPhotoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    url = serializers.CharField()


class ListingDetailSellerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    name = serializers.CharField()
    url = serializers.CharField()
    image = serializers.CharField(allow_null=True)
    phone_number = serializers.CharField(allow_blank=True)
    whatsapp_digits = serializers.CharField(allow_blank=True)
    is_phone_verified = serializers.BooleanField()
    rating = serializers.FloatField(allow_null=True)
    review_count = serializers.IntegerField()
    reviews_url = serializers.CharField()


class ListingDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    condition = serializers.CharField()
    category = ListingCategorySerializer()
    price = serializers.CharField()
    location = serializers.CharField()
    created_at = serializers.DateTimeField()
    views_count = serializers.IntegerField()
    images = ListingPhotoSerializer(many=True)
    seller = ListingDetailSellerSerializer()
    is_owner = serializers.BooleanField()
    is_favorited = serializers.BooleanField()


class SellerListingStatusSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


def _seller_dashboard_statistics(user):
    from chat.models import Message

    listing_stats = Listing.objects.filter(seller=user).aggregate(
        total_listings=Count("pk"),
        active_listings=Count("pk", filter=Q(is_active=True)),
        total_views=Sum("views_count"),
    )
    unread_messages = (
        Message.objects.filter(listing__seller=user)
        .exclude(sender=user)
        .filter(is_read=False)
        .count()
    )
    total_listings = listing_stats["total_listings"]
    active_listings = listing_stats["active_listings"]
    return {
        "total_listings": total_listings,
        "active_listings": active_listings,
        "inactive_listings": total_listings - active_listings,
        "total_views": listing_stats["total_views"] or 0,
        "unread_messages": unread_messages,
    }


def _category_payload(category):
    return {
        "id": category.pk,
        "name": get_category_display_name(category),
        "slug": category.slug,
        "url": category.get_absolute_url(),
    }


def _listing_card_payload(listing):
    cover_image = listing.cover_image
    seller = listing.seller
    return {
        "id": listing.pk,
        "name": listing.name,
        "url": listing.get_absolute_url(),
        "image": cover_image.image.url if cover_image else None,
        "price": listing.display_price,
        "location": listing.location,
        "seller": {
            "username": seller.username,
            "name": seller.get_full_name() or seller.username,
            "url": f"/seller/{seller.username}/",
            "image": seller.profile_picture.url if seller.profile_picture else None,
        },
    }


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def listing_browse_api(request):
    category_slug = request.query_params.get("category", "")
    category = (
        get_object_or_404(Category, slug=category_slug) if category_slug else None
    )
    categories = [_category_payload(item) for item in Category.objects.all()]

    listings = Listing.objects.filter(is_active=True).select_related(
        "seller", "category"
    ).prefetch_related("images")
    if category:
        listings = listings.filter(category=category)

    search_form = ListingSearchForm(request.query_params)
    listings = _apply_search(listings, search_form)

    location = request.query_params.get("location", "").strip()
    if location:
        listings = listings.filter(
            Q(district__icontains=location) | Q(sector__icontains=location)
        )

    listings = _apply_filters_and_sort(request, listings)
    paginator = Paginator(listings, 12)
    page_obj = paginator.get_page(request.query_params.get("page"))
    payload = {
        "category": _category_payload(category) if category else None,
        "categories": categories,
        "results": [_listing_card_payload(listing) for listing in page_obj],
        "pagination": {
            "page": page_obj.number,
            "pages": paginator.num_pages,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "count": paginator.count,
        },
        "filters": {
            "q": request.query_params.get("q", ""),
            "location": location,
            "condition": request.query_params.get("condition", ""),
            "sort": request.query_params.get("sort", "newest"),
            "price_sort": request.query_params.get("price_sort", ""),
        },
    }
    serializer = ListingBrowseSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    return Response(serializer.data, headers={"Cache-Control": "private, no-store"})


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def listing_detail_api(request, pk):
    listing = get_object_or_404(
        Listing.objects.select_related("seller", "category").prefetch_related("images"),
        pk=pk,
        is_active=True,
    )
    is_owner = request.user.is_authenticated and request.user.pk == listing.seller_id
    if not is_owner:
        Listing.objects.filter(pk=listing.pk).update(views_count=F("views_count") + 1)
        listing.views_count += 1

    seller = listing.seller
    review_summary = Review.objects.filter(seller=seller).aggregate(
        rating=Avg("rating"),
        review_count=Count("pk"),
    )
    is_favorited = (
        request.user.is_authenticated
        and Favorite.objects.filter(user=request.user, listing=listing).exists()
    )
    payload = {
        "id": listing.pk,
        "name": listing.name,
        "description": listing.description,
        "condition": listing.get_condition_display(),
        "category": _category_payload(listing.category),
        "price": listing.display_price,
        "location": listing.location,
        "created_at": listing.created_at,
        "views_count": listing.views_count,
        "images": [
            {"id": image.pk, "url": image.image.url}
            for image in listing.images.order_by("-is_cover", "pk")
        ],
        "seller": {
            "id": seller.pk,
            "username": seller.username,
            "name": seller.get_full_name() or seller.username,
            "url": f"/seller/{seller.username}/",
            "image": seller.profile_picture.url if seller.profile_picture else None,
            "phone_number": seller.phone_number,
            "whatsapp_digits": seller.whatsapp_digits(),
            "is_phone_verified": seller.is_phone_verified,
            "rating": review_summary["rating"],
            "review_count": review_summary["review_count"],
            "reviews_url": f"/trust/seller/{seller.pk}/reviews/",
        },
        "is_owner": is_owner,
        "is_favorited": is_favorited,
    }
    serializer = ListingDetailSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    return Response(serializer.data, headers={"Cache-Control": "private, no-store"})


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def seller_dashboard_api(request):
    """Return the authenticated seller's listing dashboard data."""
    listings = (
        Listing.objects.filter(seller=request.user)
        .select_related("category")
        .prefetch_related("images")
        .annotate(thread_count=Count("messages__buyer", distinct=True))
        .order_by("-created_at")
    )

    listings_payload = []
    for listing in listings:
        cover_image = listing.cover_image
        listings_payload.append(
            {
                "id": listing.pk,
                "title": listing.name,
                "url": listing.get_absolute_url(),
                "price": str(listing.price),
                "display_price": listing.display_price,
                "currency": listing.currency,
                "condition": listing.condition,
                "condition_display": listing.get_condition_display(),
                "status": "active" if listing.is_active else "inactive",
                "is_active": listing.is_active,
                "created_at": listing.created_at,
                "views_count": listing.views_count,
                "thread_count": listing.thread_count,
                "cover_image": (
                    request.build_absolute_uri(cover_image.image.url)
                    if cover_image
                    else None
                ),
                "category": _category_payload(listing.category),
                "location": listing.location,
            }
        )

    payload = {
        "statistics": _seller_dashboard_statistics(request.user),
        "listings": listings_payload,
        "labels": {
            "title": _("Konti yanjye"),
            "subtitle": _("Aha nihoreba ibyo watanze n'ubutumwa abaguzi bakoherereje."),
            "add_listing": _("Ongeraho igicuruzwa"),
            "total_listings": _("Ibicuruzwa"),
            "active_listings": _("Biragaragara"),
            "inactive_listings": _("Birahishwe"),
            "total_views": _("Abarebye"),
            "unread_messages": _("Ubutumwa butarasomwa"),
            "my_listings": _("Ibicuruzwa byanjye"),
            "no_listings": _("Nturigeze wongeraho ikintu cyo kugurisha."),
            "active": _("Biragaragara"),
            "inactive": _("Birahishwe"),
            "views": _("Abarebye"),
            "conversations": _("Ibiganiro"),
            "created": _("Byashyizweho"),
            "empty_image": _("Nta foto ihari"),
            "loading": _("Birimo gutegurwa..."),
            "load_error": _("Ntibashoboye gutegura konti y'ibicuruzwa."),
            "edit_listing": _("Hindura"),
            "listing_created": _("Icyo ugurisha cyashyizwe ahagaragara."),
            "listing_updated": _("Impinduka zabitswe."),
            "hide_listing": _("Hisha igicuruzwa"),
            "activate_listing": _("Erekana igicuruzwa"),
            "status_saving": _("Birimo kubikwa..."),
            "delete_listing": _("Siba"),
            "confirm_delete_listing": _(
                "Urifuza gusiba iki gicuruzwa? Iki gikorwa ntikigaruka -- amafoto n'ubutumwa bufitanye isano na cyo na byo bizasibwa."
            ),
            "delete_loading": _("Birimo gusibwa..."),
        },
    }
    return Response(payload, headers={"Cache-Control": "private, no-store"})


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def seller_listing_create_api(request):
    """Create a listing owned by the authenticated seller."""
    if request.method == "GET":
        form = ListingForm()
        categories = [
            {
                "id": category.pk,
                "name": get_category_display_name(category),
                "slug": category.slug,
            }
            for category in Category.objects.all()
        ]
        return Response(
            {
                "categories": categories,
                "conditions": [
                    {"value": value, "label": str(label)}
                    for value, label in Listing.Condition.choices
                ],
                "currencies": [
                    {"value": value, "label": str(label)}
                    for value, label in Listing.Currency.choices
                ],
                "labels": {
                    "title": _("Ongeraho icyo ugurisha"),
                    "category": _("Ubwoko"),
                    "name": _("Izina"),
                    "description": _("Ibisobanuro"),
                    "condition": _("Uko bimeze"),
                    "district": _("Akarere"),
                    "sector": _("Umurenge"),
                    "price": _("Igiciro"),
                    "currency": _("Ifaranga"),
                    "images": _("Amafoto"),
                    "add_images": _("Ongeraho amafoto"),
                    "image_help": _("Ifoto ya mbere niyo izagaragara imbere."),
                    "submit": _("Ohereza"),
                    "cancel": _("Reka"),
                    "success": _("Icyo ugurisha cyashyizwe ahagaragara."),
                    "remove_preview": _("Kuraho ifoto"),
                    "loading": _("Birimo koherezwa..."),
                },
            },
            headers={"Cache-Control": "private, no-store"},
        )

    form = ListingForm(request.data)
    if not form.is_valid():
        return Response(
            {
                "detail": _("Reba amakosa y'uburanga iyi nyandiko."),
                "errors": {
                    field: [str(error) for error in errors]
                    for field, errors in form.errors.items()
                },
            },
            status=400,
            headers={"Cache-Control": "private, no-store"},
        )

    images = request.FILES.getlist("images")
    image_errors = validate_listing_images(images)
    if image_errors:
        return Response(
            {
                "detail": _("Reba amakosa y'uburanga iyi nyandiko."),
                "errors": {"images": image_errors},
            },
            status=400,
            headers={"Cache-Control": "private, no-store"},
        )

    created_images = []
    try:
        with transaction.atomic():
            listing = form.save(commit=False)
            listing.seller = request.user
            listing.save()
            save_listing_images(
                listing, images, created_images, cover_first_image=True
            )
    except Exception:
        cleanup_uploaded_listing_images(created_images)
        raise

    return Response(
        {
            "detail": _("Icyo ugurisha cyashyizwe ahagaragara."),
            "listing": {
                "id": listing.pk,
                "url": listing.get_absolute_url(),
            },
        },
        status=201,
        headers={"Cache-Control": "private, no-store"},
    )


@api_view(["GET", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def seller_listing_edit_api(request, pk):
    """Load or update a listing owned by the authenticated seller."""
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)

    if request.method == "DELETE":
        listing_id = listing.pk
        listing.delete()
        return Response(
            {
                "detail": _("Igicuruzwa cyasibwe."),
                "listing_id": listing_id,
                "statistics": _seller_dashboard_statistics(request.user),
            },
            headers={"Cache-Control": "private, no-store"},
        )

    if request.method == "GET":
        categories = [
            {
                "id": category.pk,
                "name": get_category_display_name(category),
                "slug": category.slug,
            }
            for category in Category.objects.all()
        ]
        return Response(
            {
                "listing": {
                    "id": listing.pk,
                    "category": listing.category_id,
                    "name": listing.name,
                    "description": listing.description,
                    "condition": listing.condition,
                    "district": listing.district,
                    "sector": listing.sector,
                    "price": str(listing.price),
                    "currency": listing.currency,
                    "is_active": listing.is_active,
                    "images": [
                        {
                            "id": image.pk,
                            "url": request.build_absolute_uri(image.image.url),
                            "is_cover": image.is_cover,
                        }
                        for image in listing.images.order_by("pk")
                    ],
                },
                "categories": categories,
                "conditions": [
                    {"value": value, "label": str(label)}
                    for value, label in Listing.Condition.choices
                ],
                "currencies": [
                    {"value": value, "label": str(label)}
                    for value, label in Listing.Currency.choices
                ],
                "labels": {
                    "title": _("Hindura igicuruzwa"),
                    "category": _("Ubwoko"),
                    "name": _("Izina"),
                    "description": _("Ibisobanuro"),
                    "condition": _("Uko bimeze"),
                    "district": _("Akarere"),
                    "sector": _("Umurenge"),
                    "price": _("Igiciro"),
                    "currency": _("Ifaranga"),
                    "existing_images": _("Amafoto asanzwe"),
                    "remove_image": _("Kuraho ifoto"),
                    "cover": _("Ifoto y'imbere"),
                    "images": _("Ongeraho andi mafoto"),
                    "image_help": _("Ifoto ya mbere niyo izagaragara imbere."),
                    "submit": _("Bika impinduka"),
                    "cancel": _("Reka"),
                    "loading": _("Birimo kubikwa..."),
                },
            },
            headers={"Cache-Control": "private, no-store"},
        )

    form = ListingForm(request.data, instance=listing)
    if not form.is_valid():
        return Response(
            {
                "detail": _("Reba amakosa y'uburanga iyi nyandiko."),
                "errors": {
                    field: [str(error) for error in errors]
                    for field, errors in form.errors.items()
                },
            },
            status=400,
            headers={"Cache-Control": "private, no-store"},
        )

    remove_ids = []
    if hasattr(request.data, "getlist"):
        remove_ids = request.data.getlist("remove_images")
    elif isinstance(request.data, dict):
        remove_ids = request.data.get("remove_images", [])
        if isinstance(remove_ids, (str, int)):
            remove_ids = [str(remove_ids)]

    images = request.FILES.getlist("images")
    image_errors = validate_listing_images(images)
    if image_errors:
        return Response(
            {
                "detail": _("Reba amakosa y'uburanga iyi nyandiko."),
                "errors": {"images": image_errors},
            },
            status=400,
            headers={"Cache-Control": "private, no-store"},
        )

    created_images = []
    try:
        with transaction.atomic():
            form.save()
            if remove_ids:
                listing.images.filter(pk__in=remove_ids).delete()

            has_cover = ensure_listing_cover(listing)
            save_listing_images(
                listing,
                images,
                created_images,
                cover_first_image=not has_cover,
            )
    except Exception:
        cleanup_uploaded_listing_images(created_images)
        raise

    return Response(
        {
            "detail": _("Impinduka zabitswe."),
            "listing": {
                "id": listing.pk,
                "url": listing.get_absolute_url(),
            },
        },
        headers={"Cache-Control": "private, no-store"},
    )


@api_view(["PATCH"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def seller_listing_status_api(request, pk):
    """Activate or hide a listing owned by the authenticated seller."""
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)
    serializer = SellerListingStatusSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {
                "detail": _("Hitamo niba igicuruzwa kigaragara cyangwa gihishwe."),
                "errors": serializer.errors,
            },
            status=400,
            headers={"Cache-Control": "private, no-store"},
        )

    listing.is_active = serializer.validated_data["is_active"]
    listing.save(update_fields=["is_active", "updated_at"])
    return Response(
        {
            "is_active": listing.is_active,
            "status": "active" if listing.is_active else "inactive",
            "detail": (
                _("Igicuruzwa kiragaragara ubu.")
                if listing.is_active
                else _("Igicuruzwa cyahishwe.")
            ),
        },
        headers={"Cache-Control": "private, no-store"},
    )
