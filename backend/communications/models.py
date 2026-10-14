from django.db import models

from core.models import BaseModel, SchoolScopedModel


class Announcement(SchoolScopedModel):
    AUDIENCE = [
        ("ALL", "Everyone"),
        ("STAFF", "Staff"),
        ("STUDENTS", "Students"),
        ("PARENTS", "Parents"),
        ("TEACHERS", "Teachers"),
    ]

    title = models.CharField(max_length=200)
    body = models.TextField()
    audience = models.CharField(max_length=16, choices=AUDIENCE, default="ALL")
    attachment = models.FileField(upload_to="announcements/", blank=True, null=True)
    author = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    grade_level = models.ForeignKey(
        "schools.GradeLevel", null=True, blank=True, on_delete=models.SET_NULL, related_name="announcements"
    )
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Notification(BaseModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self):
        return self.title


class Message(BaseModel):
    sender = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="sent_messages")
    recipient = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="received_messages")
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sender} -> {self.recipient}"
