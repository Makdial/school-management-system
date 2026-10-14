from django.db import models

from core.models import UUIDModel


class AuditLog(UUIDModel):
    school = models.ForeignKey(
        "schools.School", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    actor = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    action = models.CharField(max_length=120)
    model_name = models.CharField(max_length=120, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["school", "action"])]

    def __str__(self):
        return f"{self.action} by {self.actor_id} on {self.created_at:%Y-%m-%d %H:%M}"


class ActivityLog(UUIDModel):
    LEVELS = [("INFO", "Info"), ("WARNING", "Warning"), ("ERROR", "Error")]

    school = models.ForeignKey(
        "schools.School", null=True, blank=True, on_delete=models.SET_NULL, related_name="activity_logs"
    )
    user = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="activity_logs"
    )
    level = models.CharField(max_length=10, choices=LEVELS, default="INFO")
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.level}] {self.message[:60]}"
