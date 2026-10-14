from decimal import Decimal

from django.db import transaction

from core.services import money
from schools.models import GradingBand, GradingScale

from .models import ExamSubject, ReportCard, StudentMark


def resolve_grade(scale, percentage):
    if not scale:
        return ""
    band = GradingBand.objects.filter(
        scale=scale, min_score__lte=percentage, max_score__gte=percentage
    ).first()
    return band.grade if band else ""


def default_scale(school):
    return (
        GradingScale.objects.filter(school=school, is_default=True).first()
        or GradingScale.objects.filter(school=school).first()
    )


@transaction.atomic
def enter_marks(exam_subject, records, user):
    """Create/update marks for one exam subject with validation.

    ``records`` is a list of ``{student, marks_obtained, is_absent}``. Students
    that belong to a different school are ignored so no cross tenant data can
    be written.
    """
    if exam_subject.exam.is_published and user.user_type not in ("SUPERADMIN", "SCHOOL_ADMIN", "PRINCIPAL"):
        raise PermissionError("Published results are locked.")

    from students.models import Student

    ids = [str(row.get("student") or row.get("student_id")) for row in records]
    valid = {
        str(pk)
        for pk in Student.objects.filter(
            school=exam_subject.school, id__in=ids
        ).values_list("id", flat=True)
    }
    max_marks = Decimal(str(exam_subject.max_marks))

    saved = []
    for row in records:
        student_id = str(row.get("student") or row.get("student_id"))
        if not student_id or student_id not in valid:
            continue
        is_absent = bool(row.get("is_absent"))
        marks = Decimal("0") if is_absent else money(row.get("marks_obtained") or 0)
        if not is_absent and marks > max_marks:
            raise ValueError(
                f"Marks for student {student_id} exceed maximum {exam_subject.max_marks}."
            )
        if marks < 0:
            raise ValueError("Marks cannot be negative.")
        obj, _ = StudentMark.objects.update_or_create(
            exam_subject=exam_subject,
            student_id=student_id,
            defaults={
                "marks_obtained": marks,
                "is_absent": is_absent,
                "entered_by": user,
            },
        )
        saved.append(obj)
    return saved


def student_school(school, student_id):
    from students.models import Student

    return Student.objects.filter(pk=student_id, school=school).exists()


@transaction.atomic
def compute_report_cards(exam, user=None):
    """Compute report cards for every enrolled student of the exam's grade levels."""
    from academics.models import StudentEnrollment

    school = exam.school
    scale = default_scale(school)
    exam_subjects = list(
        ExamSubject.objects.filter(exam=exam).select_related("class_subject__grade_level")
    )
    if not exam_subjects:
        return []

    grade_ids = {es.class_subject.grade_level_id for es in exam_subjects}
    enrollments = StudentEnrollment.objects.filter(
        school=school, session=exam.session, grade_level_id__in=grade_ids, status="ACTIVE"
    ).select_related("student")

    cards = []
    for enrollment in enrollments:
        student = enrollment.student
        total = Decimal("0")
        max_total = Decimal("0")
        for es in exam_subjects:
            mark = StudentMark.objects.filter(exam_subject=es, student=student).first()
            if not mark:
                continue
            max_total += es.max_marks
            if not mark.is_absent:
                total += mark.marks_obtained
        average = (total / max_total * 100) if max_total else Decimal("0")
        average = money(average)
        card, _ = ReportCard.objects.update_or_create(
            student=student,
            exam=exam,
            defaults={
                "total_marks": money(total),
                "total_max": money(max_total),
                "average": average,
                "grade": resolve_grade(scale, float(average)),
            },
        )
        cards.append(card)

    # Rank within the exam
    ordered = sorted(cards, key=lambda c: c.average, reverse=True)
    for index, card in enumerate(ordered, start=1):
        card.position = index
        card.save(update_fields=["position"])
    return cards


@transaction.atomic
def publish_results(exam):
    exam.is_published = True
    exam.save(update_fields=["is_published", "updated_at"])
    ReportCard.objects.filter(exam=exam).update(is_published=True)
    return exam
