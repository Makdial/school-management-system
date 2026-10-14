from rest_framework import serializers

from .models import Exam, ExamSubject, ReportCard, StudentMark


class ExamSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source="session.name", read_only=True)
    subject_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Exam
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class ExamSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="class_subject.subject.name", read_only=True)
    grade_level_name = serializers.CharField(source="class_subject.grade_level.name", read_only=True)

    class Meta:
        model = ExamSubject
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class StudentMarkSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    subject_name = serializers.CharField(source="exam_subject.class_subject.subject.name", read_only=True)
    grade = serializers.SerializerMethodField()

    class Meta:
        model = StudentMark
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "entered_by", "updated_on"]

    def get_grade(self, obj):
        return obj.grade

    def validate(self, attrs):
        exam_subject = attrs.get("exam_subject") or getattr(self.instance, "exam_subject", None)
        marks = attrs.get("marks_obtained")
        is_absent = attrs.get("is_absent", getattr(self.instance, "is_absent", False))
        if exam_subject and exam_subject.exam.is_published and not self.context["request"].user.is_superuser:
            if not self.context["request"].user.user_type in ("SUPERADMIN", "SCHOOL_ADMIN", "PRINCIPAL"):
                raise serializers.ValidationError("Results for this exam have been published and are locked.")
        if marks is not None and exam_subject and not is_absent:
            if marks < 0:
                raise serializers.ValidationError({"marks_obtained": "Marks cannot be negative."})
            if marks > exam_subject.max_marks:
                raise serializers.ValidationError(
                    {"marks_obtained": f"Marks cannot exceed the maximum of {exam_subject.max_marks}."}
                )
        return attrs

    def validate_student(self, student):
        request = self.context["request"]
        if request.user.school_id and student.school_id != request.user.school_id:
            raise serializers.ValidationError("Student belongs to another school.")
        return student


class MarkEntryItemSerializer(serializers.Serializer):
    student = serializers.UUIDField()
    marks_obtained = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=0)
    is_absent = serializers.BooleanField(required=False, default=False)


class MarkEntrySerializer(serializers.Serializer):
    exam_subject = serializers.UUIDField()
    marks = MarkEntryItemSerializer(many=True)


class ReportCardSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    exam_name = serializers.CharField(source="exam.name", read_only=True)

    class Meta:
        model = ReportCard
        fields = "__all__"
        # Report cards are derived from marks; never writable directly.
        read_only_fields = [
            "id", "created_at", "updated_at", "total_marks", "total_max",
            "average", "grade", "position",
        ]
