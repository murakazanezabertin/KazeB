from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Report(models.Model):
    """
    A buyer (or anyone) flagging a listing or a seller as a scam,
    inappropriate, or otherwise wrong -- reviewed by an admin in
    /admin/, not shown publicly. Exactly one of listing/reported_user
    should be set.
    """

    class Reason(models.TextChoices):
        SCAM = "scam", _("Uburiganya")
        INAPPROPRIATE = "inappropriate", _("Ntibyemewe")
        WRONG_CATEGORY = "wrong_category", _("Ubwoko butariho")
        ALREADY_SOLD = "already_sold", _("Byamaze kugurwa")
        OTHER = "other", _("Ikindi")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        UNDER_REVIEW = "under_review", _("Under review")
        RESOLVED = "resolved", _("Resolved")
        REJECTED = "rejected", _("Rejected")

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_filed"
    )
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.CASCADE, related_name="reports",
        null=True, blank=True,
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_received",
        null=True, blank=True,
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="handled_reports",
        null=True,
        blank=True,
    )
    handled_at = models.DateTimeField(null=True, blank=True)
    decision_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("manage_report", "Can review and decide reports"),
        ]

    def clean(self):
        if not self.listing_id and not self.reported_user_id:
            raise ValidationError("A report needs either a listing or a reported user.")

    def __str__(self):
        target = self.listing or self.reported_user
        return f"Report on {target} ({self.get_reason_display()})"


class Review(models.Model):
    """A buyer's rating/comment about a seller, one per (reviewer,
    seller) pair -- shown on the seller's listings so other buyers can
    see how past deals went."""

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_given"
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_received"
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["reviewer", "seller"], name="one_review_per_seller"),
        ]

    def clean(self):
        if self.reviewer_id == self.seller_id:
            raise ValidationError("You can't review yourself.")

    def __str__(self):
        return f"{self.rating}\u2605 for {self.seller} by {self.reviewer}"


def default_expiry():
    return timezone.now() + timezone.timedelta(minutes=10)


class PhoneVerification(models.Model):
    """
    A one-time code sent to confirm a seller's phone number actually
    belongs to them. Delivery goes through settings.SMS_BACKEND --
    see trust/sms.py. Without a real SMS gateway configured, the code
    is emailed (or printed to the console in development) instead, so
    the verification flow is fully testable before you have a paid
    SMS account.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="phone_verification"
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiry)
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    MAX_ATTEMPTS = 5

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"OTP for {self.user} ({'verified' if self.is_verified else 'pending'})"


class AdminAuditLog(models.Model):
    class Action(models.TextChoices):
        USER_SUSPENDED = "user_suspended", _("User suspended")
        USER_REACTIVATED = "user_reactivated", _("User reactivated")
        LISTING_HIDDEN = "listing_hidden", _("Listing hidden")
        LISTING_RESTORED = "listing_restored", _("Listing restored")
        LISTING_REMOVED = "listing_removed", _("Listing removed")
        REPORT_UPDATED = "report_updated", _("Report updated")
        REVIEW_REMOVED = "review_removed", _("Review removed")
        ADMIN_ROLE_CHANGED = "admin_role_changed", _("Administrator role changed")

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="admin_audit_entries",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    target_type = models.CharField(max_length=40)
    target_id = models.CharField(max_length=64)
    target_label = models.CharField(max_length=255)
    reason = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("view_admin_dashboard", "Can view the administrator dashboard"),
        ]

    def __str__(self):
        return f"{self.get_action_display()}: {self.target_label}"
