from django.db import models

from core.models import BaseModel, SchoolScopedModel


class Room(SchoolScopedModel):
    name = models.CharField(max_length=80)
    capacity = models.PositiveIntegerField(default=40)
    building = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = [("school", "name")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class TimetablePeriod(SchoolScopedModel):
    name = models.CharField(max_length=60)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_break = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order", "start_time"]
        unique_together = [("school", "name")]

    def __str__(self):
        return f"{self.name} ({self.start_time}-{self.end_time})"


class TimetableEntry(SchoolScopedModel):
    DAYS = [
        (0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"),
        (4, "Friday"), (5, "Saturday"), (6, "Sunday"),
    ]

    session = models.ForeignKey("schools.AcademicSession", on_delete=models.CASCADE, related_name="timetable_entries")
    section = models.ForeignKey("schools.Section", on_delete=models.CASCADE, related_name="timetable_entries")
    day_of_week = models.PositiveSmallIntegerField(choices=DAYS)
    period = models.ForeignKey(TimetablePeriod, on_delete=models.CASCADE, related_name="entries")
    subject = models.ForeignKey("academics.Subject", on_delete=models.CASCADE, related_name="timetable_entries")
    teacher = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="timetable_entries"
    )
    room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL, related_name="entries")
    is_published = models.BooleanField(default=False)

    class Meta:
        unique_together = [
            ("session", "section", "day_of_week", "period"),
        ]
        ordering = ["day_of_week", "period__order"]
        indexes = [models.Index(fields=["school", "session", "section"])]

    def __str__(self):
        return f"{self.section} {self.get_day_of_week_display()} {self.period}"
