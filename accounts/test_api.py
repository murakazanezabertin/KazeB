import re
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from listings.models import Category, Favorite, Listing

User = get_user_model()


class AccountApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="api-user",
            password="a-strong-passw0rd",
            email="api-user@example.com",
            phone_number="+250788111111",
            whatsapp_number="+250788111111",
            email_verified=True,
        )

    def csrf_headers(self, client):
        response = client.get("/api/csrf/")
        return {
            "HTTP_X_CSRFTOKEN": response.json()["csrfToken"],
            "HTTP_ORIGIN": "http://testserver",
        }

    def valid_registration(self, **overrides):
        data = {
            "username": "new-api-user",
            "email": "new-api-user@example.com",
            "phone_number": "+250788222222",
            "whatsapp_number": "+250788222222",
            "password1": "a-strong-passw0rd",
            "password2": "a-strong-passw0rd",
            "agree_to_terms": "true",
        }
        data.update(overrides)
        return data

    def test_registration_creates_unverified_user_and_sends_verification_mail(self):
        response = self.client.post(
            reverse("auth_register_api"), self.valid_registration()
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["verification_required"])
        self.assertEqual(len(mail.outbox), 1)
        user = User.objects.get(username="new-api-user")
        self.assertTrue(user.agreed_to_terms)
        self.assertFalse(user.email_verified)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_registration_reuses_existing_validation_and_reports_field_errors(self):
        response = self.client.post(
            reverse("auth_register_api"),
            self.valid_registration(whatsapp_number="", password2="different"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("whatsapp_number", response.json()["errors"])
        self.assertIn("password2", response.json()["errors"])
        self.assertFalse(User.objects.filter(username="new-api-user").exists())

    def test_registration_requires_terms_acceptance(self):
        data = self.valid_registration()
        data.pop("agree_to_terms")

        response = self.client.post(reverse("auth_register_api"), data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("agree_to_terms", response.json()["errors"])

    def test_anonymous_registration_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)

        response = client.post(
            reverse("auth_register_api"), self.valid_registration()
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username="new-api-user").exists())

    def test_login_accepts_email_and_logout_uses_session_authentication(self):
        client = Client(enforce_csrf_checks=True)
        headers = self.csrf_headers(client)
        login_response = client.post(
            reverse("auth_login_api"),
            {"username": self.user.email, "password": "a-strong-passw0rd"},
            **headers,
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.json()["account"]["email_verified"])
        self.assertNotIn("password", login_response.json()["account"])
        self.assertEqual(login_response.json()["redirect_to"], "/")

        headers = self.csrf_headers(client)
        logout_response = client.post(reverse("auth_logout_api"), {}, **headers)

        self.assertEqual(logout_response.status_code, 200)
        self.assertNotIn("_auth_user_id", client.session)

    def test_login_rejects_unverified_accounts(self):
        self.user.email_verified = False
        self.user.save(update_fields=["email_verified"])

        response = self.client.post(
            reverse("auth_login_api"),
            {"username": self.user.username, "password": "a-strong-passw0rd"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("__all__", response.json()["errors"])
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_rejects_csrfless_anonymous_post(self):
        client = Client(enforce_csrf_checks=True)

        response = client.post(
            reverse("auth_login_api"),
            {"username": self.user.username, "password": "a-strong-passw0rd"},
        )

        self.assertEqual(response.status_code, 403)

    def test_resend_verification_is_generic_for_existing_and_unknown_addresses(self):
        self.user.email_verified = False
        self.user.save(update_fields=["email_verified"])

        existing = self.client.post(
            reverse("auth_resend_verification_api"),
            {"email": self.user.email},
        )
        unknown = self.client.post(
            reverse("auth_resend_verification_api"),
            {"email": "missing@example.com"},
        )

        self.assertEqual(existing.status_code, 200)
        self.assertEqual(existing.json(), unknown.json())
        self.assertEqual(len(mail.outbox), 1)

    def test_verification_link_from_registration_logs_user_in(self):
        self.client.post(reverse("auth_register_api"), self.valid_registration())
        verification_url = re.search(
            r"http://testserver(/accounts/verify/[^/\s]+/[^/\s]+/)",
            mail.outbox[0].body,
        )
        self.assertIsNotNone(verification_url)

        response = self.client.get(verification_url.group(1))

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="new-api-user")
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_password_reset_email_and_confirmation_use_django_token_flow(self):
        reset_response = self.client.post(
            reverse("auth_password_reset_api"), {"email": self.user.email}
        )

        self.assertEqual(reset_response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        token_path = re.search(
            r"/accounts/reset/([^/\s]+)/([^/\s]+)/",
            mail.outbox[0].body,
        )
        self.assertIsNotNone(token_path)
        uidb64, token = token_path.groups()
        confirm_response = self.client.post(
            reverse("auth_password_reset_confirm_api", args=[uidb64, token]),
            {
                "new_password1": "another-strong-passw0rd",
                "new_password2": "another-strong-passw0rd",
            },
        )

        self.assertEqual(confirm_response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("another-strong-passw0rd"))

    def test_password_reset_request_does_not_disclose_unknown_emails(self):
        real = self.client.post(
            reverse("auth_password_reset_api"), {"email": self.user.email}
        )
        unknown = self.client.post(
            reverse("auth_password_reset_api"), {"email": "unknown@example.com"}
        )

        self.assertEqual(real.json(), unknown.json())
        self.assertEqual(len(mail.outbox), 1)

    def test_password_reset_rejects_invalid_token(self):
        response = self.client.post(
            reverse("auth_password_reset_confirm_api", args=["bad-uid", "bad-token"]),
            {
                "new_password1": "another-strong-passw0rd",
                "new_password2": "another-strong-passw0rd",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_account_api_requires_authentication_and_never_returns_password(self):
        anonymous = self.client.get(reverse("account_api"))
        self.assertEqual(anonymous.status_code, 401)

        self.client.force_login(self.user)
        response = self.client.get(reverse("account_api"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response.json()["account"]["email"], self.user.email)
        self.assertNotIn("password", response.json()["account"])

    def test_profile_update_reuses_model_form_and_accepts_picture_upload(self):
        output = BytesIO()
        Image.new("RGB", (4, 4), color="orange").save(output, format="PNG")
        upload = SimpleUploadedFile(
            "profile.png", output.getvalue(), content_type="image/png"
        )
        self.client.force_login(self.user)

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse("account_edit_api"),
                {
                    "first_name": "Amina",
                    "last_name": "Mutesi",
                    "email": self.user.email,
                    "location": "Kigali",
                    "bio": "Hello KazeB.",
                    "phone_number": "+250788333333",
                    "whatsapp_number": "+250788333333",
                    "profile_picture": upload,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["account"]["profile_picture"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Amina")
        self.assertEqual(self.user.phone_number, "+250788333333")
        self.assertTrue(self.user.profile_picture.name)

    def test_changing_email_requires_verification_and_logs_out(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("account_edit_api"),
            {
                "first_name": "",
                "last_name": "",
                "email": "new-api-email@example.com",
                "location": "",
                "bio": "",
                "phone_number": self.user.phone_number,
                "whatsapp_number": self.user.whatsapp_number,
            },
        )

        self.assertTrue(response.json()["email_verification_required"])
        self.assertNotIn("_auth_user_id", self.client.session)
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)
        self.assertEqual(self.user.email, "new-api-email@example.com")
        self.assertEqual(mail.outbox[-1].to, ["new-api-email@example.com"])

    def test_profile_update_is_csrf_protected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)

        response = client.post(reverse("account_edit_api"), {"email": self.user.email})

        self.assertEqual(response.status_code, 403)

    def test_delete_requires_correct_password_and_deletes_user(self):
        self.client.force_login(self.user)
        wrong = self.client.post(
            reverse("account_delete_api"), {"password": "wrong-password"}
        )
        self.assertEqual(wrong.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

        response = self.client.post(
            reverse("account_delete_api"), {"password": "a-strong-passw0rd"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_favorites_api_lists_existing_favorites_and_toggles_active_listings(self):
        category = Category.objects.create(name="Account API category")
        listing = Listing.objects.create(
            seller=self.user,
            category=category,
            name="Saved product",
            description="Public listing.",
            district="Kigali",
            sector="Gasabo",
            price="5000",
        )
        hidden = Listing.objects.create(
            seller=self.user,
            category=category,
            name="Hidden saved product",
            description="Inactive listing.",
            district="Kigali",
            sector="Gasabo",
            price="2500",
            is_active=False,
        )
        Favorite.objects.create(user=self.user, listing=hidden)
        self.client.force_login(self.user)

        added = self.client.post(
            reverse("favorite_toggle_api", args=[listing.pk])
        )
        self.assertTrue(added.json()["is_favorited"])

        response = self.client.get(reverse("favorites_api"))
        results = response.json()["results"]
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(len(results), 2)
        self.assertIn(
            False,
            [favorite["is_active"] for favorite in results],
        )

        removed = self.client.post(
            reverse("favorite_toggle_api", args=[listing.pk])
        )
        self.assertFalse(removed.json()["is_favorited"])
        self.assertTrue(Favorite.objects.filter(user=self.user, listing=hidden).exists())

    def test_favorite_toggle_can_remove_inactive_saved_listing_but_not_add_it(self):
        category = Category.objects.create(name="Hidden API category")
        listing = Listing.objects.create(
            seller=self.user,
            category=category,
            name="Hidden product",
            description="Inactive.",
            district="Kigali",
            sector="Gasabo",
            price="5000",
            is_active=False,
        )
        self.client.force_login(self.user)

        unavailable = self.client.post(reverse("favorite_toggle_api", args=[listing.pk]))
        self.assertEqual(unavailable.status_code, 404)

        Favorite.objects.create(user=self.user, listing=listing)
        removed = self.client.post(reverse("favorite_toggle_api", args=[listing.pk]))
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(Favorite.objects.filter(user=self.user, listing=listing).exists())

    def test_favorites_require_authentication_and_csrf(self):
        self.assertEqual(self.client.get(reverse("favorites_api")).status_code, 401)

        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(
            reverse("favorite_toggle_api", args=[1]),
        )
        self.assertEqual(response.status_code, 403)
