from django.contrib import admin

from .models import PhoneVerification, Report, Review


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("__str__", "reporter", "reason", "is_resolved", "created_at")
    list_filter = ("reason", "is_resolved")
    search_fields = ("details", "reporter__username")
    actions = ["mark_resolved", "deactivate_reported_listing"]

    @admin.action(description="Mark selected reports as resolved")
    def mark_resolved(self, request, queryset):
        queryset.update(is_resolved=True)

    @admin.action(description="Deactivate the reported listing(s)")
    def deactivate_reported_listing(self, request, queryset):
        for report in queryset.select_related("listing"):
            if report.listing:
                report.listing.is_active = False
                report.listing.save(update_fields=["is_active"])


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("seller", "reviewer", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("seller__username", "reviewer__username", "comment")


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "is_verified", "attempts", "created_at", "expires_at")
    list_filter = ("is_verified",)
    search_fields = ("user__username",)
