from django.db import models

from core.models import BaseModel, SchoolScopedModel


class Vehicle(SchoolScopedModel):
    STATUS = [("ACTIVE", "Active"), ("MAINTENANCE", "Under Maintenance"), ("INACTIVE", "Inactive"), ("SOLD", "Sold")]

    plate_number = models.CharField(max_length=40)
    make = models.CharField(max_length=80, blank=True)
    model = models.CharField(max_length=80, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    capacity = models.PositiveIntegerField(default=40)
    driver_name = models.CharField(max_length=120, blank=True)
    driver_phone = models.CharField(max_length=32, blank=True)
    attendant_name = models.CharField(max_length=120, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    inspection_expiry = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="ACTIVE")

    class Meta:
        unique_together = [("school", "plate_number")]
        ordering = ["plate_number"]

    def __str__(self):
        return f"{self.plate_number} ({self.make} {self.model})"


class TransportRoute(SchoolScopedModel):
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=32, blank=True)
    vehicle = models.ForeignKey(
        Vehicle, null=True, blank=True, on_delete=models.SET_NULL, related_name="routes"
    )
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("school", "name")]
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def student_count(self):
        return self.student_assignments.filter(is_active=True).count()


class TransportStop(BaseModel):
    route = models.ForeignKey(TransportRoute, on_delete=models.CASCADE, related_name="stops")
    name = models.CharField(max_length=160)
    pickup_time = models.TimeField(null=True, blank=True)
    dropoff_time = models.TimeField(null=True, blank=True)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sequence = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["sequence", "name"]

    def __str__(self):
        return f"{self.name} ({self.route.name})"


class StudentTransportAssignment(SchoolScopedModel):
    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="transport_assignments"
    )
    route = models.ForeignKey(TransportRoute, on_delete=models.CASCADE, related_name="student_assignments")
    stop = models.ForeignKey(
        TransportStop, null=True, blank=True, on_delete=models.SET_NULL, related_name="student_assignments"
    )
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [("student", "route")]

    def __str__(self):
        return f"{self.student} -> {self.route}"


class VehicleMaintenance(BaseModel):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="maintenance_records")
    description = models.CharField(max_length=240)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    performed_on = models.DateField()
    next_service_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-performed_on"]

    def __str__(self):
        return f"{self.vehicle} {self.description}"
