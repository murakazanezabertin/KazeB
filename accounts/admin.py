from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

from .models import User
from trust.audit import record_admin_activity
from trust.models import AdminAuditLog


class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "KazeB contact details",
            {"fields": ("profile_picture", "phone_number", "whatsapp_number", "agreed_to_terms", "email_verified")},
        ),
    )
    list_display = ("username", "email", "phone_number", "is_staff", "email_verified")
    list_filter = BaseUserAdmin.list_filter + ("email_verified",)

    def save_model(self, request, obj, form, change):
        previous = None
        if change:
            old = User.objects.get(pk=obj.pk)
            previous = {
                "is_active": old.is_active,
                "is_staff": old.is_staff,
                "groups": list(old.groups.values_list("pk", flat=True)),
                "user_permissions": list(old.user_permissions.values_list("pk", flat=True)),
            }
        request._kazeb_previous_admin_role = previous
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        user = form.instance
        previous = getattr(request, "_kazeb_previous_admin_role", None)
        if previous is None:
            previous = {
                "is_active": True,
                "is_staff": False,
                "groups": [],
                "user_permissions": [],
            }
        current_groups = list(user.groups.values_list("pk", flat=True))
        current_permissions = list(user.user_permissions.values_list("pk", flat=True))
        if previous["is_active"] != user.is_active:
            record_admin_activity(
                actor=request.user,
                action=(
                    AdminAuditLog.Action.USER_REACTIVATED
                    if user.is_active
                    else AdminAuditLog.Action.USER_SUSPENDED
                ),
                target_type="user",
                target_id=user.pk,
                target_label=user.get_username(),
                reason="Account status changed in Django admin.",
            )
        if (
            previous["is_staff"] != user.is_staff
            or previous["groups"] != current_groups
            or previous["user_permissions"] != current_permissions
        ) and (previous["is_staff"] or user.is_staff):
            record_admin_activity(
                actor=request.user,
                action=AdminAuditLog.Action.ADMIN_ROLE_CHANGED,
                target_type="user",
                target_id=user.pk,
                target_label=user.get_username(),
                reason="Administrator role or group membership changed in Django admin.",
                details={
                    "is_staff_before": previous["is_staff"],
                    "is_staff_after": user.is_staff,
                    "groups_before": previous["groups"],
                    "groups_after": current_groups,
                    "permissions_before": previous["user_permissions"],
                    "permissions_after": current_permissions,
                },
            )


class GroupAdmin(BaseGroupAdmin):
    def save_model(self, request, obj, form, change):
        if change:
            old_group = Group.objects.get(pk=obj.pk)
            request._kazeb_previous_group_permissions = list(
                old_group.permissions.values_list("pk", flat=True)
            )
        else:
            request._kazeb_previous_group_permissions = []
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        group = form.instance
        previous = set(
            getattr(request, "_kazeb_previous_group_permissions", [])
        )
        current = set(group.permissions.values_list("pk", flat=True))
        if previous != current:
            record_admin_activity(
                actor=request.user,
                action=AdminAuditLog.Action.ADMIN_ROLE_CHANGED,
                target_type="group",
                target_id=group.pk,
                target_label=group.name,
                reason="Group permissions changed in Django admin.",
                details={
                    "permissions_before": sorted(previous),
                    "permissions_after": sorted(current),
                },
            )


admin.site.register(User, UserAdmin)
admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
