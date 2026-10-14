from django.core.exceptions import ValidationError
from django.db import models

from core.models import BaseModel, SchoolScopedModel


class Subject(SchoolScopedModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32)
    department = models.ForeignKey(
        "schools.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="subjects"
    )
    is_elective = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [("school", "code")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class ClassSubject(SchoolScopedModel):
    """A subject taught to a grade level within a session."""

    session = models.ForeignKey("schools.AcademicSession", on_delete=models.CASCADE, related_name="class_subjects")
    grade_level = models.ForeignKey("schools.GradeLevel", on_delete=models.CASCADE, related_name="class_subjects")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="class_assignments")
    teacher = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="teaching_assignments"
    )
    periods_per_week = models.PositiveIntegerField(default=1)
    is_compulsory = models.BooleanField(default=True)

    class Meta:
        unique_together = [("school", "session", "grade_level", "subject")]
        ordering = ["grade_level__level_order", "subject__name"]

    def __str__(self):
        return f"{self.grade_level.name} - {self.subject.name}"

    def clean(self):
        if self.teacher and self.teacher.user_type not in ("TEACHER", "PRINCIPAL", "SCHOOL_ADMIN", "SUPERADMIN"):
            raise ValidationError({"teacher": "Selected user cannot be assigned as a teacher."})


class StudentEnrollment(SchoolScopedModel):
    STATUS = [
        ("ACTIVE", "Active"),
        ("PROMOTED", "Promoted"),
        ("TRANSFERRED", "Transferred"),
        ("GRADUATED", "Graduated"),
        ("WITHDRAWN", "Withdrawn"),
    ]

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="enrollments")
    session = models.ForeignKey("schools.AcademicSession", on_delete=models.CASCADE, related_name="enrollments")
    grade_level = models.ForeignKey("schools.GradeLevel", on_delete=models.PROTECT, related_name="enrollments")
    section = models.ForeignKey("schools.Section", null=True, blank=True, on_delete=models.SET_NULL, related_name="enrollments")
    roll_number = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="ACTIVE")
    enrolled_on = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = [("student", "session")]
        ordering = ["-session__start_date", "student__last_name"]

    def __str__(self):
        return f"{self.student} @ {self.session}"

    def clean(self):
        if self.section and self.section.grade_level_id != self.grade_level_id:
            raise ValidationError({"section": "Section must belong to the selected grade level."})
