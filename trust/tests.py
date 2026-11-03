from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from listings.models import Category, Listing
from .models import PhoneVerification, Report, Review

User = get_user_model()


def make_user(username, **kwargs):
    defaults = {"phone_number": "+250788000000", "whatsapp_number": "+250788000000"}
    defaults.update(kwargs)
    return User.objects.create_user(username=username, password="testpass123", **defaults)


class ReportTests(TestCase):
    def setUp(self):
        self.seller = make_user("seller")
        self.buyer = make_user("buyer")
        self.category = Category.objects.create(name="Electronics")
        self.listing = Listing.objects.create(
            seller=self.seller, category=self.category, name="Phone",
            description="A phone.", district="Gasabo", sector="Remera",
            price=Decimal("100"),
        )

    def test_requires_login(self):
        response = self.client.get(reverse("trust:report_listing", args=[self.listing.pk]))
        self.assertEqual(response.status_code, 302)

    def test_submitting_report_creates_it(self):
        self.client.login(username="buyer", password="testpass123")
        response = self.client.post(
            reverse("trust:report_listing", args=[self.listing.pk]),
            {"reason": "scam", "details": "Looked suspicious."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Report.objects.filter(listing=self.listing).count(), 1)


class ReviewTests(TestCase):
    def setUp(self):
        self.seller = make_user("seller")
        self.buyer = make_user("buyer")

    def test_cannot_review_self(self):
        self.client.login(username="seller", password="testpass123")
        response = self.client.post(
            reverse("trust:add_review", args=[self.seller.pk]),
            {"rating": 5, "comment": "Nice"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 0)

    def test_can_review_seller(self):
        self.client.login(username="buyer", password="testpass123")
        response = self.client.post(
            reverse("trust:add_review", args=[self.seller.pk]),
            {"rating": 4, "comment": "Good deal"},
        )
        self.assertEqual(response.status_code, 302)
        review = Review.objects.get()
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.seller, self.seller)
        self.assertEqual(review.reviewer, self.buyer)

    def test_only_one_review_per_seller(self):
        Review.objects.create(reviewer=self.buyer, seller=self.seller, rating=3)
        self.client.login(username="buyer", password="testpass123")
        self.client.post(
            reverse("trust:add_review", args=[self.seller.pk]),
            {"rating": 5, "comment": "Updated"},
        )
        self.assertEqual(Review.objects.filter(reviewer=self.buyer, seller=self.seller).count(), 1)
        self.assertEqual(Review.objects.get().rating, 5)  # updated, not duplicated


class PhoneVerificationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user("seller", email="[email protected]")

    def test_is_phone_verified_defaults_false(self):
        self.assertFalse(self.user.is_phone_verified)

    def test_sending_code_creates_verification_and_emails_it(self):
        self.client.login(username="seller", password="testpass123")
        self.client.post(reverse("trust:request_phone_verification"))
        self.assertTrue(PhoneVerification.objects.filter(user=self.user).exists())
        self.assertEqual(len(mail.outbox), 1)  # console/email SMS fallback

    def test_correct_code_verifies_phone(self):
        self.client.login(username="seller", password="testpass123")
        self.client.post(reverse("trust:request_phone_verification"))
        verification = PhoneVerification.objects.get(user=self.user)
        self.client.post(reverse("trust:verify_phone"), {"code": verification.code})
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_phone_verified)

    def test_wrong_code_does_not_verify_and_counts_attempt(self):
        self.client.login(username="seller", password="testpass123")
        self.client.post(reverse("trust:request_phone_verification"))
        self.client.post(reverse("trust:verify_phone"), {"code": "000000"})
        verification = PhoneVerification.objects.get(user=self.user)
        self.assertFalse(verification.is_verified)
        self.assertEqual(verification.attempts, 1)

    def test_sending_code_is_rate_limited(self):
        self.client.login(username="seller", password="testpass123")
        for _ in range(3):
            self.client.post(reverse("trust:request_phone_verification"))
        mail.outbox.clear()
        self.client.post(reverse("trust:request_phone_verification"))
        self.assertEqual(len(mail.outbox), 0)  # 4th request blocked, no new email sent
