"""School configuration / tenant models."""
from django.db import models

from core.models import BaseModel


class School(BaseModel):
    """A school institution. Root of the tenancy tree."""

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=32, unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    logo = models.ImageField(upload_to="schools/logos/", blank=True, null=True)
    motto = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    currency = models.CharField(max_length=8, default="USD")
    timezone = models.CharField(max_length=64, default="UTC")
    date_format = models.CharField(max_length=20, default="YYYY-MM-DD")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Campus(BaseModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="campuses")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_main = models.BooleanField(default=False)

    class Meta:
        unique_together = [("school", "code")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.school.code}/{self.name}"


class AcademicSession(BaseModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="sessions")
    name = models.CharField(max_length=64)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        unique_together = [("school", "name")]
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_current:
            AcademicSession.objects.filter(school=self.school, is_current=True).exclude(
                pk=self.pk
            ).update(is_current=False)


class Term(BaseModel):
    TERM_CHOICES = [("FIRST", "First Term"), ("SECOND", "Second Term"), ("THIRD", "Third Term")]

    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name="terms")
    name = models.CharField(max_length=32, choices=TERM_CHOICES, default="FIRST")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        unique_together = [("session", "name")]
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.session.name} {self.get_name_display()}"


class Department(BaseModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="departments")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [("school", "code")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class GradeLevel(BaseModel):
    """A class / grade level e.g. Grade 1 or Form 4."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="grade_levels")
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=32)
    level_order = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    next_level = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="previous_levels"
    )

    class Meta:
        unique_together = [("school", "code")]
        ordering = ["level_order", "name"]

    def __str__(self):
        return self.name


class Section(BaseModel):
    """A section / stream inside a grade level."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="sections")
    grade_level = models.ForeignKey(GradeLevel, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=60)
    capacity = models.PositiveIntegerField(default=40)
    class_teacher = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sections_led",
    )

    class Meta:
        unique_together = [("school", "grade_level", "name")]
        ordering = ["grade_level__level_order", "name"]

    def __str__(self):
        return f"{self.grade_level.name} {self.name}"


class Classroom(BaseModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="classrooms")
    name = models.CharField(max_length=80)
    capacity = models.PositiveIntegerField(default=40)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class GradingScale(BaseModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="grading_scales")
    name = models.CharField(max_length=80)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class GradingBand(BaseModel):
    scale = models.ForeignKey(GradingScale, on_delete=models.CASCADE, related_name="bands")
    grade = models.CharField(max_length=8)
    min_score = models.DecimalField(max_digits=6, decimal_places=2)
    max_score = models.DecimalField(max_digits=6, decimal_places=2)
    remark = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["-min_score"]
        unique_together = [("scale", "grade")]

    def __str__(self):
        return f"{self.grade} ({self.min_score}-{self.max_score})"

    @classmethod
    def grade_for(cls, scale, score):
        from decimal import Decimal

        score = Decimal(str(score))
        band = scale.bands.filter(min_score__lte=score, max_score__gte=score).first()
        return band.grade if band else None


class Holiday(BaseModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="holidays")
    name = models.CharField(max_length=120)
    date = models.DateField()
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["date"]
        unique_together = [("school", "date", "name")]

    def __str__(self):
        return f"{self.name} ({self.date})"


class SchoolEvent(BaseModel):
    EVENT_TYPES = [
        ("GENERAL", "General"),
        ("EXAM", "Examination"),
        ("MEETING", "Parent Meeting"),
        ("ACTIVITY", "School Activity"),
        ("HOLIDAY", "Holiday"),
    ]
    AUDIENCE = [
        ("ALL", "Everyone"),
        ("STAFF", "Staff"),
        ("STUDENTS", "Students"),
        ("PARENTS", "Parents"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=16, choices=EVENT_TYPES, default="GENERAL")
    audience = models.CharField(max_length=16, choices=AUDIENCE, default="ALL")
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=180, blank=True)

    class Meta:
        ordering = ["start"]

    def __str__(self):
        return self.title


class SchoolSetting(BaseModel):
    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name="settings")
    data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Settings for {self.school.code}"
