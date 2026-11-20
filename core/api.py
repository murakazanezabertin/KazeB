from django.middleware.csrf import get_token
from django.templatetags.static import static
from django.utils.translation import get_language, gettext as _
from django.views.decorators.csrf import ensure_csrf_cookie

from chat.context_processors import unread_messages
from listings.models import Category, Listing
from listings.templatetags.category_extras import (
    DEFAULT_ICONS,
    get_category_display_name,
)
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class HomepageLabelsSerializer(serializers.Serializer):
    home = serializers.CharField()
    welcome_prefix = serializers.CharField()
    hero_title_line_1 = serializers.CharField()
    hero_title_line_2 = serializers.CharField()
    hero_title_line_3 = serializers.CharField()
    hero_title_line_4 = serializers.CharField()
    hero_title_line_5 = serializers.CharField()
    hero_buyer_cta = serializers.CharField()
    hero_seller_cta = serializers.CharField()
    brand_tagline = serializers.CharField()
    add_listing = serializers.CharField()
    search_placeholder = serializers.CharField()
    search = serializers.CharField()
    login = serializers.CharField()
    register = serializers.CharField()
    my_account = serializers.CharField()
    account = serializers.CharField()
    favorites = serializers.CharField()
    messages = serializers.CharField()
    categories = serializers.CharField()
    recent_listings = serializers.CharField()
    about = serializers.CharField()
    faq = serializers.CharField()
    safety = serializers.CharField()
    terms = serializers.CharField()
    privacy = serializers.CharField()
    contact = serializers.CharField()
    follow = serializers.CharField()
    footer_tagline = serializers.CharField()
    change_language = serializers.CharField()
    sign_out = serializers.CharField()
    empty_image = serializers.CharField()
    empty_categories = serializers.CharField()
    page_not_found = serializers.CharField()
    loading = serializers.CharField()
    all_listings = serializers.CharField()
    all_conditions = serializers.CharField()
    new_condition = serializers.CharField()
    used_condition = serializers.CharField()
    newest = serializers.CharField()
    oldest = serializers.CharField()
    most_viewed = serializers.CharField()
    all_prices = serializers.CharField()
    lowest_price = serializers.CharField()
    highest_price = serializers.CharField()
    previous_page = serializers.CharField()
    next_page = serializers.CharField()
    no_results = serializers.CharField()
    listing_views = serializers.CharField()
    no_reviews = serializers.CharField()
    posted_by = serializers.CharField()
    phone_verified = serializers.CharField()
    save_favorite = serializers.CharField()
    saved_favorite = serializers.CharField()
    report_listing = serializers.CharField()
    contact_seller = serializers.CharField()
    send_message = serializers.CharField()
    login_to_message = serializers.CharField()
    whatsapp_seller = serializers.CharField()
    copy_listing_link = serializers.CharField()
    copy_phone = serializers.CharField()
    call_seller = serializers.CharField()
    joined_kazeb = serializers.CharField()
    seller_listing_count = serializers.CharField()
    seller_bio = serializers.CharField()
    no_seller_bio = serializers.CharField()
    seller_listings = serializers.CharField()
    no_seller_listings = serializers.CharField()
    no_contact_options = serializers.CharField()
    edit_listing = serializers.CharField()
    delete_listing = serializers.CharField()
    share_listing = serializers.CharField()


class HomepageCategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    url = serializers.CharField()
    icon = serializers.CharField(allow_null=True)


class HomepageSellerSerializer(serializers.Serializer):
    username = serializers.CharField()
    name = serializers.CharField()
    url = serializers.CharField()
    image = serializers.CharField(allow_null=True)


class HomepageListingSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    url = serializers.CharField()
    image = serializers.CharField(allow_null=True)
    price = serializers.CharField()
    location = serializers.CharField()
    seller = HomepageSellerSerializer()


class HomepageUserSerializer(serializers.Serializer):
    is_authenticated = serializers.BooleanField()
    unread_message_count = serializers.IntegerField()


class HomepageSerializer(serializers.Serializer):
    language = serializers.CharField()
    labels = HomepageLabelsSerializer()
    user = HomepageUserSerializer()
    categories = HomepageCategorySerializer(many=True)
    recent_listings = HomepageListingSerializer(many=True)


def _homepage_payload(request):
    categories = []
    for category in Category.objects.all():
        icon_url = category.icon.url if category.icon else None
        if not icon_url and category.slug in DEFAULT_ICONS:
            icon_url = static(DEFAULT_ICONS[category.slug])

        categories.append(
            {
                "id": category.pk,
                "name": get_category_display_name(category),
                "slug": category.slug,
                "url": category.get_absolute_url(),
                "icon": icon_url,
            }
        )

    recent_listings = (
        Listing.objects.filter(
            is_active=True,
            moderation_status=Listing.ModerationStatus.VISIBLE,
        )
        .select_related("seller", "category")
        .prefetch_related("images")[:8]
    )
    listings = []
    for listing in recent_listings:
        cover_image = listing.cover_image
        seller = listing.seller
        listings.append(
            {
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
        )

    is_authenticated = request.user.is_authenticated
    return {
        "language": (get_language() or "rw").split("-")[0],
        "labels": {
            "home": _("Ahabanza"),
            "welcome_prefix": _("Murakaza neza kuri"),
            "hero_title_line_1": _("Bona umuguzi"),
            "hero_title_line_2": _("cyangwa"),
            "hero_title_line_3": _("umugurisha"),
            "hero_title_line_4": _("vuba kandi"),
            "hero_title_line_5": _("byoroshye."),
            "hero_buyer_cta": _("Shaka umuguzi nonaha"),
            "hero_seller_cta": _("Shaka umugurisha nonaha"),
            "brand_tagline": _("Gura no kugurisha byoroshye!"),
            "add_listing": _("Ongeraho igicuruzwa"),
            "search_placeholder": _("Shakisha ukurikije aho biherereye..."),
            "search": _("Shakisha"),
            "login": _("Injira"),
            "register": _("Iyandikishe"),
            "my_account": _("Konti yanjye"),
            "account": _("Umwirondoro wanjye"),
            "favorites": _("Ibya kwibuka"),
            "messages": _("Ubutumwa"),
            "categories": _("Shakisha ukurikije ubwoko"),
            "recent_listings": _("Ibiherutse kwandikwa"),
            "about": _("Abo turi bo"),
            "faq": _("Ibibazo bikunze kubazwa"),
            "safety": _("Kwirinda uburiganya"),
            "terms": _("Amabwiriza"),
            "privacy": _("Ibanga"),
            "contact": _("Twandikire"),
            "follow": _("Dukurikire kuri"),
            "footer_tagline": _("Ikiraro gihuza abaguzi n'abagurisha"),
            "change_language": _("Hindura Ururimi"),
            "sign_out": _("Sohoka"),
            "empty_image": _("Nta foto ihari"),
            "empty_categories": _("Nta bwoko burahari."),
            "page_not_found": _("Urupapuro ntirwabashije kuboneka."),
            "loading": _("Birimo gutegurwa..."),
            "all_listings": _("Ibicuruzwa byose"),
            "all_conditions": _("Uko bimeze: byose"),
            "new_condition": _("Gishya"),
            "used_condition": _("Gikoreshejwe"),
            "newest": _("Bishya mbere"),
            "oldest": _("Bishaje mbere"),
            "most_viewed": _("Abarebye benshi"),
            "all_prices": _("Igiciro: byose"),
            "lowest_price": _("Igiciro: gito mbere"),
            "highest_price": _("Igiciro: kinini mbere"),
            "previous_page": _("Ibibanziriza"),
            "next_page": _("Ibikurikira"),
            "no_results": _("Nta gicuruzwa gihuye n'ushaka."),
            "listing_views": _("Abarebye"),
            "no_reviews": _("Nta busuzumire burahari"),
            "posted_by": _("Yashyizweho na"),
            "phone_verified": _("Numero yemejwe"),
            "save_favorite": _("Bika ku bya kwibuka"),
            "saved_favorite": _("Ku bya kwibuka"),
            "report_listing": _("Tanga raporo kuri iki gicuruzwa"),
            "contact_seller": _("Vugana n'ucuruza"),
            "send_message": _("Ohereza ubutumwa kuri KazeB"),
            "login_to_message": _("Injira kugira ngo uvugane n'ucuruza"),
            "whatsapp_seller": _("Vugana n'ucuruza kuri WhatsApp"),
            "copy_listing_link": _("Koporora umurongo"),
            "copy_phone": _("Koporora numero ya telefone"),
            "call_seller": _("Hamagara"),
            "joined_kazeb": _("Yinjiye kuri KazeB"),
            "seller_listing_count": _("Ibicuruzwa biri ku isoko"),
            "seller_bio": _("Ibyo umucuruzi yivugaho"),
            "no_seller_bio": _("Uyu mucuruzi ntiyashyizeho ibisobanuro."),
            "seller_listings": _("Ibicuruzwa by'uyu mucuruzi"),
            "no_seller_listings": _("Uyu mucuruzi nta gicuruzwa kiri ku isoko afite ubu."),
            "no_contact_options": _("Uyu mucuruzi nta buryo bwo kuvugana na we yashyize ahagaragara."),
            "edit_listing": _("Hindura"),
            "delete_listing": _("Siba"),
            "share_listing": _("Sangiza abandi icyo ugurisha"),
        },
        "user": {
            "is_authenticated": is_authenticated,
            "unread_message_count": (
                unread_messages(request).get("unread_message_count", 0)
                if is_authenticated
                else 0
            ),
        },
        "categories": categories,
        "recent_listings": listings,
    }


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def home_api(request):
    serializer = HomepageSerializer(data=_homepage_payload(request))
    serializer.is_valid(raise_exception=True)
    return Response(serializer.data, headers={"Cache-Control": "private, no-store"})


@ensure_csrf_cookie
@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def csrf_api(request):
    response = Response({"csrfToken": get_token(request)})
    response["Cache-Control"] = "no-store"
    return response
