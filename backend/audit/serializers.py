from rest_framework import serializers

from .models import ActivityLog, AuditLog


class ReadOnlyModelSerializer(serializers.ModelSerializer):
    """Model serializer whose fields can never be written to.

    Used for immutable audit/activity records. ``read_only_fields`` cannot be
    set to the string ``"__all__"`` (DRF requires a list/tuple), so all fields
    are marked read-only in one place here instead.
    """

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


class AuditLogSerializer(ReadOnlyModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = "__all__"


class ActivityLogSerializer(ReadOnlyModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True, default=None)

    class Meta:
        model = ActivityLog
        fields = "__all__"
