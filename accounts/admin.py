from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "KazeB contact details",
            {"fields": ("profile_picture", "phone_number", "whatsapp_number", "agreed_to_terms", "email_verified")},
        ),
    )
    list_display = ("username", "email", "phone_number", "is_staff", "email_verified")
    list_filter = BaseUserAdmin.list_filter + ("email_verified",)


admin.site.register(User, UserAdmin)
