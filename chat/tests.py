from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import Category, Listing
from .models import Message

User = get_user_model()


def make_user(username, **kwargs):
    defaults = {"phone_number": "+250788000000", "whatsapp_number": "+250788000000"}
    defaults.update(kwargs)
    return User.objects.create_user(username=username, password="testpass123", **defaults)


class ChatAccessTests(TestCase):
    def setUp(self):
        self.seller = make_user("seller")
        self.buyer = make_user("buyer")
        self.stranger = make_user("stranger")
        self.category = Category.objects.create(name="Electronics")
        self.listing = Listing.objects.create(
            seller=self.seller, category=self.category, name="Phone",
            description="A phone.", district="Gasabo", sector="Remera",
            price=Decimal("100"),
        )

    def test_buyer_can_start_thread(self):
        self.client.login(username="buyer", password="testpass123")
        response = self.client.post(
            reverse("chat:thread_as_buyer", args=[self.listing.pk]),
            {"body": "Is this still available?"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Message.objects.filter(listing=self.listing, buyer=self.buyer).count(), 1)

    def test_seller_cannot_message_own_listing_as_buyer(self):
        self.client.login(username="seller", password="testpass123")
        response = self.client.get(reverse("chat:thread_as_buyer", args=[self.listing.pk]))
        self.assertEqual(response.status_code, 403)

    def test_stranger_cannot_view_someone_elses_thread(self):
        Message.objects.create(
            listing=self.listing, buyer=self.buyer, sender=self.buyer, body="Hi"
        )
        self.client.login(username="stranger", password="testpass123")
        response = self.client.get(
            reverse("chat:thread_as_seller", args=[self.listing.pk, self.buyer.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_seller_can_view_thread_with_buyer(self):
        Message.objects.create(
            listing=self.listing, buyer=self.buyer, sender=self.buyer, body="Hi"
        )
        self.client.login(username="seller", password="testpass123")
        response = self.client.get(
            reverse("chat:thread_as_seller", args=[self.listing.pk, self.buyer.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_inbox_requires_login(self):
        response = self.client.get(reverse("chat:inbox"))
        self.assertEqual(response.status_code, 302)

    def test_resubmitting_the_same_message_does_not_duplicate_it(self):
        """A slow connection plus a second tap on "Send" (or refreshing
        the POST response) used to create two identical rows."""
        self.client.login(username="buyer", password="testpass123")
        url = reverse("chat:thread_as_buyer", args=[self.listing.pk])
        self.client.post(url, {"body": "Is this still available?"})
        self.client.post(url, {"body": "Is this still available?"})
        self.assertEqual(
            Message.objects.filter(listing=self.listing, buyer=self.buyer).count(), 1
        )

    def test_different_messages_are_not_treated_as_duplicates(self):
        self.client.login(username="buyer", password="testpass123")
        url = reverse("chat:thread_as_buyer", args=[self.listing.pk])
        self.client.post(url, {"body": "Is this still available?"})
        self.client.post(url, {"body": "What's the lowest price?"})
        self.assertEqual(
            Message.objects.filter(listing=self.listing, buyer=self.buyer).count(), 2
        )
