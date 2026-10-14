from rest_framework import viewsets

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsAnyRole, IsSchoolAdmin

from .models import Guardian, Student, StudentDocument, StudentGuardian, StudentStatusHistory
from .serializers import (
    GuardianSerializer, StudentDocumentSerializer, StudentSerializer,
    StudentGuardianSerializer, StudentStatusHistorySerializer,
)


class StaffWriteMixin:
    """Any role may read, only school admins may write."""

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsSchoolAdmin()]
        return [IsAnyRole()]


class StudentViewSet(StaffWriteMixin, SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Student.objects.select_related("user", "school")
    serializer_class = StudentSerializer
    permission_classes = [IsAnyRole]
    search_fields = ["first_name", "last_name", "admission_number", "other_names"]
    filterset_fields = ["status", "gender"]
    ordering_fields = ["first_name", "last_name", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(user=user)
        if user.user_type == "PARENT":
            return qs.filter(guardian_links__guardian__user=user).distinct()
        return qs


class GuardianViewSet(StaffWriteMixin, SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Guardian.objects.select_related("user")
    serializer_class = GuardianSerializer
    permission_classes = [IsAnyRole]
    search_fields = ["first_name", "last_name", "phone_number", "email"]
    filterset_fields = ["relationship"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "PARENT":
            return qs.filter(user=user)
        return qs


class StudentGuardianViewSet(StaffWriteMixin, SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentGuardian.objects.select_related("student", "guardian")
    serializer_class = StudentGuardianSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["student", "guardian", "is_primary"]

    def get_school_id(self):
        return self.request.user.school_id


class StudentDocumentViewSet(StaffWriteMixin, SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentDocument.objects.select_related("student")
    serializer_class = StudentDocumentSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["student"]


class StudentStatusHistoryViewSet(SchoolScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = StudentStatusHistory.objects.select_related("student", "changed_by")
    serializer_class = StudentStatusHistorySerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["student", "status"]
