from django.db import transaction
from django.utils import timezone

from academics.models import StudentEnrollment
from core.services import generate_sequence_number
from students.models import Student

from .models import AdmissionApplication


@transaction.atomic
def submit_application(school, **data):
    if not data.get("application_number"):
        data["application_number"] = generate_sequence_number(
            "APP", AdmissionApplication, "application_number", school=school
        )
    data.setdefault("status", "SUBMITTED")
    return AdmissionApplication.objects.create(school=school, **data)


@transaction.atomic
def approve_application(application, user):
    application.status = "APPROVED"
    application.reviewed_by = user
    application.reviewed_at = timezone.now()
    application.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
    return application


@transaction.atomic
def reject_application(application, user, reason=""):
    application.status = "REJECTED"
    application.reviewed_by = user
    application.reviewed_at = timezone.now()
    if reason:
        application.notes = (application.notes + "\n" + reason).strip()
    application.save(update_fields=["status", "reviewed_by", "reviewed_at", "notes", "updated_at"])
    return application


@transaction.atomic
def enroll_application(application, section=None, user=None):
    """Convert an approved application into an enrolled student record.

    Idempotent: enrolling twice returns the existing student.
    """
    if application.created_student_id:
        return application.created_student
    if application.status not in ("APPROVED", "ENROLLED"):
        raise ValueError("Only approved applications can be enrolled.")

    student = Student.objects.create(
        school=application.school,
        admission_number=generate_sequence_number(
            "ADM", Student, "admission_number", school=application.school
        ),
        first_name=application.applicant_first_name,
        last_name=application.applicant_last_name,
        gender=application.gender,
        date_of_birth=application.date_of_birth,
        status="ACTIVE",
    )
    StudentEnrollment.objects.create(
        school=application.school,
        student=student,
        session=application.session,
        grade_level=application.grade_level,
        section=section,
        status="ACTIVE",
    )
    application.status = "ENROLLED"
    application.created_student = student
    if user:
        application.reviewed_by = user
    application.save(update_fields=["status", "created_student", "reviewed_by", "updated_at"])
    return student
