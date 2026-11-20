from .models import AdminAuditLog


def record_admin_activity(
    actor,
    action,
    target_type,
    target_id,
    target_label,
    reason="",
    details=None,
):
    return AdminAuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        target_label=str(target_label)[:255],
        reason=reason,
        details=details or {},
    )
