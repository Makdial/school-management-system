from django.db import models

from core.models import SchoolScopedModel


class AdmissionApplication(SchoolScopedModel):
    STATUS = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("UNDER_REVIEW", "Under Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("ENROLLED", "Enrolled"),
    ]
    GENDER = [("M", "Male"), ("F", "Female"), ("O", "Other")]

    application_number = models.CharField(max_length=32)
    session = models.ForeignKey("schools.AcademicSession", on_delete=models.CASCADE, related_name="applications")
    grade_level = models.ForeignKey("schools.GradeLevel", on_delete=models.PROTECT, related_name="applications")

    applicant_first_name = models.CharField(max_length=80)
    applicant_last_name = models.CharField(max_length=80)
    gender = models.CharField(max_length=1, choices=GENDER, default="M")
    date_of_birth = models.DateField(null=True, blank=True)
    previous_school = models.CharField(max_length=200, blank=True)

    guardian_name = models.CharField(max_length=160)
    guardian_phone = models.CharField(max_length=32, blank=True)
    guardian_email = models.EmailField(blank=True)
    guardian_relationship = models.CharField(max_length=40, default="Parent")
    address = models.TextField(blank=True)

    status = models.CharField(max_length=16, choices=STATUS, default="SUBMITTED", db_index=True)
    notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_applications"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_student = models.ForeignKey(
        "students.Student", null=True, blank=True, on_delete=models.SET_NULL, related_name="admission_application"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["school", "status"])]

    def __str__(self):
        return f"{self.first_name} {self.last_name} [{self.status}]"

    @property
    def first_name(self):
        return self.applicant_first_name

    @property
    def last_name(self):
        return self.applicant_last_name

    @property
    def full_name(self):
        return f"{self.applicant_first_name} {self.applicant_last_name}"


class AdmissionDocument(SchoolScopedModel):
    application = models.ForeignKey(AdmissionApplication, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=160)
    file = models.FileField(upload_to="admission_documents/")

    def __str__(self):
        return self.title
