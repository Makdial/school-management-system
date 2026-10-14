from rest_framework import serializers

from .models import StudentTransportAssignment, TransportRoute, TransportStop, Vehicle, VehicleMaintenance


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class TransportStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportStop
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class TransportRouteSerializer(serializers.ModelSerializer):
    stops = TransportStopSerializer(many=True, read_only=True)
    vehicle_plate = serializers.CharField(source="vehicle.plate_number", read_only=True, default=None)
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = TransportRoute
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class StudentTransportAssignmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    route_name = serializers.CharField(source="route.name", read_only=True)
    stop_name = serializers.CharField(source="stop.name", read_only=True, default=None)

    class Meta:
        model = StudentTransportAssignment
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class VehicleMaintenanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleMaintenance
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
