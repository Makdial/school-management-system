from rest_framework import serializers

from .models import Guardian, Student, StudentDocument, StudentGuardian, StudentStatusHistory


class GuardianSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    children_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Guardian
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class StudentGuardianSerializer(serializers.ModelSerializer):
    guardian_detail = GuardianSerializer(source="guardian", read_only=True)

    class Meta:
        model = StudentGuardian
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentDocument
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "uploaded_at"]


class StudentStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentStatusHistory
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "changed_at"]


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    current_section_name = serializers.SerializerMethodField()
    guardians = StudentGuardianSerializer(source="guardian_links", many=True, read_only=True)

    class Meta:
        model = Student
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]

    def get_current_section_name(self, obj):
        enrollment = obj.enrollments.filter(status="ACTIVE").select_related("section", "grade_level").first()
        if enrollment and enrollment.section:
            return f"{enrollment.grade_level.name} {enrollment.section.name}"
        return None


class StudentListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Student
        fields = [
            "id", "admission_number", "full_name", "first_name", "last_name",
            "gender", "status", "date_of_birth",
        ]
