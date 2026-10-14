from rest_framework import serializers

from .models import ClassSubject, StudentEnrollment, Subject


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class ClassSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    grade_level_name = serializers.CharField(source="grade_level.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True, default=None)

    class Meta:
        model = ClassSubject
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]

    def validate(self, attrs):
        session = attrs.get("session") or getattr(self.instance, "session", None)
        grade = attrs.get("grade_level") or getattr(self.instance, "grade_level", None)
        subject = attrs.get("subject") or getattr(self.instance, "subject", None)
        school = self.context["request"].user.school
        if session and grade and grade.school_id != session.school_id:
            raise serializers.ValidationError("Grade level and session belong to different schools.")
        if subject and school and subject.school_id != school.id:
            raise serializers.ValidationError("Subject belongs to a different school.")
        return attrs


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    grade_level_name = serializers.CharField(source="grade_level.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)

    class Meta:
        model = StudentEnrollment
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]
