from rest_framework import serializers

from .models import AdmissionApplication, AdmissionDocument


class AdmissionDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionDocument
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class AdmissionApplicationSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    grade_level_name = serializers.CharField(source="grade_level.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)

    class Meta:
        model = AdmissionApplication
        fields = "__all__"
        read_only_fields = [
            "id", "created_at", "updated_at", "school", "reviewed_by",
            "reviewed_at", "created_student",
        ]
