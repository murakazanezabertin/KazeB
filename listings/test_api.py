from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from trust.models import Review
from chat.models import Message

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
        first = ListingImage.objects.create(
            listing=self.listing, image="listings/first.jpg", is_cover=False
        )
        cover = ListingImage.objects.create(
            listing=self.listing, image="listings/cover.jpg", is_cover=True
        )
        Review.objects.create(reviewer=self.buyer, seller=self.seller, rating=4, comment="Good.")

        response = self.client.get(reverse("listing_detail_api", args=[self.listing.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            [image["id"] for image in payload["images"]], [cover.pk, first.pk]
        )
        self.assertEqual(payload["images"][0]["url"], "/media/listings/cover.jpg")
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

    def test_seller_listing_create_requires_authentication(self):
        response = self.client.post(reverse("seller_listing_create_api"), {})

        self.assertIn(response.status_code, (401, 403))

    def test_seller_listing_create_requires_csrf_for_authenticated_user(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.seller)

        response = client.post(
            reverse("seller_listing_create_api"),
            {
                "category": self.category.pk,
                "name": "CSRF product",
                "description": "CSRF protected.",
                "condition": "used",
                "district": "Kigali",
                "sector": "Kicukiro",
                "price": "1000",
                "currency": "RWF",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_seller_listing_create_reuses_form_validation_and_ignores_seller(self):
        self.client.force_login(self.seller)

        response = self.client.post(
            reverse("seller_listing_create_api"),
            {
                "seller": self.buyer.pk,
                "category": "",
                "name": "",
                "description": "",
                "condition": "used",
                "district": "",
                "sector": "",
                "price": "",
                "currency": "RWF",
            },
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertIn("category", payload["errors"])
        self.assertIn("name", payload["errors"])
        self.assertIn("description", payload["errors"])
        self.assertIn("district", payload["errors"])
        self.assertIn("sector", payload["errors"])
        self.assertIn("price", payload["errors"])
        self.assertFalse(Listing.objects.filter(name="").exists())

    def test_seller_listing_create_assigns_request_user_and_uploads_images(self):
        output = BytesIO()
        Image.new("RGB", (4, 4), color="orange").save(output, format="PNG")
        first_image = SimpleUploadedFile(
            "first.png", output.getvalue(), content_type="image/png"
        )
        second_image = SimpleUploadedFile(
            "second.png", output.getvalue(), content_type="image/png"
        )
        self.client.force_login(self.seller)

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse("seller_listing_create_api"),
                {
                    "seller": self.buyer.pk,
                    "category": self.category.pk,
                    "name": "React-created phone",
                    "description": "Created through the React API.",
                    "condition": "new",
                    "district": "Kigali",
                    "sector": "Kicukiro",
                    "price": "15000",
                    "currency": "RWF",
                    "images": [first_image, second_image],
                },
            )

        self.assertEqual(response.status_code, 201)
        listing = Listing.objects.get(name="React-created phone")
        self.assertEqual(listing.seller, self.seller)
        self.assertEqual(listing.category, self.category)
        images = list(listing.images.order_by("pk"))
        self.assertEqual(len(images), 2)
        self.assertTrue(images[0].is_cover)
        self.assertFalse(images[1].is_cover)

    def test_seller_listing_create_rejects_invalid_image_before_creating_listing(self):
        self.client.force_login(self.seller)

        response = self.client.post(
            reverse("seller_listing_create_api"),
            {
                "category": self.category.pk,
                "name": "Invalid image listing",
                "description": "Should not be created.",
                "condition": "used",
                "district": "Kigali",
                "sector": "Kicukiro",
                "price": "15000",
                "currency": "RWF",
                "images": SimpleUploadedFile(
                    "not-an-image.jpg", b"not an image", content_type="image/jpeg"
                ),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("images", response.json()["errors"])
        self.assertFalse(
            Listing.objects.filter(name="Invalid image listing").exists()
        )

    def test_seller_listing_create_compresses_uploaded_images(self):
        image_bytes = BytesIO()
        Image.new("RGB", (1700, 900), color="blue").save(image_bytes, format="PNG")
        self.client.force_login(self.seller)

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse("seller_listing_create_api"),
                {
                    "category": self.category.pk,
                    "name": "Compressed image listing",
                    "description": "Image compression check.",
                    "condition": "used",
                    "district": "Kigali",
                    "sector": "Kicukiro",
                    "price": "15000",
                    "currency": "RWF",
                    "images": SimpleUploadedFile(
                        "large.png", image_bytes.getvalue(), content_type="image/png"
                    ),
                },
            )

            self.assertEqual(response.status_code, 201)
            stored_image = ListingImage.objects.get(
                listing__name="Compressed image listing"
            ).image
            with stored_image.open("rb") as stored_file:
                with Image.open(stored_file) as decoded_image:
                    self.assertLessEqual(max(decoded_image.size), 1600)
                    self.assertEqual(decoded_image.format, "JPEG")

    def test_seller_listing_create_cleans_partial_storage_write_on_failure(self):
        self.client.force_login(self.seller)
        image_bytes = BytesIO()
        Image.new("RGB", (4, 4), color="orange").save(image_bytes, format="PNG")
        images = [
            SimpleUploadedFile(f"image-{index}.png", image_bytes.getvalue(), content_type="image/png")
            for index in range(2)
        ]

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            storage = ListingImage._meta.get_field("image").storage
            original_save = storage.save
            saved_names = []

            def save_once_then_fail(name, content, max_length=None):
                if saved_names:
                    raise OSError("simulated storage failure")
                saved_name = original_save(name, content, max_length=max_length)
                saved_names.append(saved_name)
                return saved_name

            with patch.object(storage, "save", side_effect=save_once_then_fail):
                with self.assertRaises(OSError):
                    self.client.post(
                        reverse("seller_listing_create_api"),
                        {
                            "category": self.category.pk,
                            "name": "Failed upload listing",
                            "description": "Should roll back.",
                            "condition": "used",
                            "district": "Kigali",
                            "sector": "Kicukiro",
                            "price": "15000",
                            "currency": "RWF",
                            "images": images,
                        },
                    )

            self.assertFalse(Listing.objects.filter(name="Failed upload listing").exists())
            self.assertEqual(len(saved_names), 1)
            self.assertFalse(storage.exists(saved_names[0]))

    def test_seller_listing_create_metadata_returns_categories_and_choices(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("seller_listing_create_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("categories", payload)
        self.assertIn("conditions", payload)
        self.assertIn("currencies", payload)
        self.assertTrue(any(item["id"] == self.category.pk for item in payload["categories"]))

    def test_seller_dashboard_requires_authentication(self):
        response = self.client.get(reverse("seller_dashboard_api"))

        self.assertIn(response.status_code, (401, 403))

    def test_seller_dashboard_returns_only_owned_active_and_inactive_listings(self):
        other_seller = User.objects.create_user(
            username="other-seller",
            password="test-password",
            phone_number="+250788000001",
            whatsapp_number="+250788000001",
        )
        other_listing = Listing.objects.create(
            seller=other_seller,
            category=self.category,
            name="Other seller listing",
            description="Not owned.",
            district="Kigali",
            sector="Kicukiro",
            price=Decimal("999"),
        )
        ListingImage.objects.create(
            listing=self.listing,
            image="listings/dashboard-phone.jpg",
            is_cover=True,
        )
        self.listing.views_count = 7
        self.listing.save(update_fields=["views_count"])
        Message.objects.create(
            listing=self.listing,
            buyer=self.buyer,
            sender=self.buyer,
            body="Is this available?",
            is_read=False,
        )
        self.client.force_login(self.seller)

        response = self.client.get(reverse("seller_dashboard_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        listing_ids = {item["id"] for item in payload["listings"]}
        self.assertIn(self.listing.pk, listing_ids)
        self.assertIn(self.hidden.pk, listing_ids)
        self.assertNotIn(other_listing.pk, listing_ids)
        self.assertTrue(
            any(
                item["id"] == self.listing.pk and item["cover_image"].endswith(
                    "/media/listings/dashboard-phone.jpg"
                )
                for item in payload["listings"]
            )
        )
        self.assertEqual(payload["statistics"]["total_listings"], 3)
        self.assertEqual(payload["statistics"]["active_listings"], 2)
        self.assertEqual(payload["statistics"]["inactive_listings"], 1)
        self.assertEqual(payload["statistics"]["total_views"], 7)
        self.assertEqual(payload["statistics"]["unread_messages"], 1)
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_seller_listing_edit_rejects_anonymous_and_non_owner(self):
        anonymous = self.client.get(
            reverse("seller_listing_edit_api", args=[self.listing.pk])
        )
        self.assertIn(anonymous.status_code, (401, 403))

        self.client.force_login(self.buyer)
        response = self.client.get(
            reverse("seller_listing_edit_api", args=[self.listing.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_seller_listing_edit_loads_inactive_listing_and_existing_images(self):
        image = ListingImage.objects.create(
            listing=self.hidden,
            image="listings/hidden.jpg",
            is_cover=True,
        )
        self.client.force_login(self.seller)

        response = self.client.get(
            reverse("seller_listing_edit_api", args=[self.hidden.pk])
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["listing"]["id"], self.hidden.pk)
        self.assertFalse(payload["listing"]["is_active"])
        self.assertEqual(payload["listing"]["images"][0]["id"], image.pk)
        self.assertTrue(payload["listing"]["images"][0]["is_cover"])

    def test_seller_listing_edit_updates_fields_removes_images_and_falls_back_cover(self):
        cover = ListingImage.objects.create(
            listing=self.listing,
            image="listings/cover.jpg",
            is_cover=True,
        )
        remaining = ListingImage.objects.create(
            listing=self.listing,
            image="listings/remaining.jpg",
            is_cover=False,
        )
        api_client = APIClient()
        api_client.force_authenticate(user=self.seller)
        response = api_client.patch(
            reverse("seller_listing_edit_api", args=[self.listing.pk]),
            {
                "category": self.other_category.pk,
                "name": "Updated phone",
                "description": "Updated description.",
                "condition": "new",
                "district": "Huye",
                "sector": "Tumba",
                "price": "18000",
                "currency": "USD",
                "remove_images": str(cover.pk),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.name, "Updated phone")
        self.assertEqual(self.listing.category, self.other_category)
        self.assertEqual(self.listing.currency, "USD")
        self.assertFalse(ListingImage.objects.filter(pk=cover.pk).exists())
        remaining.refresh_from_db()
        self.assertTrue(remaining.is_cover)

    def test_seller_listing_edit_preserves_images_without_removal_and_adds_upload(self):
        existing = ListingImage.objects.create(
            listing=self.listing,
            image="listings/existing.jpg",
            is_cover=True,
        )
        output = BytesIO()
        Image.new("RGB", (5, 5), color="blue").save(output, format="PNG")
        upload = SimpleUploadedFile(
            "new.png", output.getvalue(), content_type="image/png"
        )
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            api_client = APIClient()
            api_client.force_authenticate(user=self.seller)
            response = api_client.patch(
                reverse("seller_listing_edit_api", args=[self.listing.pk]),
                {
                    "category": self.category.pk,
                    "name": self.listing.name,
                    "description": self.listing.description,
                    "condition": self.listing.condition,
                    "district": self.listing.district,
                    "sector": self.listing.sector,
                    "price": str(self.listing.price),
                    "currency": self.listing.currency,
                    "images": upload,
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(ListingImage.objects.filter(pk=existing.pk).exists())
        self.assertEqual(self.listing.images.count(), 2)

    def test_seller_listing_edit_failure_rolls_back_changes_and_preserves_old_image(self):
        image_bytes = BytesIO()
        Image.new("RGB", (4, 4), color="red").save(image_bytes, format="PNG")

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            existing = ListingImage.objects.create(
                listing=self.listing,
                image=SimpleUploadedFile(
                    "existing.png", image_bytes.getvalue(), content_type="image/png"
                ),
                is_cover=True,
            )
            existing_name = existing.image.name
            storage = existing.image.storage
            image_bytes.seek(0)
            uploads = [
                SimpleUploadedFile(
                    f"new-{index}.png",
                    image_bytes.getvalue(),
                    content_type="image/png",
                )
                for index in range(2)
            ]
            original_save = storage.save
            saved_names = []

            def save_once_then_fail(name, content, max_length=None):
                if saved_names:
                    raise OSError("simulated storage failure")
                saved_name = original_save(name, content, max_length=max_length)
                saved_names.append(saved_name)
                return saved_name

            api_client = APIClient()
            api_client.force_authenticate(user=self.seller)
            with patch.object(storage, "save", side_effect=save_once_then_fail):
                with self.assertRaises(OSError):
                    api_client.patch(
                        reverse("seller_listing_edit_api", args=[self.listing.pk]),
                        {
                            "category": self.category.pk,
                            "name": "Failed edit",
                            "description": self.listing.description,
                            "condition": self.listing.condition,
                            "district": self.listing.district,
                            "sector": self.listing.sector,
                            "price": str(self.listing.price),
                            "currency": self.listing.currency,
                            "remove_images": str(existing.pk),
                            "images": uploads,
                        },
                        format="multipart",
                    )

            self.listing.refresh_from_db()
            self.assertEqual(self.listing.name, "Used phone")
            self.assertTrue(ListingImage.objects.filter(pk=existing.pk).exists())
            self.assertEqual(self.listing.images.count(), 1)
            self.assertTrue(storage.exists(existing_name))
            self.assertEqual(len(saved_names), 1)
            self.assertFalse(storage.exists(saved_names[0]))

    def test_non_owner_cannot_modify_another_sellers_images(self):
        image = ListingImage.objects.create(
            listing=self.listing,
            image="listings/private.jpg",
            is_cover=True,
        )
        api_client = APIClient()
        api_client.force_authenticate(user=self.buyer)

        response = api_client.patch(
            reverse("seller_listing_edit_api", args=[self.listing.pk]),
            {
                "category": self.category.pk,
                "name": "Unauthorized edit",
                "description": self.listing.description,
                "condition": self.listing.condition,
                "district": self.listing.district,
                "sector": self.listing.sector,
                "price": str(self.listing.price),
                "currency": self.listing.currency,
                "remove_images": str(image.pk),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 404)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.name, "Used phone")
        self.assertTrue(ListingImage.objects.filter(pk=image.pk).exists())

    def test_seller_listing_edit_invalid_form_returns_field_errors(self):
        api_client = APIClient()
        api_client.force_authenticate(user=self.seller)
        response = api_client.patch(
            reverse("seller_listing_edit_api", args=[self.listing.pk]),
            {
                "category": "",
                "name": "",
                "description": "",
                "condition": "used",
                "district": "",
                "sector": "",
                "price": "",
                "currency": "RWF",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        for field in ("category", "name", "description", "district", "sector", "price"):
            self.assertIn(field, payload["errors"])

    def test_seller_listing_edit_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.seller)

        response = client.patch(
            reverse("seller_listing_edit_api", args=[self.listing.pk]),
            {
                "category": self.category.pk,
                "name": self.listing.name,
                "description": self.listing.description,
                "condition": self.listing.condition,
                "district": self.listing.district,
                "sector": self.listing.sector,
                "price": str(self.listing.price),
                "currency": self.listing.currency,
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_seller_listing_edit_removal_deletes_stored_image_file(self):
        self.client.force_login(self.seller)
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            output = BytesIO()
            Image.new("RGB", (4, 4), color="red").save(output, format="PNG")
            upload = SimpleUploadedFile(
                "stored.png", output.getvalue(), content_type="image/png"
            )
            image = ListingImage.objects.create(
                listing=self.listing,
                image=upload,
                is_cover=True,
            )
            stored_name = image.image.name
            stored_path = image.image.path
            self.assertTrue(image.image.storage.exists(stored_name))

            api_client = APIClient()
            api_client.force_authenticate(user=self.seller)
            with self.captureOnCommitCallbacks(execute=True):
                response = api_client.patch(
                    reverse("seller_listing_edit_api", args=[self.listing.pk]),
                    {
                        "category": self.category.pk,
                        "name": self.listing.name,
                        "description": self.listing.description,
                        "condition": self.listing.condition,
                        "district": self.listing.district,
                        "sector": self.listing.sector,
                        "price": str(self.listing.price),
                        "currency": self.listing.currency,
                        "remove_images": str(image.pk),
                    },
                    format="multipart",
                )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(ListingImage.objects.filter(pk=image.pk).exists())
            self.assertFalse(image.image.storage.exists(stored_name))

    def test_seller_listing_status_requires_authentication_and_csrf(self):
        anonymous = self.client.patch(
            reverse("seller_listing_status_api", args=[self.listing.pk]),
            {"is_active": False},
            content_type="application/json",
        )
        self.assertIn(anonymous.status_code, (401, 403))

        client = Client(enforce_csrf_checks=True)
        client.force_login(self.seller)
        csrf_missing = client.patch(
            reverse("seller_listing_status_api", args=[self.listing.pk]),
            '{"is_active": false}',
            content_type="application/json",
        )
        self.assertEqual(csrf_missing.status_code, 403)

    def test_non_owner_cannot_change_listing_status(self):
        self.client.force_login(self.buyer)

        response = self.client.patch(
            reverse("seller_listing_status_api", args=[self.listing.pk]),
            '{"is_active": false}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.listing.refresh_from_db()
        self.assertTrue(self.listing.is_active)

    def test_owner_can_hide_and_reactivate_listing_and_dashboard_keeps_it(self):
        self.client.force_login(self.seller)
        url = reverse("seller_listing_status_api", args=[self.listing.pk])

        hidden = self.client.patch(
            url,
            '{"is_active": false}',
            content_type="application/json",
        )
        self.assertEqual(hidden.status_code, 200)
        self.assertFalse(hidden.json()["is_active"])
        self.assertEqual(hidden.json()["status"], "inactive")

        dashboard = self.client.get(reverse("seller_dashboard_api"))
        dashboard_listing_ids = {
            item["id"] for item in dashboard.json()["listings"]
        }
        self.assertIn(self.listing.pk, dashboard_listing_ids)
        dashboard_listing = next(
            item
            for item in dashboard.json()["listings"]
            if item["id"] == self.listing.pk
        )
        self.assertFalse(dashboard_listing["is_active"])

        edit = self.client.get(
            reverse("seller_listing_edit_api", args=[self.listing.pk])
        )
        self.assertEqual(edit.status_code, 200)

        active = self.client.patch(
            url,
            '{"is_active": true}',
            content_type="application/json",
        )
        self.assertEqual(active.status_code, 200)
        self.assertTrue(active.json()["is_active"])
        self.assertEqual(active.json()["status"], "active")

    def test_status_changes_preserve_public_listing_visibility_rules(self):
        self.client.force_login(self.seller)
        status_url = reverse("seller_listing_status_api", args=[self.listing.pk])
        detail_url = reverse("listing_detail_api", args=[self.listing.pk])

        hidden = self.client.patch(
            status_url,
            '{"is_active": false}',
            content_type="application/json",
        )
        self.assertEqual(hidden.status_code, 200)
        browse_hidden = self.client.get(
            reverse("listing_browse_api"), {"q": self.listing.name}
        )
        detail_hidden = self.client.get(detail_url)
        self.assertNotIn(
            self.listing.pk,
            [item["id"] for item in browse_hidden.json()["results"]],
        )
        self.assertEqual(detail_hidden.status_code, 404)

        active = self.client.patch(
            status_url,
            '{"is_active": true}',
            content_type="application/json",
        )
        self.assertEqual(active.status_code, 200)
        browse_active = self.client.get(
            reverse("listing_browse_api"), {"q": self.listing.name}
        )
        detail_active = self.client.get(detail_url)
        self.assertIn(
            self.listing.pk,
            [item["id"] for item in browse_active.json()["results"]],
        )
        self.assertEqual(detail_active.status_code, 200)

    def test_seller_listing_delete_requires_authentication_and_csrf(self):
        url = reverse("seller_listing_edit_api", args=[self.listing.pk])
        anonymous = self.client.delete(url)
        self.assertIn(anonymous.status_code, (401, 403))

        client = Client(enforce_csrf_checks=True)
        client.force_login(self.seller)
        csrf_missing = client.delete(url)
        self.assertEqual(csrf_missing.status_code, 403)

    def test_non_owner_cannot_delete_another_sellers_listing(self):
        self.client.force_login(self.buyer)

        with self.captureOnCommitCallbacks(execute=True):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.delete(
                    reverse("seller_listing_edit_api", args=[self.listing.pk])
                )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Listing.objects.filter(pk=self.listing.pk).exists())

    def test_owner_delete_cascades_images_cleans_storage_and_refreshes_statistics(self):
        self.client.force_login(self.seller)
        self.listing.views_count = 11
        self.listing.save(update_fields=["views_count"])
        Message.objects.create(
            listing=self.listing,
            buyer=self.buyer,
            sender=self.buyer,
            body="Please contact me.",
            is_read=False,
        )

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            output = BytesIO()
            Image.new("RGB", (4, 4), color="orange").save(output, format="PNG")
            upload = SimpleUploadedFile(
                "delete-me.png",
                output.getvalue(),
                content_type="image/png",
            )
            image = ListingImage.objects.create(
                listing=self.listing,
                image=upload,
                is_cover=True,
            )
            image_id = image.pk
            image_name = image.image.name
            self.assertTrue(image.image.storage.exists(image_name))

            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.delete(
                    reverse("seller_listing_edit_api", args=[self.listing.pk])
                )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(Listing.objects.filter(pk=self.listing.pk).exists())
            self.assertFalse(ListingImage.objects.filter(pk=image_id).exists())
            self.assertFalse(image.image.storage.exists(image_name))
            self.assertEqual(response.json()["listing_id"], self.listing.pk)
            self.assertEqual(
                response.json()["statistics"],
                {
                    "total_listings": 2,
                    "active_listings": 1,
                    "inactive_listings": 1,
                    "total_views": 0,
                    "unread_messages": 0,
                },
            )
