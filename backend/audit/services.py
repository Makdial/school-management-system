from .models import ActivityLog, AuditLog


def log_action(actor, action, obj=None, changes=None, school=None, ip_address=None):
    """Persist an immutable audit record for a sensitive operation."""
    return AuditLog.objects.create(
        school=school or getattr(actor, "school", None) or getattr(obj, "school", None),
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        model_name=obj.__class__.__name__ if obj is not None else "",
        object_id=str(getattr(obj, "pk", "") or ""),
        changes=changes or {},
        ip_address=ip_address,
    )


def log_activity(message, user=None, school=None, level="INFO", metadata=None):
    return ActivityLog.objects.create(
        school=school or getattr(user, "school", None),
        user=user if getattr(user, "is_authenticated", False) else None,
        level=level,
        message=message,
        metadata=metadata or {},
    )
