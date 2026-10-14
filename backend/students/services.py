from django.db import transaction

from core.services import generate_sequence_number

from .models import Student


@transaction.atomic
def create_student(school, **kwargs):
    """Create a student, generating a unique admission number when omitted."""
    if not kwargs.get("admission_number"):
        kwargs["admission_number"] = generate_sequence_number(
            "ADM", Student, "admission_number", school=school
        )
    return Student.objects.create(school=school, **kwargs)
