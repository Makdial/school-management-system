from rest_framework import viewsets

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsTransportManager

from .models import StudentTransportAssignment, TransportRoute, TransportStop, Vehicle, VehicleMaintenance
from .serializers import (
    StudentTransportAssignmentSerializer, TransportRouteSerializer,
    TransportStopSerializer, VehicleMaintenanceSerializer, VehicleSerializer,
)


class VehicleViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsTransportManager]
    filterset_fields = ["status"]
    search_fields = ["plate_number", "make", "model"]


class TransportRouteViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = TransportRoute.objects.prefetch_related("stops").select_related("vehicle")
    serializer_class = TransportRouteSerializer
    permission_classes = [IsTransportManager]
    search_fields = ["name", "code"]


class TransportStopViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = TransportStop.objects.select_related("route")
    serializer_class = TransportStopSerializer
    permission_classes = [IsTransportManager]
    filterset_fields = ["route"]


class StudentTransportAssignmentViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentTransportAssignment.objects.select_related("student", "route", "stop")
    serializer_class = StudentTransportAssignmentSerializer
    permission_classes = [IsTransportManager]
    filterset_fields = ["route", "student", "is_active"]

    def perform_create(self, serializer):
        student = serializer.validated_data["student"]
        serializer.save(school_id=student.school_id)


class VehicleMaintenanceViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = VehicleMaintenance.objects.select_related("vehicle")
    serializer_class = VehicleMaintenanceSerializer
    permission_classes = [IsTransportManager]
    filterset_fields = ["vehicle"]
