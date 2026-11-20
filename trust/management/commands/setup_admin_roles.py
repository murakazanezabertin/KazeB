from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction

from trust.audit import record_admin_activity
from trust.models import AdminAuditLog


ROLE_PERMISSIONS = {
    "KazeB Admin Viewer": {
        ("trust", "view_admin_dashboard"),
        ("accounts", "view_user"),
        ("listings", "view_listing"),
        ("trust", "view_report"),
        ("trust", "view_review"),
        ("trust", "view_phoneverification"),
        ("trust", "view_adminauditlog"),
    },
    "KazeB User Support": {
        ("trust", "view_admin_dashboard"),
        ("accounts", "view_user"),
        ("accounts", "suspend_user"),
        ("listings", "view_listing"),
        ("trust", "view_report"),
        ("trust", "view_review"),
        ("trust", "view_phoneverification"),
        ("trust", "view_adminauditlog"),
    },
    "KazeB Trust & Safety": {
        ("trust", "view_admin_dashboard"),
        ("accounts", "view_user"),
        ("listings", "view_listing"),
        ("listings", "moderate_listing"),
        ("listings", "remove_listing"),
        ("trust", "view_report"),
        ("trust", "manage_report"),
        ("trust", "view_review"),
        ("trust", "delete_review"),
        ("trust", "view_phoneverification"),
        ("trust", "view_adminauditlog"),
    },
}


class Command(BaseCommand):
    help = "Create or update the limited KazeB administrator role groups."

    @transaction.atomic
    def handle(self, *args, **options):
        for role_name, permission_keys in ROLE_PERMISSIONS.items():
            permissions = list(
                Permission.objects.filter(
                    content_type__app_label__in={app for app, _ in permission_keys},
                    codename__in={codename for _, codename in permission_keys},
                ).select_related("content_type")
            )
            resolved = {
                (permission.content_type.app_label, permission.codename): permission
                for permission in permissions
            }
            missing = permission_keys - resolved.keys()
            if missing:
                missing_labels = ", ".join(
                    f"{app}.{codename}" for app, codename in sorted(missing)
                )
                raise CommandError(
                    f"Missing permissions: {missing_labels}. Run migrations first."
                )

            group, created = Group.objects.get_or_create(name=role_name)
            previous = set(group.permissions.values_list("content_type__app_label", "codename"))
            desired = set(permission_keys)
            if previous != desired:
                group.permissions.set(resolved[key] for key in sorted(desired))
                record_admin_activity(
                    actor=None,
                    action=AdminAuditLog.Action.ADMIN_ROLE_CHANGED,
                    target_type="group",
                    target_id=group.pk,
                    target_label=role_name,
                    reason="Permissions synchronized by setup_admin_roles.",
                    details={
                        "before": [f"{app}.{code}" for app, code in sorted(previous)],
                        "after": [f"{app}.{code}" for app, code in sorted(desired)],
                    },
                )
            state = "created" if created else "synchronized"
            self.stdout.write(f"{role_name}: {state}")
