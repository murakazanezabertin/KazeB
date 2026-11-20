import json
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

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

    def test_homepage_keeps_branding_tagline_categories_and_carousel(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Murakaza neza kuri")
        self.assertContains(response, 'class="kazeb-logo-black">Kaze</span>')
        self.assertContains(response, 'class="kazeb-logo-orange">B</span>')
        self.assertContains(response, "Ikiraro gihuza abaguzi n'abagurisha")
        page = response.content.decode()
        self.assertLess(page.index("kazeb-welcome-tagline"), page.index("homepage-search"))
        self.assertLess(page.index("homepage-search"), page.index("kazeb-hero"))
        self.assertEqual(page.count('name="q"'), 1)
        self.assertContains(response, self.category.get_absolute_url())
        self.assertContains(response, "data-kazeb-carousel")
        self.assertContains(response, "images/hero/car.png")

    def test_api_translations_follow_language_switches(self):
        language_response = self.client.post(
            "/i18n/setlang/",
            {"language": "en", "next": "/seller/seller/?page=2"},
        )
        self.assertEqual(language_response["Location"], "/seller/seller/?page=2")

        english_home = self.client.get("/api/home/").json()["labels"]
        english_auth = self.client.get("/api/auth/ui/").json()
        english_page = self.client.get("/")

        self.assertContains(english_page, "Welcome to")
        self.assertContains(english_page, 'class="kazeb-logo-black">Kaze</span>')
        self.assertContains(english_page, "Find a buyer<br>or<br>a seller")
        self.assertContains(english_page, "Buy and sell with ease!")
        self.assertEqual(english_home["welcome_prefix"], "Welcome to")
        self.assertEqual(english_home["hero_title_line_1"], "Find a buyer")
        self.assertEqual(english_home["hero_buyer_cta"], "Find a buyer now")
        self.assertEqual(english_home["brand_tagline"], "Buy and sell with ease!")
        self.assertEqual(english_home["call_seller"], "Call")
        self.assertEqual(english_home["seller_bio"], "About the seller")
        self.assertEqual(english_home["my_account"], "My account")
        self.assertEqual(english_home["account"], "My profile")
        self.assertEqual(english_auth["labels"]["resend"], "Resend")
        self.assertEqual(english_auth["labels"]["account"], "My profile")
        self.assertEqual(english_auth["labels"]["account_details"], "My profile")
        self.assertEqual(english_auth["account_fields"]["last_name"], "Last name")

        self.client.post("/i18n/setlang/", {"language": "fr", "next": "/"})

        french_home = self.client.get("/api/home/").json()["labels"]
        french_auth = self.client.get("/api/auth/ui/").json()
        french_page = self.client.get("/")

        self.assertContains(french_page, "Bienvenue sur")
        self.assertContains(french_page, 'class="kazeb-logo-black">Kaze</span>')
        self.assertContains(french_page, "Trouvez un acheteur<br>ou<br>un vendeur")
        self.assertContains(french_page, "Achetez et vendez facilement !")
        self.assertEqual(french_home["welcome_prefix"], "Bienvenue sur")
        self.assertEqual(french_home["hero_title_line_1"], "Trouvez un acheteur")
        self.assertEqual(french_home["hero_buyer_cta"], "Trouvez un acheteur maintenant")
        self.assertEqual(french_home["brand_tagline"], "Achetez et vendez facilement !")
        self.assertEqual(french_home["call_seller"], "Appeler")
        self.assertEqual(french_home["seller_bio"], "À propos du vendeur")
        self.assertEqual(french_home["my_account"], "Mon compte")
        self.assertEqual(french_home["account"], "Mon profil")
        self.assertEqual(french_auth["labels"]["resend"], "Renvoyer")
        self.assertEqual(french_auth["labels"]["account"], "Mon profil")
        self.assertEqual(french_auth["labels"]["account_details"], "Mon profil")
        self.assertEqual(french_auth["account_fields"]["last_name"], "Nom de famille")

        self.client.post("/i18n/setlang/", {"language": "rw", "next": "/"})
        kinyarwanda_home = self.client.get("/api/home/").json()["labels"]
        kinyarwanda_auth = self.client.get("/api/auth/ui/").json()

        self.assertEqual(kinyarwanda_home["my_account"], "Konti yanjye")
        self.assertEqual(kinyarwanda_home["account"], "Umwirondoro wanjye")
        self.assertEqual(kinyarwanda_auth["labels"]["account"], "Umwirondoro wanjye")
        self.assertEqual(kinyarwanda_auth["labels"]["account_details"], "Umwirondoro wanjye")

    def test_authenticated_navigation_has_one_link_to_each_account_page(self):
        self.client.force_login(self.user)

        response = self.client.get("/")
        navigation = response.content.split(b"</nav>", 1)[0]

        self.assertEqual(navigation.count(b'href="/listings/dashboard/"'), 1)
        self.assertEqual(navigation.count(b'href="/accounts/profile/"'), 1)
        self.assertContains(response, "Konti yanjye")
        self.assertContains(response, "Umwirondoro wanjye")

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


class AccountProfilePageTests(TestCase):
    def test_existing_profile_path_serves_the_react_account_page(self):
        with TemporaryDirectory() as temporary_directory:
            manifest_path = (
                Path(temporary_directory)
                / "static"
                / "react"
                / ".vite"
                / "manifest.json"
            )
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "index.html": {
                            "file": "assets/app.js",
                            "css": ["assets/app.css"],
                        }
                    }
                ),
                encoding="utf-8",
            )
            with patch("core.views.settings.BASE_DIR", Path(temporary_directory)):
                response = self.client.get(reverse("core:account_profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>Umwirondoro wanjye · KazeB</title>")
        self.assertContains(response, "/static/react/assets/app.js")
