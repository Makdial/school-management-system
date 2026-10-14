from django.utils import timezone
from rest_framework import serializers

from .models import Assignment, Submission


class SubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = Submission
        fields = "__all__"
        read_only_fields = [
            "id", "created_at", "updated_at", "submitted_at", "score",
            "feedback", "graded_by", "graded_at", "is_late", "student",
        ]


class AssignmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="class_subject.subject.name", read_only=True)
    grade_level_name = serializers.CharField(source="class_subject.grade_level.name", read_only=True)
    submission_count = serializers.IntegerField(read_only=True)
    teacher_name = serializers.CharField(source="created_by.full_name", read_only=True, default=None)

    class Meta:
        model = Assignment
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "created_by"]

    def validate_max_score(self, value):
        if value <= 0:
            raise serializers.ValidationError("Maximum score must be positive.")
        return value


class GradeSubmissionSerializer(serializers.Serializer):
    score = serializers.DecimalField(max_digits=6, decimal_places=2)
    feedback = serializers.CharField(required=False, allow_blank=True)

    def validate_score(self, value):
        if value < 0:
            raise serializers.ValidationError("Score cannot be negative.")
        return value
