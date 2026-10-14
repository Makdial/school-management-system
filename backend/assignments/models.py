from django.db import models

from core.models import BaseModel, SchoolScopedModel

ALLOWED_UPLOAD_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "txt", "png", "jpg", "jpeg", "zip"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def validate_upload(file):
    """Reject unsafe or oversized assignment/submission attachments."""
    import os

    from django.core.exceptions import ValidationError

    ext = os.path.splitext(file.name)[1].lstrip(".").lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError("Unsupported file type.")
    if file.size and file.size > MAX_UPLOAD_BYTES:
        raise ValidationError("File is too large (maximum 10 MB).")


class Assignment(SchoolScopedModel):
    class_subject = models.ForeignKey(
        "academics.ClassSubject", on_delete=models.CASCADE, related_name="assignments"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField()
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    attachment = models.FileField(upload_to="assignments/", blank=True, null=True)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-due_date"]

    def __str__(self):
        return self.title


class Submission(BaseModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="submissions")
    content = models.TextField(blank=True)
    file = models.FileField(upload_to="submissions/", blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    graded_at = models.DateTimeField(null=True, blank=True)
    is_late = models.BooleanField(default=False)

    class Meta:
        unique_together = [("assignment", "student")]
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.student} -> {self.assignment}"
