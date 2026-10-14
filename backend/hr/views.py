from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsHR, IsSchoolAdmin

from .models import Contract, LeaveRequest, LeaveType, StaffProfile
from .serializers import ContractSerializer, LeaveRequestSerializer, LeaveTypeSerializer, StaffProfileSerializer


class StaffProfileViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StaffProfile.objects.select_related("user", "department")
    serializer_class = StaffProfileSerializer
    permission_classes = [IsHR]
    filterset_fields = ["department", "status", "employment_type"]
    search_fields = ["user__first_name", "user__last_name", "employee_id", "job_title"]


class ContractViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Contract.objects.select_related("staff__user")
    serializer_class = ContractSerializer
    permission_classes = [IsHR]
    filterset_fields = ["staff"]


class LeaveTypeViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsSchoolAdmin]


class LeaveRequestViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.select_related("staff__user", "leave_type", "approved_by")
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsHR]
    filterset_fields = ["status", "staff", "leave_type"]

    def perform_create(self, serializer):
        staff = serializer.validated_data.get("staff")
        serializer.save(school_id=staff.school_id)

    @action(detail=True, methods=["post"], permission_classes=[IsSchoolAdmin])
    def approve(self, request, pk=None):
        leave = self.get_object()
        leave.status = "APPROVED"
        leave.approved_by = request.user
        leave.reviewed_at = timezone.now()
        leave.save(update_fields=["status", "approved_by", "reviewed_at", "updated_at"])
        return Response(self.get_serializer(leave).data)

    @action(detail=True, methods=["post"], permission_classes=[IsSchoolAdmin])
    def reject(self, request, pk=None):
        leave = self.get_object()
        leave.status = "REJECTED"
        leave.approved_by = request.user
        leave.reviewed_at = timezone.now()
        leave.save(update_fields=["status", "approved_by", "reviewed_at", "updated_at"])
        return Response(self.get_serializer(leave).data)
