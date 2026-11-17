from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from trust.models import Review

from .forms import ListingSearchForm
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
            for image in listing.images.all()
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
