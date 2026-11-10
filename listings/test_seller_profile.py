from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Category, Listing

User = get_user_model()


class SellerProfileTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="profile-seller",
            password="test-password",
            email="private-seller@example.com",
            first_name="Amina",
            last_name="Mutesi",
            phone_number="+250788000000",
            whatsapp_number="+250788000000",
            location="Kigali",
            bio="Quality goods for sale.",
        )
        self.category = Category.objects.create(name="Test category")
        self.active_listing = Listing.objects.create(
            seller=self.seller,
            category=self.category,
            name="Active product",
            description="A public product.",
            district="Gasabo",
            sector="Kimironko",
            price=Decimal("5000"),
        )
        Listing.objects.create(
            seller=self.seller,
            category=self.category,
            name="Hidden product",
            description="An inactive product.",
            district="Gasabo",
            sector="Kimironko",
            price=Decimal("2000"),
            is_active=False,
        )

    def test_public_profile_shows_seller_and_only_active_listings(self):
        response = self.client.get(reverse("seller_profile", args=[self.seller.username]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Amina Mutesi")
        self.assertContains(response, "Kigali")
        self.assertContains(response, "Quality goods for sale.")
        self.assertContains(response, "Active product")
        self.assertNotContains(response, "Hidden product")
        self.assertNotContains(response, self.seller.email)
        self.assertEqual(response.context["active_listings_count"], 1)

    def test_public_profile_has_safe_optional_information_fallbacks(self):
        seller = User.objects.create_user(
            username="minimal-profile",
            password="test-password",
        )
        response = self.client.get(reverse("seller_profile", args=[seller.username]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "minimal-profile")
        self.assertContains(response, "ntiyashyizeho ibisobanuro")
        self.assertContains(response, "nta gicuruzwa kiri ku isoko")
        self.assertContains(response, "nta buryo bwo kuvugana na we")

    def test_profile_links_from_listing_card_and_detail(self):
        profile_url = reverse("seller_profile", args=[self.seller.username])
        card_response = self.client.get(reverse("listings:search"))
        detail_response = self.client.get(
            reverse("listings:listing_detail", args=[self.active_listing.pk])
        )

        self.assertContains(card_response, f'href="{profile_url}"')
        self.assertContains(detail_response, f'href="{profile_url}"')

    def test_profile_returns_404_for_unknown_seller(self):
        response = self.client.get(reverse("seller_profile", args=["not-a-seller"]))
        self.assertEqual(response.status_code, 404)

    def test_public_api_returns_only_public_profile_and_active_listing_data(self):
        response = self.client.get(reverse("seller_profile_api", args=[self.seller.username]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["display_name"], "Amina Mutesi")
        self.assertEqual(payload["location"], "Kigali")
        self.assertEqual(payload["active_listings_count"], 1)
        self.assertEqual([item["title"] for item in payload["listings"]], ["Active product"])
        self.assertNotIn("email", payload)
        self.assertNotIn("password", payload)
        self.assertNotIn("email", response.content.decode())
        self.assertNotIn(self.seller.email, response.content.decode())

    def test_public_api_returns_json_404_for_unknown_seller(self):
        response = self.client.get(reverse("seller_profile_api", args=["not-a-seller"]))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Seller not found."})
