"""Analytics and reporting services.

Every function here is *school scoped*: callers must pass an explicit
``school`` instance so a report can never leak records from another tenant.
All monetary values are returned as ``Decimal`` (quantised to 2 dp) and are
never converted to floats.
"""
from datetime import timedelta

from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from academics.models import ClassSubject, StudentEnrollment, Subject
from admissions.models import AdmissionApplication
from attendance.models import StaffAttendance, StudentAttendance
from core.permissions import FINANCE_ROLES, HR_ROLES
from core.services import money
from examinations.models import Exam, ReportCard
from finance.models import Invoice, Payment
from hr.models import LeaveRequest, StaffProfile
from library.models import Book, BookCopy, Borrowing
from schools.models import (
    AcademicSession, GradeLevel, Holiday, SchoolEvent, Section,
)
from students.models import Student
from transport.models import StudentTransportAssignment, TransportRoute, Vehicle


def resolve_school(request):
    """Return the school a report should be scoped to.

    Super administrators may select a school with ``?school=<id>``; without
    one they fall back to their own membership (which is normally ``None``).
    Regular users are hard scoped to their own school.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser or user.user_type == "SUPERADMIN":
        school_id = request.query_params.get("school") or request.query_params.get("school_id")
        if school_id:
            from schools.models import School

            return School.objects.filter(pk=school_id).first()
        return user.school
    return user.school


def _sum(queryset, field):
    value = queryset.aggregate(total=Sum(field))["total"]
    return money(value or 0)


def _date_range(request, default_days=30):
    today = timezone.localdate()
    start_raw = request.query_params.get("start")
    end_raw = request.query_params.get("end") or request.query_params.get("end_date")
    start = _parse_date(start_raw) or (today - timedelta(days=default_days))
    end = _parse_date(end_raw) or today
    if start > end:
        start, end = end, start
    return start, end


def _date_range_values(request, default_days=30):
    start, end = _date_range(request, default_days)
    return start.isoformat(), end.isoformat()


def _parse_date(value):
    if not value:
        return None
    try:
        return timezone.datetime.fromisoformat(str(value)).date()
    except (TypeError, ValueError):
        return None


def current_session(school):
    if school is None:
        return None
    return (
        AcademicSession.objects.filter(school=school, is_current=True).first()
        or AcademicSession.objects.filter(school=school).order_by("-start_date").first()
    )


def current_term(school):
    session = AcademicSession.objects.filter(school=school, is_current=True).first()
    if not session:
        return None
    return school.terms.filter(is_current=True).first() or school.terms.filter(session=session).first()


# --------------------------------------------------------------------- helpers
def _student_summary(school):
    base = Student.objects.filter(school=school)
    by_status = dict(base.values_list("status").annotate(c=Count("id")))
    by_gender = dict(
        (row["gender"], row["c"]) for row in base.values("gender").annotate(c=Count("id"))
    )
    by_grade = list(
        base.values(name=F("current_grade_level__name"))
        .annotate(count=Count("id"))
        .order_by("current_grade_level__level_order")
    )
    return {
        "total": base.count(),
        "active": base.filter(status="ACTIVE").count(),
        "by_status": by_status,
        "by_gender": by_gender,
        "by_grade": [
            {"grade": row["name"] or "Unassigned", "count": row["count"]} for row in by_grade
        ],
    }


def _attendance_summary(school, day=None):
    day = day or timezone.localdate()
    qs = StudentAttendance.objects.filter(school=school, date=day)
    rows = qs.values("status").annotate(c=Count("id"))
    counts = {key: 0 for key, _ in StudentAttendance.STATUS}
    for row in rows:
        counts[row["status"]] = row["c"]
    total = sum(counts.values())
    attended = counts.get("PRESENT", 0) + counts.get("LATE", 0)
    rate = round(attended / total * 100, 2) if total else 0.0
    return {"date": day.isoformat(), "counts": counts, "total": total, "rate": rate}


def _admission_summary(school):
    qs = AdmissionApplication.objects.filter(school=school)
    rows = qs.values("status").annotate(c=Count("id"))
    counts = {key: 0 for key, _ in AdmissionApplication.STATUS}
    for row in rows:
        counts[row["status"]] = row["c"]
    return {"total": qs.count(), "by_status": counts}


def _exam_summary(school):
    exams = Exam.objects.filter(school=school)
    report_cards = ReportCard.objects.filter(exam__school=school)
    return {
        "total": exams.count(),
        "published": exams.filter(is_published=True).count(),
        "report_cards": report_cards.count(),
        "published_report_cards": report_cards.filter(is_published=True).count(),
    }


def _finance_summary(school):
    invoices = Invoice.objects.filter(school=school)
    return {
        "currency": school.currency if school else "USD",
        "invoiced": _sum(invoices.exclude(status="CANCELLED"), "total_amount"),
        "collected": _sum(Payment.objects.filter(school=school, status="COMPLETED"), "amount"),
        "outstanding": _sum(invoices.exclude(status="CANCELLED"), "balance"),
        "invoices_total": invoices.count(),
        "invoices_unpaid": invoices.filter(status__in=["ISSUED", "PARTIAL", "OVERDUE"]).count(),
        "overdue_count": qs_overdue_count(school),
        "payments_by_method": [
            {"method": row["method"], "total": money(row["total"] or 0), "count": row["count"]}
            for row in Payment.objects.filter(school=school, status="COMPLETED")
            .values("method")
            .annotate(total=Sum("amount"), count=Count("id"))
        ],
    }


def qs_overdue_count(school):
    today = timezone.localdate()
    return Invoice.objects.filter(
        school=school, balance__gt=0, due_date__lt=today
    ).exclude(status="CANCELLED").count()


def _library_summary(school):
    borrowings = Borrowing.objects.filter(school=school)
    overdue = borrowings.filter(
        status__in=["BORROWED", "OVERDUE"], due_date__lt=timezone.localdate()
    )
    outstanding_fines = borrowings.filter(fine_paid=False).aggregate(t=Sum("fine_amount"))["t"] or 0
    return {
        "books": Book.objects.filter(school=school).count(),
        "copies": BookCopy.objects.filter(book__school=school).count(),
        "borrowed": borrowings.filter(status__in=["BORROWED", "OVERDUE"], returned_at__isnull=True).count(),
        "overdue": overdue.count(),
        "outstanding_fines": money(outstanding_fines),
    }


def _transport_summary(school):
    return {
        "vehicles": Vehicle.objects.filter(school=school).count(),
        "active_vehicles": Vehicle.objects.filter(school=school, status="ACTIVE").count(),
        "routes": TransportRoute.objects.filter(school=school).count(),
        "students_assigned": StudentTransportAssignment.objects.filter(
            school=school, is_active=True
        ).count(),
    }


def _hr_summary(school):
    staff = StaffProfile.objects.filter(school=school)
    today = timezone.localdate()
    on_leave_today = StaffAttendance.objects.filter(
        school=school, date=today, status="LEAVE"
    ).count()
    return {
        "total": staff.count(),
        "active": staff.filter(status="ACTIVE").count(),
        "by_status": dict(
            (row["status"], row["c"]) for row in staff.values("status").annotate(c=Count("id"))
        ),
        "on_leave_today": on_leave_today,
        "pending_leave_requests": LeaveRequest.objects.filter(school=school, status="PENDING").count(),
    }


# ------------------------------------------------------------------- dashboard
def dashboard_overview(school, user=None):
    """Return the aggregate payload that powers the role aware dashboard.

    Sections the caller is not entitled to see are omitted entirely rather
    than returned empty, so a low privileged role cannot infer finance or HR
    figures from the dashboard response.
    """
    if school is None:
        return {
            "school": None,
            "generated_at": timezone.now().isoformat(),
            "message": "No school selected. Super administrators must pass ?school=<id>.",
        }

    roles = getattr(user, "user_type", None)
    is_super = bool(user and (user.is_superuser or roles == "SUPERADMIN"))
    can_finance = is_super or roles in FINANCE_ROLES
    can_hr = is_super or roles in HR_ROLES

    today = timezone.localdate()
    upcoming = list(
        SchoolEvent.objects.filter(school=school, start__date__gte=today)
        .order_by("start")
        .values("id", "title", "event_type", "start", "location")[:5]
    )
    for event in upcoming:
        event["start"] = event["start"].isoformat()
    holidays = list(
        Holiday.objects.filter(school=school, date__gte=today)
        .order_by("date")
        .values("id", "name", "date")[:5]
    )

    current_session = (
        AcademicSession.objects.filter(school=school, is_current=True).first()
        or AcademicSession.objects.filter(school=school).order_by("-start_date").first()
    )

    payload = {
        "school": {
            "id": str(school.pk),
            "name": school.name,
            "code": school.code,
            "currency": school.currency,
        },
        "generated_at": timezone.now().isoformat(),
        "current_session": (
            {"id": str(current_session.pk), "name": current_session.name}
            if current_session
            else None
        ),
        "students": _student_summary(school),
        "academics": {
            "grade_levels": GradeLevel.objects.filter(school=school).count(),
            "sections": Section.objects.filter(school=school).count(),
            "subjects": Subject.objects.filter(school=school).count(),
            "class_subjects": ClassSubject.objects.filter(school=school).count(),
        },
        "attendance": _attendance_summary(school, today),
        "admissions": _admission_summary(school),
        "examinations": _exam_summary(school),
        "library": _library_summary(school),
        "transport": _transport_summary(school),
        "upcoming_events": upcoming,
        "upcoming_holidays": holidays,
    }

    if can_finance:
        payload["finance"] = _finance_summary(school)
    if can_hr:
        payload["hr"] = _hr_summary(school)

    if user is not None and getattr(user, "is_authenticated", False):
        from communications.models import Notification

        payload["notifications"] = {
            "unread": Notification.objects.filter(user=user, is_read=False).count()
        }
    return payload


# ---------------------------------------------------------------------- trends
def attendance_trend(school, start=None, end=None, section=None):
    end = end or timezone.localdate()
    start = start or (end - timedelta(days=29))
    qs = StudentAttendance.objects.filter(school=school, date__gte=start, date__lte=end)
    if section:
        qs = qs.filter(section_id=section)
    rows = (
        qs.values("date")
        .annotate(
            present=Count("id", filter=Q(status="PRESENT")),
            absent=Count("id", filter=Q(status="ABSENT")),
            late=Count("id", filter=Q(status="LATE")),
            excused=Count("id", filter=Q(status="EXCUSED")),
            total=Count("id"),
        )
        .order_by("date")
    )
    series = []
    for row in rows:
        total = row["total"] or 0
        attended = row["present"] + row["late"]
        series.append(
            {
                "date": row["date"].isoformat(),
                "present": row["present"],
                "absent": row["absent"],
                "late": row["late"],
                "excused": row["excused"],
                "total": total,
                "rate": round(attended / total * 100, 2) if total else 0.0,
            }
        )
    return {"start": start.isoformat(), "end": end.isoformat(), "series": series}


def enrollment_by_grade(school, session=None):
    qs = StudentEnrollment.objects.filter(school=school)
    if session:
        qs = qs.filter(session_id=session)
    rows = (
        qs.values("grade_level__name", "grade_level__level_order")
        .annotate(
            total=Count("id"),
            male=Count("id", filter=Q(student__gender="M")),
            female=Count("id", filter=Q(student__gender="F")),
        )
        .order_by("grade_level__level_order")
    )
    return [
        {
            "grade": row["grade_level__name"] or "Unassigned",
            "total": row["total"],
            "male": row["male"],
            "female": row["female"],
        }
        for row in rows
    ]


def finance_collection_trend(school, start=None, end=None):
    end = end or timezone.localdate()
    start = start or (end - timedelta(days=29))
    rows = (
        Payment.objects.filter(
            school=school, status="COMPLETED", created_at__date__gte=start, created_at__date__lte=end
        )
        .values("created_at__date")
        .annotate(collected=Sum("amount"), count=Count("id"))
        .order_by("created_at__date")
    )
    return [
        {
            "date": row["created_at__date"].isoformat(),
            "collected": money(row["collected"] or 0),
            "count": row["count"],
        }
        for row in rows
    ]


def performance_summary(school, exam_id=None):
    exams = Exam.objects.filter(school=school)
    if exam_id:
        exams = exams.filter(pk=exam_id)
    exam = exams.order_by("-start_date").first()
    if exam is None:
        return {"exam": None, "grades": [], "subjects": [], "average": "0.00"}

    report_cards = ReportCard.objects.filter(exam=exam)
    grade_rows = report_cards.values("grade").annotate(c=Count("id")).order_by("-grade")
    subject_rows = (
        report_cards.values("student__enrollments__section__name")
        .annotate(average=Sum("average"), count=Count("id"))
        .order_by("student__enrollments__section__name")
    )
    aggregate = report_cards.aggregate(a=Sum("average"))["a"] or 0
    return {
        "exam": {
            "id": str(exam.pk),
            "name": exam.name,
            "exam_type": exam.exam_type,
            "is_published": exam.is_published,
        },
        "count": report_cards.count(),
        "grades": [
            {"grade": row["grade"] or "N/A", "count": row["c"]} for row in grade_rows
        ],
        "subjects": [
            {
                "section": row["student__enrollments__section__name"] or "Unassigned",
                "average": money(row["average"] or 0),
                "count": row["count"],
            }
            for row in subject_rows
        ],
        "average": money(aggregate / max(report_cards.count(), 1)),
    }
