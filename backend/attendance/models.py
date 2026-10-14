from django.db import models

from core.models import BaseModel, SchoolScopedModel


class StudentAttendance(BaseModel):
    STATUS = [
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
        ("LATE", "Late"),
        ("EXCUSED", "Excused"),
    ]

    school = models.ForeignKey("schools.School", on_delete=models.CASCADE, related_name="student_attendance")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="attendance")
    session = models.ForeignKey("schools.AcademicSession", on_delete=models.CASCADE, related_name="attendance")
    section = models.ForeignKey("schools.Section", null=True, blank=True, on_delete=models.SET_NULL)
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=STATUS, default="PRESENT")
    remark = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = [("student", "session", "date")]
        ordering = ["-date"]
        indexes = [models.Index(fields=["school", "date"]), models.Index(fields=["section", "date"])]

    def __str__(self):
        return f"{self.student} {self.date} {self.status}"


class StaffAttendance(BaseModel):
    STATUS = [
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
        ("LATE", "Late"),
        ("LEAVE", "On Leave"),
        ("EXCUSED", "Excused"),
    ]

    school = models.ForeignKey("schools.School", on_delete=models.CASCADE, related_name="staff_attendance")
    staff = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="staff_attendance")
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=STATUS, default="PRESENT")
    remark = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="recorded_staff_attendance"
    )

    class Meta:
        unique_together = [("staff", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.staff} {self.date} {self.status}"


class AttendanceCorrection(BaseModel):
    """Immutable audit trail for attendance edits."""

    attendance = models.ForeignKey(
        StudentAttendance, on_delete=models.CASCADE, related_name="corrections"
    )
    previous_status = models.CharField(max_length=10)
    new_status = models.CharField(max_length=10)
    reason = models.TextField(blank=True)
    corrected_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]
