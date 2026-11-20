from django import forms
from django.contrib import admin
from django.contrib import messages
from django.utils import timezone

from .audit import record_admin_activity
from .models import AdminAuditLog, PhoneVerification, Report, Review


class ReportAdminForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        decision_notes = (cleaned_data.get("decision_notes") or "").strip()
        if status in (Report.Status.RESOLVED, Report.Status.REJECTED) and not decision_notes:
            self.add_error("decision_notes", "Enter a decision note for a closed report.")
        return cleaned_data


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    form = ReportAdminForm
    list_display = ("__str__", "reporter", "reason", "status", "handled_by", "created_at")
    list_filter = ("reason", "status")
    search_fields = ("details", "reporter__username")
    readonly_fields = ("is_resolved", "handled_by", "handled_at")
    actions = ["mark_resolved", "deactivate_reported_listing"]

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            old_status = Report.objects.get(pk=obj.pk).status
        if old_status != obj.status:
            obj.handled_by = request.user
            obj.handled_at = timezone.now()
            obj.is_resolved = obj.status in (
                Report.Status.RESOLVED,
                Report.Status.REJECTED,
            )
            if obj.is_resolved:
                obj.resolution_notes = obj.decision_notes
        super().save_model(request, obj, form, change)
        if old_status is not None and old_status != obj.status:
            record_admin_activity(
                request.user,
                AdminAuditLog.Action.REPORT_UPDATED,
                "report",
                obj.pk,
                f"Report #{obj.pk}",
                obj.decision_notes,
                {"status_before": old_status, "status_after": obj.status},
            )

    @admin.action(description="Mark selected reports as resolved")
    def mark_resolved(self, request, queryset):
        for report in queryset:
            old_status = report.status
            report.status = Report.Status.RESOLVED
            report.is_resolved = True
            report.handled_by = request.user
            report.handled_at = timezone.now()
            report.decision_notes = report.decision_notes or "Resolved from Django admin."
            report.resolution_notes = report.decision_notes
            report.save(
                update_fields=[
                    "status",
                    "is_resolved",
                    "handled_by",
                    "handled_at",
                    "decision_notes",
                    "resolution_notes",
                ]
            )
            record_admin_activity(
                request.user,
                AdminAuditLog.Action.REPORT_UPDATED,
                "report",
                report.pk,
                f"Report #{report.pk}",
                report.decision_notes,
                {"status_before": old_status, "status_after": report.status},
            )

    @admin.action(description="Deactivate the reported listing(s)")
    def deactivate_reported_listing(self, request, queryset):
        if not request.user.has_perm("listings.moderate_listing"):
            self.message_user(
                request,
                "You do not have permission to moderate listings.",
                level=messages.ERROR,
            )
            return
        for report in queryset.select_related("listing"):
            if report.listing:
                listing = report.listing
                listing.moderation_status = listing.ModerationStatus.HIDDEN
                listing.moderation_reason = f"Hidden from report #{report.pk} in Django admin."
                listing.moderated_by = request.user
                listing.moderated_at = timezone.now()
                listing.save(
                    update_fields=[
                        "moderation_status",
                        "moderation_reason",
                        "moderated_by",
                        "moderated_at",
                        "updated_at",
                    ]
                )
                record_admin_activity(
                    request.user,
                    AdminAuditLog.Action.LISTING_HIDDEN,
                    "listing",
                    listing.pk,
                    listing.name,
                    listing.moderation_reason,
                    {"report_id": report.pk},
                )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("seller", "reviewer", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("seller__username", "reviewer__username", "comment")

    def delete_model(self, request, obj):
        record_admin_activity(
            request.user,
            AdminAuditLog.Action.REVIEW_REMOVED,
            "review",
            obj.pk,
            f"{obj.rating} stars: {obj.reviewer} to {obj.seller}",
            "Removed from Django admin.",
        )
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for review in queryset.select_related("reviewer", "seller"):
            record_admin_activity(
                request.user,
                AdminAuditLog.Action.REVIEW_REMOVED,
                "review",
                review.pk,
                f"{review.rating} stars: {review.reviewer} to {review.seller}",
                "Removed from Django admin.",
            )
        super().delete_queryset(request, queryset)


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "is_verified", "attempts", "created_at", "expires_at")
    list_filter = ("is_verified",)
    search_fields = ("user__username",)


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "target_label", "actor", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("target_label", "target_type", "target_id", "reason")
    readonly_fields = (
        "actor",
        "action",
        "target_type",
        "target_id",
        "target_label",
        "reason",
        "details",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
