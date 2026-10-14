from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsSchoolAdmin
from students.serializers import StudentSerializer

from . import services
from .models import AdmissionApplication, AdmissionDocument
from .serializers import AdmissionApplicationSerializer, AdmissionDocumentSerializer


class AdmissionApplicationViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = AdmissionApplication.objects.select_related("grade_level", "session", "created_student")
    serializer_class = AdmissionApplicationSerializer
    permission_classes = [IsSchoolAdmin]
    filterset_fields = ["status", "session", "grade_level"]
    search_fields = ["applicant_first_name", "applicant_last_name", "application_number"]
    ordering_fields = ["created_at", "status"]

    def perform_create(self, serializer):
        school = self.request.user.school
        instance = services.submit_application(school=school, **serializer.validated_data)
        serializer.instance = instance

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        app = self.get_object()
        services.approve_application(app, request.user)
        return Response(self.get_serializer(app).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        app = self.get_object()
        services.reject_application(app, request.user, request.data.get("reason", ""))
        return Response(self.get_serializer(app).data)

    @action(detail=True, methods=["post"])
    def enroll(self, request, pk=None):
        app = self.get_object()
        section_id = request.data.get("section")
        section = None
        if section_id:
            from schools.models import Section

            section = Section.objects.filter(pk=section_id, school=request.user.school).first()
        student = services.enroll_application(app, section=section, user=request.user)
        return Response(StudentSerializer(student).data, status=201)


class AdmissionDocumentViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = AdmissionDocument.objects.select_related("application")
    serializer_class = AdmissionDocumentSerializer
    permission_classes = [IsSchoolAdmin]
    filterset_fields = ["application"]
