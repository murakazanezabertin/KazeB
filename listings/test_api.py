from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from trust.models import Review

from .models import Category, Favorite, Listing, ListingImage

User = get_user_model()


class ListingApiTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="api-seller",
            password="test-password",
            phone_number="+250788000000",
            whatsapp_number="+250788000000",
        )
        self.buyer = User.objects.create_user(username="api-buyer", password="test-password")
        self.category = Category.objects.create(name="Phones")
        self.other_category = Category.objects.create(name="Vehicles")
        self.listing = Listing.objects.create(
            seller=self.seller,
            category=self.category,
            name="Used phone",
            description="A working phone.",
            condition=Listing.Condition.USED,
            district="Kigali",
            sector="Kicukiro",
            price=Decimal("12500"),
        )
        self.cheaper = Listing.objects.create(
            seller=self.seller,
            category=self.category,
            name="New phone",
            description="A new phone.",
            condition=Listing.Condition.NEW,
            district="Huye",
            sector="Ngoma",
            price=Decimal("10000"),
        )
        self.hidden = Listing.objects.create(
            seller=self.seller,
            category=self.category,
            name="Hidden phone",
            description="Not for sale.",
            district="Kigali",
            sector="Kicukiro",
            price=Decimal("5000"),
            is_active=False,
        )

    def test_browse_api_combines_category_search_location_condition_and_price_sort(self):
        response = self.client.get(
            reverse("listing_browse_api"),
            {
                "category": self.category.slug,
                "q": "phone",
                "location": "Kigali",
                "condition": "used",
                "price_sort": "asc",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()["results"]], [self.listing.pk])
        self.assertEqual(response.json()["category"]["slug"], self.category.slug)
        self.assertEqual(response.json()["results"][0]["price"], "12,500 RWF")
        self.assertEqual(response.json()["filters"]["location"], "Kigali")

    def test_browse_api_sorts_and_paginates_active_listings(self):
        for index in range(11):
            Listing.objects.create(
                seller=self.seller,
                category=self.category,
                name=f"Phone {index}",
                description="Phone.",
                district="Gasabo",
                sector="Kimironko",
                price=Decimal("20000") + index,
            )

        first_page = self.client.get(reverse("listing_browse_api"), {"price_sort": "asc"})
        second_page = self.client.get(
            reverse("listing_browse_api"), {"price_sort": "asc", "page": "2"}
        )

        self.assertEqual(len(first_page.json()["results"]), 12)
        self.assertTrue(first_page.json()["pagination"]["has_next"])
        self.assertEqual(second_page.json()["pagination"]["page"], 2)
        self.assertEqual(second_page.json()["pagination"]["count"], 13)
        self.assertEqual(second_page.json()["results"][0]["name"], "Phone 10")
        self.assertNotIn(self.hidden.pk, [item["id"] for item in first_page.json()["results"]])

    def test_detail_api_returns_photos_seller_rating_and_increments_public_views(self):
        ListingImage.objects.create(listing=self.listing, image="listings/phone.jpg", is_cover=True)
        Review.objects.create(reviewer=self.buyer, seller=self.seller, rating=4, comment="Good.")

        response = self.client.get(reverse("listing_detail_api", args=[self.listing.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["images"][0]["url"], "/media/listings/phone.jpg")
        self.assertEqual(payload["seller"]["rating"], 4.0)
        self.assertEqual(payload["seller"]["review_count"], 1)
        self.assertFalse(payload["is_owner"])
        self.assertEqual(payload["views_count"], 1)
        self.assertEqual(payload["seller"]["phone_number"], self.seller.phone_number)

    def test_detail_api_owner_does_not_increment_views_and_reports_favorite(self):
        Favorite.objects.create(user=self.buyer, listing=self.listing)
        self.client.force_login(self.seller)

        response = self.client.get(reverse("listing_detail_api", args=[self.listing.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_owner"])
        self.assertFalse(response.json()["is_favorited"])
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.views_count, 0)

    def test_detail_api_reports_authenticated_buyers_favorite(self):
        Favorite.objects.create(user=self.buyer, listing=self.listing)
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("listing_detail_api", args=[self.listing.pk]))

        self.assertTrue(response.json()["is_favorited"])

    def test_inactive_listings_are_absent_from_browse_and_detail_apis(self):
        browse_response = self.client.get(reverse("listing_browse_api"))
        detail_response = self.client.get(reverse("listing_detail_api", args=[self.hidden.pk]))

        self.assertNotIn(self.hidden.pk, [item["id"] for item in browse_response.json()["results"]])
        self.assertEqual(detail_response.status_code, 404)

    def test_unknown_category_returns_not_found(self):
        response = self.client.get(reverse("listing_browse_api"), {"category": "missing"})
        self.assertEqual(response.status_code, 404)
