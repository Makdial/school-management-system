from rest_framework import viewsets

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsSchoolAdmin

from .models import ActivityLog, AuditLog
from .serializers import ActivityLogSerializer, AuditLogSerializer


class AuditLogViewSet(SchoolScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("actor")
    serializer_class = AuditLogSerializer
    permission_classes = [IsSchoolAdmin]
    filterset_fields = ["action", "model_name", "actor"]
    search_fields = ["action", "model_name", "object_id"]


class ActivityLogViewSet(SchoolScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ActivityLog.objects.select_related("user")
    serializer_class = ActivityLogSerializer
    permission_classes = [IsSchoolAdmin]
    filterset_fields = ["level", "user"]
