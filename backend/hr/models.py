from django.db import models

from core.models import BaseModel, SchoolScopedModel


class StaffProfile(SchoolScopedModel):
    EMPLOYMENT_TYPES = [
        ("FULL_TIME", "Full Time"),
        ("PART_TIME", "Part Time"),
        ("CONTRACT", "Contract"),
        ("INTERN", "Intern"),
    ]
    STATUS = [("ACTIVE", "Active"), ("ON_LEAVE", "On Leave"), ("SUSPENDED", "Suspended"), ("TERMINATED", "Terminated")]

    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="staff_profile"
    )
    employee_id = models.CharField(max_length=40)
    department = models.ForeignKey(
        "schools.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="staff"
    )
    job_title = models.CharField(max_length=120)
    employment_type = models.CharField(max_length=12, choices=EMPLOYMENT_TYPES, default="FULL_TIME")
    hire_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="ACTIVE")
    national_id = models.CharField(max_length=40, blank=True)
    emergency_contact = models.CharField(max_length=120, blank=True)
    emergency_phone = models.CharField(max_length=32, blank=True)
    qualifications = models.TextField(blank=True)

    class Meta:
        unique_together = [("school", "employee_id")]
        ordering = ["user__first_name", "user__last_name"]

    def __str__(self):
        return f"{self.user} ({self.employee_id})"


class Contract(BaseModel):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="contracts")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2)
    document = models.FileField(upload_to="hr/contracts/", blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]


class LeaveType(SchoolScopedModel):
    name = models.CharField(max_length=120)
    max_days_per_year = models.PositiveIntegerField(default=30)
    is_paid = models.BooleanField(default=True)

    class Meta:
        unique_together = [("school", "name")]

    def __str__(self):
        return self.name


class LeaveRequest(SchoolScopedModel):
    STATUS = [("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")]

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="requests")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="PENDING")
    approved_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_leaves"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.staff} {self.leave_type} ({self.status})"

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1
