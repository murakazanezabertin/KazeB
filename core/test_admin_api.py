import json
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from listings.models import Category, Listing
from trust.models import AdminAuditLog, PhoneVerification, Report, Review

User = get_user_model()


class AdminApiTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            username="admin-api-buyer",
            email="buyer@example.com",
            password="test-pass-12345",
            phone_number="+250788000001",
        )
        self.seller = User.objects.create_user(
            username="admin-api-seller",
            email="seller@example.com",
            password="test-pass-12345",
            phone_number="+250788000002",
        )
        self.staff = User.objects.create_user(
            username="admin-api-staff",
            email="staff@example.com",
            password="test-pass-12345",
            is_staff=True,
        )
        self.category = Category.objects.create(name="Admin API category")
        self.listing = Listing.objects.create(
            seller=self.seller,
            category=self.category,
            name="Moderated item",
            description="An item for moderation.",
            district="Gasabo",
            sector="Remera",
            price=Decimal("12500"),
        )
        self.report = Report.objects.create(
            reporter=self.buyer,
            listing=self.listing,
            reason=Report.Reason.OTHER,
            details="Please review this listing.",
        )
        self.review = Review.objects.create(
            reviewer=self.buyer,
            seller=self.seller,
            rating=1,
            comment="A review to inspect.",
        )
        PhoneVerification.objects.create(
            user=self.seller,
            code="123456",
            is_verified=True,
        )
        self.grant(
            self.staff,
            "trust",
            "view_admin_dashboard",
            "view_adminauditlog",
            "view_report",
            "manage_report",
            "view_review",
            "delete_review",
            "view_phoneverification",
        )
        self.grant(self.staff, "accounts", "view_user", "suspend_user")
        self.grant(
            self.staff,
            "listings",
            "view_listing",
            "moderate_listing",
            "remove_listing",
        )
        self.client.force_login(self.staff)

    @staticmethod
    def grant(user, app_label, *codenames):
        permissions = []
        for codename in codenames:
            permission = Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename,
            )
            permissions.append(permission)
        user.user_permissions.add(*permissions)

    def json_post(self, url, payload):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_dashboard_returns_real_database_totals_and_activity(self):
        response = self.client.get(reverse("admin_overview_api"))

        self.assertEqual(response.status_code, 200)
        statistics = response.json()["statistics"]
        self.assertEqual(statistics["users"]["total"], User.objects.count())
        self.assertEqual(statistics["listings"]["total"], Listing.objects.count())
        self.assertEqual(statistics["reports"]["total"], Report.objects.count())
        self.assertEqual(statistics["reports"]["pending"], 1)
        self.assertEqual(statistics["reviews"], Review.objects.count())
        self.assertEqual(statistics["verified_phones"], 1)
        self.assertTrue(response.json()["recent_activity"])

    def test_user_search_and_date_filters_are_paginated(self):
        response = self.client.get(
            reverse("admin_users_api"),
            {"q": "admin-api-buyer", "joined_from": "2020-01-01", "page_size": "1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["username"], self.buyer.username)
        self.assertEqual(response.json()["pagination"]["count"], 1)

    def test_non_staff_users_are_denied_even_if_granted_dashboard_permission(self):
        self.grant(self.buyer, "trust", "view_admin_dashboard")
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("admin_overview_api"))

        self.assertEqual(response.status_code, 403)

    def test_anonymous_users_receive_json_unauthorized_response(self):
        self.client.logout()

        response = self.client.get(reverse("admin_overview_api"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Authentication is required.")

    def test_dashboard_page_requires_staff_permission_and_loads_manifest_assets(self):
        self.client.logout()
        self.assertEqual(
            self.client.get(reverse("core:admin_dashboard")).status_code,
            401,
        )

        self.client.force_login(self.staff)
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
                            "file": "assets/admin.js",
                            "css": ["assets/admin.css"],
                        }
                    }
                ),
                encoding="utf-8",
            )
            with patch("core.views.settings.BASE_DIR", Path(temporary_directory)):
                response = self.client.get(reverse("core:admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="root"')
        self.assertContains(response, "/static/react/assets/admin.js")

    def test_account_suspension_requires_reason_and_records_audit(self):
        response = self.json_post(
            reverse("admin_user_status_api", args=[self.buyer.pk]),
            {"is_active": False, "reason": "Repeated marketplace abuse."},
        )

        self.assertEqual(response.status_code, 200)
        self.buyer.refresh_from_db()
        self.assertFalse(self.buyer.is_active)
        entry = AdminAuditLog.objects.get(action=AdminAuditLog.Action.USER_SUSPENDED)
        self.assertEqual(entry.actor, self.staff)
        self.assertEqual(entry.reason, "Repeated marketplace abuse.")

    def test_staff_without_suspension_permission_is_denied(self):
        self.staff.user_permissions.remove(
            Permission.objects.get(content_type__app_label="accounts", codename="suspend_user")
        )

        response = self.json_post(
            reverse("admin_user_status_api", args=[self.buyer.pk]),
            {"is_active": False, "reason": "Repeated marketplace abuse."},
        )

        self.assertEqual(response.status_code, 403)

    def test_listing_hide_and_restore_are_audited_and_hidden_from_marketplace(self):
        hide = self.json_post(
            reverse("admin_listing_moderation_api", args=[self.listing.pk]),
            {"action": "hide", "reason": "Listing violates marketplace rules."},
        )

        self.assertEqual(hide.status_code, 200)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.moderation_status, Listing.ModerationStatus.HIDDEN)
        self.assertEqual(
            self.client.get(reverse("listing_detail_api", args=[self.listing.pk])).status_code,
            404,
        )
        self.assertTrue(
            AdminAuditLog.objects.filter(action=AdminAuditLog.Action.LISTING_HIDDEN).exists()
        )

        restore = self.json_post(
            reverse("admin_listing_moderation_api", args=[self.listing.pk]),
            {"action": "restore", "reason": "Reviewed and approved."},
        )

        self.assertEqual(restore.status_code, 200)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.moderation_status, Listing.ModerationStatus.VISIBLE)
        self.assertEqual(
            self.client.get(reverse("listing_detail_api", args=[self.listing.pk])).status_code,
            200,
        )

    def test_removing_listing_is_soft_and_requires_remove_permission(self):
        response = self.json_post(
            reverse("admin_listing_moderation_api", args=[self.listing.pk]),
            {"action": "remove", "reason": "Confirmed prohibited item."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Listing.objects.filter(pk=self.listing.pk).exists())
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.moderation_status, Listing.ModerationStatus.REMOVED)
        self.assertTrue(
            AdminAuditLog.objects.filter(action=AdminAuditLog.Action.LISTING_REMOVED).exists()
        )

    def test_report_decision_records_handler_and_decision(self):
        response = self.json_post(
            reverse("admin_report_update_api", args=[self.report.pk]),
            {
                "status": Report.Status.RESOLVED,
                "decision_notes": "Listing was reviewed and corrected.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, Report.Status.RESOLVED)
        self.assertEqual(self.report.handled_by, self.staff)
        self.assertIsNotNone(self.report.handled_at)
        self.assertTrue(self.report.is_resolved)
        self.assertTrue(
            AdminAuditLog.objects.filter(action=AdminAuditLog.Action.REPORT_UPDATED).exists()
        )

    def test_resolved_report_requires_decision_notes(self):
        response = self.json_post(
            reverse("admin_report_update_api", args=[self.report.pk]),
            {"status": Report.Status.RESOLVED, "decision_notes": ""},
        )

        self.assertEqual(response.status_code, 400)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, Report.Status.PENDING)

    def test_review_removal_is_audited(self):
        response = self.json_post(
            reverse("admin_review_remove_api", args=[self.review.pk]),
            {"reason": "Contains abusive content."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Review.objects.filter(pk=self.review.pk).exists())
        self.assertTrue(
            AdminAuditLog.objects.filter(action=AdminAuditLog.Action.REVIEW_REMOVED).exists()
        )

    def test_phone_verification_list_reports_real_status(self):
        response = self.client.get(reverse("admin_phones_api"), {"verified": "verified"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["user"], self.seller.username)

    def test_activity_endpoint_is_permission_protected(self):
        self.staff.user_permissions.remove(
            Permission.objects.get(
                content_type__app_label="trust",
                codename="view_adminauditlog",
            )
        )

        response = self.client.get(reverse("admin_activity_api"))

        self.assertEqual(response.status_code, 403)

    def test_setup_command_creates_limited_staff_groups(self):
        call_command("setup_admin_roles", stdout=StringIO())

        viewer = Group.objects.get(name="KazeB Admin Viewer")
        support = Group.objects.get(name="KazeB User Support")
        safety = Group.objects.get(name="KazeB Trust & Safety")
        self.assertTrue(viewer.permissions.filter(codename="view_admin_dashboard").exists())
        self.assertFalse(viewer.permissions.filter(codename="suspend_user").exists())
        self.assertTrue(support.permissions.filter(codename="suspend_user").exists())
        self.assertTrue(safety.permissions.filter(codename="moderate_listing").exists())
        self.assertFalse(User.objects.filter(is_superuser=True).exists())
