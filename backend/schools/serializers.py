from rest_framework import serializers

from .models import (
    AcademicSession, Campus, Classroom, Department, GradeLevel, GradingBand,
    GradingScale, Holiday, School, SchoolEvent, SchoolSetting, Section, Term,
)


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class CampusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campus
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class AcademicSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicSession
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class TermSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source="session.name", read_only=True)

    class Meta:
        model = Term
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class GradeLevelSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = GradeLevel
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class SectionSerializer(serializers.ModelSerializer):
    grade_level_name = serializers.CharField(source="grade_level.name", read_only=True)
    class_teacher_name = serializers.CharField(source="class_teacher.get_full_name", read_only=True)
    enrolled = serializers.IntegerField(read_only=True)

    class Meta:
        model = Section
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ClassroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class GradingBandSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingBand
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class GradingScaleSerializer(serializers.ModelSerializer):
    bands = GradingBandSerializer(many=True, read_only=True)

    class Meta:
        model = GradingScale
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class SchoolEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolEvent
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class SchoolSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolSetting
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
