import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ("SUPERADMIN", "Super Administrator"),
        ("SCHOOL_ADMIN", "School Administrator"),
        ("PRINCIPAL", "Principal / Headteacher"),
        ("TEACHER", "Teacher"),
        ("STUDENT", "Student"),
        ("PARENT", "Parent / Guardian"),
        ("ACCOUNTANT", "Accountant"),
        ("LIBRARIAN", "Librarian"),
        ("TRANSPORT_MANAGER", "Transport Manager"),
        ("HR_MANAGER", "Human Resources Manager"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type = models.CharField(max_length=30, choices=USER_TYPE_CHOICES, default="STUDENT", db_index=True)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
    )
    phone_number = models.CharField(max_length=32, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)

    class Meta:
        db_table = "auth_user"
        ordering = ["first_name", "last_name", "username"]

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def full_name(self):
        return self.get_full_name() or self.username


class LoginAudit(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="login_audits")
    username = models.CharField(max_length=150, blank=True)
    success = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.username} {'ok' if self.success else 'failed'} @ {self.created_at:%Y-%m-%d %H:%M}"
