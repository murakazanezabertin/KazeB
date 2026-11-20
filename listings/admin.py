from django.contrib import admin

from .models import Category, Favorite, Listing, ListingImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order")
    prepopulated_fields = {"slug": ("name",)}


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "seller",
        "price",
        "currency",
        "district",
        "sector",
        "is_active",
        "moderation_status",
        "created_at",
    )
    list_filter = (
        "category",
        "condition",
        "currency",
        "is_active",
        "moderation_status",
        "district",
    )
    search_fields = ("name", "description", "district", "sector")
    inlines = [ListingImageInline]
    readonly_fields = (
        "is_active",
        "moderation_status",
        "moderation_reason",
        "moderated_by",
        "moderated_at",
    )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "listing", "created_at")
    search_fields = ("user__username", "listing__name")
