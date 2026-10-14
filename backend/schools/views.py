from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedQuerysetMixin
from core.permissions import IsAnyRole, IsSchoolAdmin, IsSuperAdmin

from .models import (
    AcademicSession, Campus, Classroom, Department, GradeLevel, GradingBand,
    GradingScale, Holiday, School, SchoolEvent, SchoolSetting, Section, Term,
)
from .serializers import (
    AcademicSessionSerializer, CampusSerializer, ClassroomSerializer,
    DepartmentSerializer, GradeLevelSerializer, GradingBandSerializer,
    GradingScaleSerializer, HolidaySerializer, SchoolEventSerializer,
    SchoolSerializer, SchoolSettingSerializer, SectionSerializer, TermSerializer,
)


class SchoolViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolSerializer
    permission_classes = [IsSuperAdmin]
    queryset = School.objects.all()
    search_fields = ["name", "code", "email"]
    ordering_fields = ["name", "created_at"]

    @action(detail=False, methods=["get"], permission_classes=[IsAnyRole])
    def current(self, request):
        school = request.user.school
        if school is None:
            return Response({"detail": "No school linked to this account."}, status=404)
        return Response(self.get_serializer(school).data)


class SchoolScopedModelViewSet(SchoolScopedQuerysetMixin, viewsets.ModelViewSet):
    permission_classes = [IsSchoolAdmin]


class CampusViewSet(SchoolScopedModelViewSet):
    queryset = Campus.objects.select_related("school")
    serializer_class = CampusSerializer
    search_fields = ["name", "code"]


class AcademicSessionViewSet(SchoolScopedModelViewSet):
    queryset = AcademicSession.objects.all()
    serializer_class = AcademicSessionSerializer
    permission_classes = [IsAnyRole]
    search_fields = ["name"]
    ordering_fields = ["start_date", "name"]


class TermViewSet(SchoolScopedModelViewSet):
    queryset = Term.objects.select_related("session")
    serializer_class = TermSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["session"]


class DepartmentViewSet(SchoolScopedModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    search_fields = ["name", "code"]


class GradeLevelViewSet(SchoolScopedModelViewSet):
    queryset = GradeLevel.objects.all()
    serializer_class = GradeLevelSerializer
    search_fields = ["name", "code"]


class SectionViewSet(SchoolScopedModelViewSet):
    queryset = Section.objects.select_related("grade_level", "class_teacher")
    serializer_class = SectionSerializer
    filterset_fields = ["grade_level"]
    search_fields = ["name"]


class ClassroomViewSet(SchoolScopedModelViewSet):
    queryset = Classroom.objects.select_related("section")
    serializer_class = ClassroomSerializer
    filterset_fields = ["section"]


class GradingScaleViewSet(SchoolScopedModelViewSet):
    queryset = GradingScale.objects.prefetch_related("bands")
    serializer_class = GradingScaleSerializer


class GradingBandViewSet(SchoolScopedModelViewSet):
    queryset = GradingBand.objects.select_related("scale")
    serializer_class = GradingBandSerializer
    filterset_fields = ["scale"]


class HolidayViewSet(SchoolScopedModelViewSet):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [IsAnyRole]


class SchoolEventViewSet(SchoolScopedModelViewSet):
    queryset = SchoolEvent.objects.all()
    serializer_class = SchoolEventSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["event_type", "audience"]
    search_fields = ["title", "description"]


class SchoolSettingViewSet(SchoolScopedModelViewSet):
    queryset = SchoolSetting.objects.all()
    serializer_class = SchoolSettingSerializer
