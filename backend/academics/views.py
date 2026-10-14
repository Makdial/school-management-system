from rest_framework import viewsets

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsAcademicStaff, IsAnyRole, IsSchoolAdmin

from .models import ClassSubject, StudentEnrollment, Subject
from .serializers import ClassSubjectSerializer, StudentEnrollmentSerializer, SubjectSerializer


class SubjectViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Subject.objects.select_related("department")
    serializer_class = SubjectSerializer
    permission_classes = [IsAnyRole]
    search_fields = ["name", "code"]
    filterset_fields = ["department", "is_elective"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsSchoolAdmin()]
        return super().get_permissions()


class ClassSubjectViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = ClassSubject.objects.select_related("subject", "grade_level", "teacher", "session")
    serializer_class = ClassSubjectSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["session", "grade_level", "subject", "teacher"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsSchoolAdmin()]
        return super().get_permissions()


class StudentEnrollmentViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentEnrollment.objects.select_related("student", "session", "grade_level", "section")
    serializer_class = StudentEnrollmentSerializer
    permission_classes = [IsAcademicStaff]
    filterset_fields = ["session", "grade_level", "section", "status"]
    search_fields = ["student__first_name", "student__last_name", "student__admission_number"]
