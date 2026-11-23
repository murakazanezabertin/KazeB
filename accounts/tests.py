from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from accounts.models import EmailVerificationCode

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
        to enter the emailed verification code first."""
        response = self.client.post(reverse("accounts:register"), self._valid_payload())
        self.assertRedirects(response, reverse("accounts:verify_code"))
        user = User.objects.get(username="newseller")
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertFalse(user.email_verified)
        self.assertTrue(user.agreed_to_terms)

    def test_register_sends_verification_email_with_code(self):
        self.client.post(reverse("accounts:register"), self._valid_payload())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["newseller@example.com"])
        # Check that email contains a 6-digit code
        body = mail.outbox[0].body
        import re
        codes = re.findall(r'\b\d{6}\b', body)
        self.assertEqual(len(codes), 1)
        self.assertEqual(len(codes[0]), 6)

    def test_whatsapp_number_is_required(self):
        response = self.client.post(
            reverse("accounts:register"), self._valid_payload(whatsapp_number="")
        )
        self.assertEqual(response.status_code, 200)
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


class EmailVerificationCodeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="unverified",
            password="correct-password",
            email="unverified@example.com",
            phone_number="+250788555555",
            whatsapp_number="+250788555555",
        )
        self.user.email_verified = False
        self.user.save()

    def test_generate_code_creates_6_digit_code(self):
        code, evc = EmailVerificationCode.generate_code(self.user)
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        self.assertEqual(evc.user, self.user)
        self.assertIsNotNone(evc.code_hash)
        self.assertIsNotNone(evc.expires_at)
        self.assertEqual(evc.attempts, 0)
        self.assertEqual(evc.max_attempts, 5)
        self.assertIsNone(evc.used_at)

    def test_generate_code_invalidates_previous(self):
        code1, evc1 = EmailVerificationCode.generate_code(self.user)
        code2, evc2 = EmailVerificationCode.generate_code(self.user)
        self.assertNotEqual(code1, code2)
        self.assertEqual(EmailVerificationCode.objects.filter(user=self.user).count(), 1)
        # Old code should not work
        self.assertFalse(evc1.verify_code(code1))
        # New code should work
        self.assertTrue(evc2.verify_code(code2))

    def test_verify_code_success(self):
        code, evc = EmailVerificationCode.generate_code(self.user)
        self.assertTrue(evc.verify_code(code))
        evc.refresh_from_db()
        self.assertIsNotNone(evc.used_at)

    def test_verify_code_failure_increments_attempts(self):
        code, evc = EmailVerificationCode.generate_code(self.user)
        self.assertFalse(evc.verify_code("111111"))
        evc.refresh_from_db()
        self.assertEqual(evc.attempts, 1)

    def test_verify_code_max_attempts(self):
        code, evc = EmailVerificationCode.generate_code(self.user)
        for _ in range(5):
            evc.verify_code("111111")
        evc.refresh_from_db()
        self.assertEqual(evc.attempts, 5)
        self.assertFalse(evc.is_valid())
        # Even correct code should not work after max attempts
        self.assertFalse(evc.verify_code(code))

    def test_verify_code_expired(self):
        code, evc = EmailVerificationCode.generate_code(self.user)
        from django.utils import timezone
        from datetime import timedelta
        evc.expires_at = timezone.now() - timedelta(minutes=1)
        evc.save()
        self.assertFalse(evc.is_valid())
        self.assertFalse(evc.verify_code(code))


class EmailVerificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="unverified",
            password="correct-password",
            email="unverified@example.com",
            phone_number="+250788555555",
            whatsapp_number="+250788555555",
        )
        self.user.email_verified = False
        self.user.save()

    def test_unverified_user_cannot_log_in(self):
        response = self.client.post(
            reverse("login"),
            {"username": "unverified", "password": "correct-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_valid_code_verifies_and_logs_in(self):
        code, _ = EmailVerificationCode.generate_code(self.user)
        response = self.client.post(
            reverse("accounts:verify_code"),
            {"code": code},
        )
        self.assertRedirects(response, reverse("core:home"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_invalid_code_shows_error(self):
        code, _ = EmailVerificationCode.generate_code(self.user)
        response = self.client.post(
            reverse("accounts:verify_code"),
            {"code": "111111"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kode ntabwo ikora")
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)

    def test_code_only_works_once(self):
        code, _ = EmailVerificationCode.generate_code(self.user)
        self.client.post(reverse("accounts:verify_code"), {"code": code})  # first use
        self.client.logout()
        second_response = self.client.post(
            reverse("accounts:verify_code"),
            {"code": code},
        )
        self.assertEqual(second_response.status_code, 200)
        self.assertContains(second_response, "Kode ntabwo ikora")

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
        self.assertRedirects(real, reverse("accounts:verify_code"))
        self.assertRedirects(fake, reverse("accounts:verify_code"))

    def test_resend_email_lookup_is_case_insensitive(self):
        response = self.client.post(
            reverse("accounts:resend_verification"),
            {"email": "UNVERIFIED@example.com"},
        )

        self.assertRedirects(response, reverse("accounts:verify_code"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["unverified@example.com"])

    def test_resend_generates_new_code(self):
        code1, _ = EmailVerificationCode.generate_code(self.user)
        self.client.post(
            reverse("accounts:resend_verification"), {"email": "unverified@example.com"}
        )
        # Old code should not work
        response = self.client.post(
            reverse("accounts:verify_code"),
            {"code": code1},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kode ntabwo ikora")
        # New code should be in the email
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        import re
        codes = re.findall(r'\b\d{6}\b', body)
        self.assertEqual(len(codes), 1)
        self.assertNotEqual(codes[0], code1)


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