from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsAcademicStaff, IsAnyRole, IsSchoolAdmin
from students.models import Student

from . import services
from .models import Exam, ExamSubject, ReportCard, StudentMark
from .serializers import (
    ExamSerializer, ExamSubjectSerializer, MarkEntrySerializer,
    ReportCardSerializer, StudentMarkSerializer,
)


class ExamViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Exam.objects.select_related("session", "term")
    serializer_class = ExamSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["session", "term", "exam_type", "is_published"]
    search_fields = ["name"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsSchoolAdmin()]
        return super().get_permissions()

    @action(detail=True, methods=["post"], permission_classes=[IsSchoolAdmin])
    def publish(self, request, pk=None):
        exam = self.get_object()
        services.publish_results(exam)
        return Response(self.get_serializer(exam).data)

    @action(detail=True, methods=["post"], permission_classes=[IsSchoolAdmin])
    def compute_results(self, request, pk=None):
        exam = self.get_object()
        cards = services.compute_report_cards(exam, user=request.user)
        return Response({"report_cards": len(cards)})


class ExamSubjectViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = ExamSubject.objects.select_related("exam", "class_subject__subject", "class_subject__grade_level")
    serializer_class = ExamSubjectSerializer
    permission_classes = [IsAcademicStaff]
    filterset_fields = ["exam", "class_subject"]

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)


class StudentMarkViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentMark.objects.select_related("student", "exam_subject__class_subject__subject", "exam_subject__exam")
    serializer_class = StudentMarkSerializer
    permission_classes = [IsAcademicStaff]
    filterset_fields = ["exam_subject", "student"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(student__user=user, exam_subject__exam__is_published=True)
        if user.user_type == "PARENT":
            return qs.filter(
                student__guardian_links__guardian__user=user,
                exam_subject__exam__is_published=True,
            ).distinct()
        return qs

    def perform_create(self, serializer):
        serializer.save(entered_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk(self, request):
        serializer = MarkEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        exam_subject = ExamSubject.objects.filter(
            pk=data["exam_subject"], school=request.user.school
        ).first()
        if not exam_subject:
            return Response({"detail": "Exam subject not found."}, status=404)
        services.enter_marks(exam_subject, data["marks"], request.user)
        return Response({"saved": len(data["marks"])}, status=201)


class ReportCardViewSet(SchoolScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ReportCard.objects.select_related("student", "exam")
    serializer_class = ReportCardSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["exam", "student"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(student__user=user, is_published=True)
        if user.user_type == "PARENT":
            return qs.filter(student__guardian_links__guardian__user=user, is_published=True).distinct()
        return qs
