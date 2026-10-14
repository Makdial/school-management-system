from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.permissions import IsAcademicStaff, IsAnyRole

from .models import Assignment, Submission
from .serializers import AssignmentSerializer, SubmissionSerializer


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.select_related(
        "class_subject__subject", "class_subject__grade_level", "created_by"
    )
    serializer_class = AssignmentSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["class_subject", "is_published"]
    search_fields = ["title", "description"]
    pagination_class = __import__("core.pagination", fromlist=["StandardPagination"]).StandardPagination

    def get_school_id(self):
        user = self.request.user
        if user.is_superuser or user.user_type == "SUPERADMIN":
            return self.request.query_params.get("school")
        return user.school_id

    def get_queryset(self):
        qs = super().get_queryset()
        school_id = self.get_school_id()
        if school_id:
            qs = qs.filter(school_id=school_id)
        elif not (self.request.user.is_superuser or self.request.user.user_type == "SUPERADMIN"):
            return qs.none()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(
                is_published=True,
                class_subject__grade_level__enrollments__student__user=user,
            ).distinct()
        if user.user_type == "PARENT":
            return qs.filter(
                is_published=True,
                class_subject__grade_level__enrollments__student__guardian_links__guardian__user=user,
            ).distinct()
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAcademicStaff()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(school_id=self.request.user.school_id, created_by=self.request.user)


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.select_related("student", "assignment")
    serializer_class = SubmissionSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["assignment", "student"]
    pagination_class = __import__("core.pagination", fromlist=["StandardPagination"]).StandardPagination

    def get_school_id(self):
        user = self.request.user
        if user.is_superuser or user.user_type == "SUPERADMIN":
            return self.request.query_params.get("school")
        return user.school_id

    def get_queryset(self):
        qs = super().get_queryset()
        school_id = self.get_school_id()
        if school_id:
            qs = qs.filter(assignment__school_id=school_id)
        elif not (self.request.user.is_superuser or self.request.user.user_type == "SUPERADMIN"):
            return qs.none()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(student__user=user)
        if user.user_type == "PARENT":
            return qs.filter(student__guardian_links__guardian__user=user).distinct()
        return qs

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy", "grade"):
            return [IsAcademicStaff()]
        return super().get_permissions()

    def perform_create(self, serializer):
        user = self.request.user
        assignment = serializer.validated_data["assignment"]
        if user.school_id and assignment.school_id != user.school_id:
            raise PermissionDenied("Assignment belongs to another school.")
        student = getattr(user, "student_profile", None)
        if student is None:
            student = serializer.validated_data.get("student")
        if student is None:
            raise serializers.ValidationError({"student": "A student is required."})
        is_late = bool(assignment.due_date and timezone.now() > assignment.due_date)
        serializer.save(student=student, is_late=is_late)

    @action(detail=True, methods=["post"], permission_classes=[IsAcademicStaff])
    def grade(self, request, pk=None):
        submission = self.get_object()
        score = request.data.get("score")
        if score is None:
            raise serializers.ValidationError({"score": "Score is required."})
        max_score = submission.assignment.max_score
        if float(score) > float(max_score):
            raise serializers.ValidationError({"score": f"Cannot exceed {max_score}."})
        submission.score = score
        submission.feedback = request.data.get("feedback", "")
        submission.graded_by = request.user
        submission.graded_at = timezone.now()
        submission.save(update_fields=["score", "feedback", "graded_by", "graded_at", "updated_at"])
        return Response(self.get_serializer(submission).data)
