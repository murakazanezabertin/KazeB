from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Category, Favorite, Listing, ListingImage

User = get_user_model()


def make_user(username="seller", **kwargs):
    defaults = {
        "phone_number": "+250788000000",
        "whatsapp_number": "+250788000000",
    }
    defaults.update(kwargs)
    return User.objects.create_user(username=username, password="testpass123", **defaults)


def make_category(name="Vehicles"):
    return Category.objects.create(name=name)


def make_listing(seller, category, **kwargs):
    defaults = {
        "name": "Test car",
        "description": "A car for sale.",
        "district": "Gasabo",
        "sector": "Kimironko",
        "price": Decimal("5000"),
    }
    defaults.update(kwargs)
    return Listing.objects.create(seller=seller, category=category, **defaults)


class ListingModelTests(TestCase):
    def setUp(self):
        self.seller = make_user()
        self.category = make_category()

    def test_display_price_rwf(self):
        listing = make_listing(self.seller, self.category, price=Decimal("5000"), currency="RWF")
        self.assertEqual(listing.display_price, "5,000 RWF")

    def test_display_price_usd(self):
        listing = make_listing(self.seller, self.category, price=Decimal("20"), currency="USD")
        self.assertEqual(listing.display_price, "$20.00")

    def test_cover_image_prefers_flagged_cover(self):
        listing = make_listing(self.seller, self.category)
        first = ListingImage.objects.create(listing=listing, image="listings/a.jpg", is_cover=False)
        cover = ListingImage.objects.create(listing=listing, image="listings/b.jpg", is_cover=True)
        self.assertEqual(listing.cover_image.pk, cover.pk)

    def test_cover_image_falls_back_to_first_when_no_flagged_cover(self):
        listing = make_listing(self.seller, self.category)
        first = ListingImage.objects.create(listing=listing, image="listings/a.jpg", is_cover=False)
        self.assertEqual(listing.cover_image.pk, first.pk)

    def test_cover_image_none_when_no_photos(self):
        listing = make_listing(self.seller, self.category)
        self.assertIsNone(listing.cover_image)

    def test_category_slug_auto_generated(self):
        category = make_category("Houses for rent")
        self.assertEqual(category.slug, "houses-for-rent")


class ListingViewAccessTests(TestCase):
    """Access control: a seller can only edit/delete their OWN
    listings, never someone else's, even if logged in."""

    def setUp(self):
        self.owner = make_user("owner")
        self.other = make_user("other")
        self.category = make_category()
        self.listing = make_listing(self.owner, self.category)

    def test_listing_detail_is_public(self):
        response = self.client.get(reverse("listings:listing_detail", args=[self.listing.pk]))
        self.assertEqual(response.status_code, 200)

    def test_edit_requires_login(self):
        response = self.client.get(reverse("listings:listing_edit", args=[self.listing.pk]))
        self.assertEqual(response.status_code, 302)  # redirected to login

    def test_edit_rejects_non_owner(self):
        self.client.login(username="other", password="testpass123")
        response = self.client.get(reverse("listings:listing_edit", args=[self.listing.pk]))
        self.assertEqual(response.status_code, 404)  # owner-only lookup, not just hidden

    def test_edit_allows_owner(self):
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(reverse("listings:listing_edit", args=[self.listing.pk]))
        self.assertEqual(response.status_code, 200)

    def test_delete_rejects_non_owner(self):
        self.client.login(username="other", password="testpass123")
        response = self.client.post(reverse("listings:listing_delete", args=[self.listing.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Listing.objects.filter(pk=self.listing.pk).exists())

    def test_delete_allows_owner_and_removes_listing(self):
        self.client.login(username="owner", password="testpass123")
        response = self.client.post(reverse("listings:listing_delete", args=[self.listing.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Listing.objects.filter(pk=self.listing.pk).exists())

    def test_viewing_own_listing_does_not_increment_views(self):
        self.client.login(username="owner", password="testpass123")
        self.client.get(reverse("listings:listing_detail", args=[self.listing.pk]))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.views_count, 0)

    def test_viewing_others_listing_increments_views(self):
        self.client.login(username="other", password="testpass123")
        self.client.get(reverse("listings:listing_detail", args=[self.listing.pk]))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.views_count, 1)


class SearchViewTests(TestCase):
    def setUp(self):
        self.seller = make_user()
        self.category = make_category()
        self.cheap = make_listing(self.seller, self.category, name="Cheap phone", price=Decimal("100"))
        self.expensive = make_listing(self.seller, self.category, name="Expensive laptop", price=Decimal("2000"))

    def test_search_matches_name(self):
        response = self.client.get(reverse("listings:search"), {"q": "laptop"})
        self.assertContains(response, "Expensive laptop")
        self.assertNotContains(response, "Cheap phone")

    def test_sort_price_ascending(self):
        response = self.client.get(reverse("listings:search"), {"price_sort": "asc"})
        page = list(response.context["page_obj"])
        self.assertEqual([listing.pk for listing in page], [self.cheap.pk, self.expensive.pk])

    def test_sort_price_descending(self):
        response = self.client.get(reverse("listings:search"), {"price_sort": "desc"})
        page = list(response.context["page_obj"])
        self.assertEqual([listing.pk for listing in page], [self.expensive.pk, self.cheap.pk])

    def test_price_sort_overrides_date_sort(self):
        response = self.client.get(
            reverse("listings:search"), {"sort": "oldest", "price_sort": "desc"}
        )
        page = list(response.context["page_obj"])
        self.assertEqual([listing.pk for listing in page], [self.expensive.pk, self.cheap.pk])

    def test_sort_oldest_first(self):
        response = self.client.get(reverse("listings:search"), {"sort": "oldest"})
        page = list(response.context["page_obj"])
        self.assertEqual([listing.pk for listing in page], [self.cheap.pk, self.expensive.pk])

    def test_sort_defaults_to_newest_first(self):
        response = self.client.get(reverse("listings:search"))
        page = list(response.context["page_obj"])
        self.assertEqual([listing.pk for listing in page], [self.expensive.pk, self.cheap.pk])

    def test_inactive_listing_hidden_from_search(self):
        self.cheap.is_active = False
        self.cheap.save()
        response = self.client.get(reverse("listings:search"))
        self.assertNotContains(response, "Cheap phone")


class FavoriteTests(TestCase):
    def setUp(self):
        self.seller = make_user(username="owner")
        self.buyer = make_user(username="buyer")
        self.category = make_category()
        self.listing = make_listing(self.seller, self.category)

    def test_requires_login(self):
        response = self.client.post(reverse("listings:toggle_favorite", args=[self.listing.pk]))
        self.assertEqual(response.status_code, 302)

    def test_toggle_adds_and_removes_favorite(self):
        self.client.login(username="buyer", password="testpass123")
        url = reverse("listings:toggle_favorite", args=[self.listing.pk])

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Favorite.objects.filter(user=self.buyer, listing=self.listing).exists())

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Favorite.objects.filter(user=self.buyer, listing=self.listing).exists())

    def test_favorites_page_lists_saved_listings(self):
        Favorite.objects.create(user=self.buyer, listing=self.listing)
        self.client.login(username="buyer", password="testpass123")
        response = self.client.get(reverse("listings:favorites"))
        self.assertContains(response, self.listing.name)
