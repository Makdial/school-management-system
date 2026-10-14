from rest_framework import serializers

from .models import AttendanceCorrection, StaffAttendance, StudentAttendance


class StudentAttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)

    class Meta:
        model = StudentAttendance
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "recorded_by"]

    def validate(self, attrs):
        session = attrs.get("session") or getattr(self.instance, "session", None)
        date = attrs.get("date") or getattr(self.instance, "date", None)
        student = attrs.get("student") or getattr(self.instance, "student", None)
        if session and date and not (session.start_date <= date <= session.end_date):
            raise serializers.ValidationError("Date falls outside the selected academic session.")
        if student and session and student.school_id != session.school_id:
            raise serializers.ValidationError("Student does not belong to this school.")
        return attrs


class BulkAttendanceItemSerializer(serializers.Serializer):
    student = serializers.UUIDField()
    status = serializers.ChoiceField(choices=[c[0] for c in StudentAttendance.STATUS])
    remark = serializers.CharField(required=False, allow_blank=True)


class BulkAttendanceSerializer(serializers.Serializer):
    session = serializers.UUIDField()
    section = serializers.UUIDField(required=False, allow_null=True)
    date = serializers.DateField()
    records = BulkAttendanceItemSerializer(many=True)


class StaffAttendanceSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.full_name", read_only=True)

    class Meta:
        model = StaffAttendance
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "recorded_by"]


class AttendanceCorrectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceCorrection
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "corrected_by"]
