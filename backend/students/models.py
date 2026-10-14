from django.db import models

from core.models import BaseModel, SchoolScopedModel


class Student(SchoolScopedModel):
    GENDER = [("M", "Male"), ("F", "Female"), ("O", "Other")]
    STATUS = [
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("GRADUATED", "Graduated"),
        ("TRANSFERRED", "Transferred"),
        ("SUSPENDED", "Suspended"),
    ]

    user = models.OneToOneField(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="student_profile"
    )
    admission_number = models.CharField(max_length=32)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    other_names = models.CharField(max_length=80, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER, default="M")
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=80, blank=True)
    religion = models.CharField(max_length=60, blank=True)
    blood_group = models.CharField(max_length=8, blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    photo = models.ImageField(upload_to="students/photos/", blank=True, null=True)
    current_grade_level = models.ForeignKey(
        "schools.GradeLevel", null=True, blank=True, on_delete=models.SET_NULL, related_name="students"
    )
    section = models.ForeignKey(
        "schools.Section", null=True, blank=True, on_delete=models.SET_NULL, related_name="students"
    )
    status = models.CharField(max_length=16, choices=STATUS, default="ACTIVE", db_index=True)
    admission_date = models.DateField(null=True, blank=True)
    medical_notes = models.TextField(blank=True)
    previous_school = models.CharField(max_length=180, blank=True)
    blood_group_note = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = [("school", "admission_number")]
        ordering = ["last_name", "first_name"]
        indexes = [models.Index(fields=["school", "status"])]

    def __str__(self):
        return f"{self.full_name} ({self.admission_number})"

    @property
    def full_name(self):
        return " ".join(part for part in [self.first_name, self.other_names, self.last_name] if part)


class Guardian(SchoolScopedModel):
    user = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="guardian_profiles"
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    relationship = models.CharField(max_length=40, default="Parent")
    phone_number = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    occupation = models.CharField(max_length=120, blank=True)
    address = models.TextField(blank=True)
    national_id = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class StudentGuardian(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="guardian_links")
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name="student_links")
    is_primary = models.BooleanField(default=False)

    class Meta:
        unique_together = [("student", "guardian")]

    def __str__(self):
        return f"{self.guardian} -> {self.student}"


class StudentDocument(SchoolScopedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=160)
    file = models.FileField(upload_to="student_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title


class StudentStatusHistory(SchoolScopedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=16)
    note = models.TextField(blank=True)
    changed_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
