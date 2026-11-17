from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from listings.models import Category, Listing


class HomepageApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="seller",
            password="test-password",
        )
        self.category = Category.objects.create(name="Vehicles", order=1)
        self.listing = Listing.objects.create(
            seller=self.user,
            category=self.category,
            name="Bicycle",
            description="A used bicycle.",
            condition=Listing.Condition.USED,
            district="Kigali",
            sector="Kicukiro",
            price=Decimal("12500"),
            currency=Listing.Currency.RWF,
        )

    def test_home_api_returns_existing_categories_and_recent_listings(self):
        response = self.client.get("/api/home/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        payload = response.json()
        self.assertEqual(payload["user"]["is_authenticated"], False)
        self.assertEqual(payload["categories"][0]["id"], self.category.pk)
        self.assertEqual(payload["categories"][0]["url"], "/listings/category/vehicles/")
        self.assertEqual(payload["recent_listings"][0]["id"], self.listing.pk)
        self.assertEqual(payload["recent_listings"][0]["price"], "12,500 RWF")
        self.assertEqual(payload["recent_listings"][0]["seller"]["username"], "seller")

    def test_home_api_reports_the_existing_django_session(self):
        self.client.force_login(self.user)

        response = self.client.get("/api/home/")

        self.assertTrue(response.json()["user"]["is_authenticated"])

    def test_csrf_api_sets_cookie_and_token_for_same_origin_forms(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get("/api/csrf/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)
        token = response.json()["csrfToken"]
        language_response = client.post(
            "/i18n/setlang/",
            {"language": "en", "next": "/"},
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="http://testserver",
        )

        self.assertEqual(language_response.status_code, 302)
