from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsAcademicStaff, IsAnyRole, IsSchoolAdmin

from . import services
from .models import AttendanceCorrection, StaffAttendance, StudentAttendance
from .serializers import (
    AttendanceCorrectionSerializer, BulkAttendanceSerializer,
    StaffAttendanceSerializer, StudentAttendanceSerializer,
)


class StudentAttendanceViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentAttendance.objects.select_related("student", "session", "section")
    serializer_class = StudentAttendanceSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["date", "status", "section", "session", "student"]
    search_fields = ["student__first_name", "student__last_name", "student__admission_number"]
    ordering_fields = ["date", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(student__user=user)
        if user.user_type == "PARENT":
            return qs.filter(student__guardian_links__guardian__user=user).distinct()
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "bulk"):
            return [IsAcademicStaff()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(
            school=self.request.user.school,
            recorded_by=self.request.user,
        )

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk(self, request):
        serializer = BulkAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        from schools.models import AcademicSession, Section

        school = request.user.school
        session = AcademicSession.objects.get(pk=data["session"], school=school)
        section = None
        if data.get("section"):
            section = Section.objects.filter(pk=data["section"], school=school).first()
        saved = services.bulk_upsert_attendance(
            school=school,
            session=session,
            attendance_date=data["date"],
            section=section,
            records=data["records"],
            user=request.user,
        )
        return Response({"saved": len(saved)}, status=201)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        return Response(
            services.attendance_summary(
                school=request.user.school,
                session=request.query_params.get("session"),
                section=request.query_params.get("section"),
                student=request.query_params.get("student"),
            )
        )


class StaffAttendanceViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StaffAttendance.objects.select_related("staff")
    serializer_class = StaffAttendanceSerializer
    permission_classes = [IsSchoolAdmin]
    filterset_fields = ["date", "status", "staff"]

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school, recorded_by=self.request.user)


class AttendanceCorrectionViewSet(SchoolScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AttendanceCorrection.objects.select_related("attendance", "corrected_by")
    serializer_class = AttendanceCorrectionSerializer
    permission_classes = [IsSchoolAdmin]
    filterset_fields = ["attendance"]
