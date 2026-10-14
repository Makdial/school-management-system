from rest_framework import serializers

from .models import Contract, LeaveRequest, LeaveType, StaffProfile


class StaffProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = StaffProfile
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        privileged = request and (
            request.user.is_superuser
            or request.user.user_type in ("SUPERADMIN", "SCHOOL_ADMIN", "HR_MANAGER")
        )
        if not privileged:
            data.pop("salary", None)
            data.pop("national_id", None)
            data.pop("emergency_phone", None)
        return data


class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.user.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    days = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = [
            "id", "created_at", "updated_at", "school", "approved_by", "reviewed_at",
        ]

    def validate(self, attrs):
        start = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        end = attrs.get("end_date") or getattr(self.instance, "end_date", None)
        if start and end and end < start:
            raise serializers.ValidationError("End date cannot be before the start date.")
        return attrs
