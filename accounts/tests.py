from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RegistrationTests(TestCase):
    def _valid_payload(self, **overrides):
        payload = {
            "username": "newseller",
            "email": "newseller@example.com",
            "phone_number": "+250788111111",
            "whatsapp_number": "+250788111111",
            "password1": "a-strong-passw0rd",
            "password2": "a-strong-passw0rd",
            "agree_to_terms": True,
        }
        payload.update(overrides)
        return payload

    def test_register_creates_unverified_user_without_logging_in(self):
        """Signing up no longer logs the user straight in -- they have
        to click the emailed verification link first."""
        response = self.client.post(reverse("accounts:register"), self._valid_payload())
        self.assertRedirects(response, reverse("accounts:verification_sent"))
        user = User.objects.get(username="newseller")
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertFalse(user.email_verified)
        self.assertTrue(user.agreed_to_terms)

    def test_register_sends_verification_email(self):
        from django.core import mail

        self.client.post(reverse("accounts:register"), self._valid_payload())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["newseller@example.com"])

    def test_whatsapp_number_is_required(self):
        response = self.client.post(
            reverse("accounts:register"), self._valid_payload(whatsapp_number="")
        )
        self.assertEqual(response.status_code, 200)  # re-rendered with an error, not redirected
        self.assertFalse(User.objects.filter(username="newseller").exists())

    def test_phone_number_is_required(self):
        response = self.client.post(
            reverse("accounts:register"), self._valid_payload(phone_number="")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newseller").exists())

    def test_email_is_required(self):
        response = self.client.post(
            reverse("accounts:register"), self._valid_payload(email="")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newseller").exists())

    def test_agreeing_to_terms_is_required(self):
        """A first-time visitor can't create an account without
        checking the terms/privacy-policy checkbox -- omitting the
        field entirely (as an unchecked HTML checkbox does; browsers
        don't submit a value for it at all) must not create the user."""
        payload = self._valid_payload()
        del payload["agree_to_terms"]
        response = self.client.post(reverse("accounts:register"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newseller").exists())


class EmailVerificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="unverified",
            password="correct-password",
            email="unverified@example.com",
            phone_number="+250788555555",
            whatsapp_number="+250788555555",
        )
        # create_user doesn't set email_verified, so it uses the model
        # field's own default (False) -- confirmed explicitly here so
        # this test's intent doesn't quietly depend on that default.
        self.user.email_verified = False
        self.user.save()

    def _verify_url(self):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        from accounts.tokens import email_verification_token

        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = email_verification_token.make_token(self.user)
        return reverse("accounts:verify_email", args=[uidb64, token])

    def test_unverified_user_cannot_log_in(self):
        response = self.client.post(
            reverse("login"),
            {"username": "unverified", "password": "correct-password"},
        )
        self.assertEqual(response.status_code, 200)  # re-rendered with an error
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_valid_link_verifies_and_logs_in(self):
        response = self.client.get(self._verify_url())
        self.assertRedirects(response, reverse("core:home"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_link_only_works_once(self):
        url = self._verify_url()
        self.client.get(url)  # first click verifies successfully
        self.client.logout()
        second_response = self.client.get(url)  # replaying the same link
        self.assertTemplateUsed(second_response, "registration/verification_invalid.html")

    def test_garbage_token_shows_invalid_page(self):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(
            reverse("accounts:verify_email", args=[uidb64, "not-a-real-token"])
        )
        self.assertTemplateUsed(response, "registration/verification_invalid.html")

    def test_resend_does_not_reveal_whether_email_exists(self):
        """Same redirect whether or not the address is a real,
        unverified account -- so this can't be used to check who's
        registered on KazeB."""
        real = self.client.post(
            reverse("accounts:resend_verification"), {"email": "unverified@example.com"}
        )
        fake = self.client.post(
            reverse("accounts:resend_verification"), {"email": "nobody@example.com"}
        )
        self.assertRedirects(real, reverse("accounts:verification_sent"))
        self.assertRedirects(fake, reverse("accounts:verification_sent"))

    def test_resend_email_lookup_is_case_insensitive(self):
        from django.core import mail

        response = self.client.post(
            reverse("accounts:resend_verification"),
            {"email": "UNVERIFIED@example.com"},
        )

        self.assertRedirects(response, reverse("accounts:verification_sent"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["unverified@example.com"])


class DeleteAccountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="deleteme",
            password="correct-password",
            phone_number="+250788222222",
            whatsapp_number="+250788222222",
        )

    def test_requires_login(self):
        response = self.client.get(reverse("accounts:delete_account"))
        self.assertEqual(response.status_code, 302)

    def test_wrong_password_does_not_delete(self):
        self.client.login(username="deleteme", password="correct-password")
        response = self.client.post(reverse("accounts:delete_account"), {"password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="deleteme").exists())

    def test_correct_password_deletes_account(self):
        self.client.login(username="deleteme", password="correct-password")
        response = self.client.post(
            reverse("accounts:delete_account"), {"password": "correct-password"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username="deleteme").exists())


class EditAccountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="editme",
            password="correct-password",
            email="editme@example.com",
            phone_number="+250788333333",
            whatsapp_number="+250788333333",
        )

    def test_requires_login(self):
        response = self.client.get(reverse("accounts:edit_account"))
        self.assertEqual(response.status_code, 302)

    def test_updates_profile_fields(self):
        self.client.login(username="editme", password="correct-password")
        response = self.client.post(
            reverse("accounts:edit_account"),
            {
                "email": "new-email@example.com",
                "phone_number": "+250788444444",
                "whatsapp_number": "+250788444444",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new-email@example.com")
        self.assertEqual(self.user.phone_number, "+250788444444")

    def test_email_change_requires_verification_of_new_address(self):
        from django.core import mail

        self.user.email_verified = True
        self.user.save(update_fields=["email_verified"])
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:edit_account"),
            {
                "email": "new-email@example.com",
                "phone_number": "+250788444444",
                "whatsapp_number": "+250788444444",
            },
        )

        self.assertRedirects(response, reverse("accounts:verification_sent"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new-email@example.com")
        self.assertFalse(self.user.email_verified)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["new-email@example.com"])
