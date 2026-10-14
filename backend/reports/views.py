"""Role aware reporting and analytics endpoints.

All responses are JSON except ``GET /api/reports/export/`` which streams a
CSV. Every queryset is scoped to the caller's school via
``reports.services.resolve_school``; super administrators may target a school
with ``?school=<id>``.
"""
import csv

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.services import money

from . import services
from .permissions import (
    CanExportDataset, CanViewAcademicReports, CanViewFinanceReports,
    CanViewHRReports, CanViewLibraryReports, CanViewReports,
    CanViewTransportReports,
)


class BaseReportView(APIView):
    permission_classes = [CanViewReports]

    def get_school(self, request):
        school = services.resolve_school(request)
        if school is None:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {"school": "No school in scope. Super administrators must pass ?school=<id>."}
            )
        return school


class DashboardView(BaseReportView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        school = services.resolve_school(request)
        payload = services.dashboard_overview(school, request.user)
        return Response(payload)


class AttendanceReportView(BaseReportView):
    def get(self, request):
        school = self.get_school(request)
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        section = request.query_params.get("section")
        return Response(
            {
                "today": services._attendance_summary(school),
                "trend": services.attendance_trend(
                    school,
                    start=_parse_date(start),
                    end=_parse_date(end),
                    section=section,
                ),
            }
        )


class EnrollmentReportView(BaseReportView):
    permission_classes = [CanViewAcademicReports]

    def get(self, request):
        school = self.get_school(request)
        session_id = request.query_params.get("session")
        return Response(
            {
                "students": services._student_summary(school),
                "by_grade": services.enrollment_by_grade(school, session_id),
            }
        )


class FinanceReportView(BaseReportView):
    permission_classes = [CanViewFinanceReports]

    def get(self, request):
        school = self.get_school(request)
        start = _parse_date(request.query_params.get("start"))
        end = _parse_date(request.query_params.get("end"))
        return Response(
            {
                "summary": services._finance_summary(school),
                "trend": services.finance_collection_trend(school, start=start, end=end),
            }
        )


class HRReportView(BaseReportView):
    permission_classes = [CanViewHRReports]

    def get(self, request):
        school = self.get_school(request)
        return Response(services._hr_summary(school))


class AcademicReportView(BaseReportView):
    permission_classes = [CanViewAcademicReports]

    def get(self, request):
        school = self.get_school(request)
        exam_id = request.query_params.get("exam")
        return Response(services.performance_summary(school, exam_id))


class LibraryReportView(BaseReportView):
    permission_classes = [CanViewLibraryReports]

    def get(self, request):
        school = self.get_school(request)
        return Response(services._library_summary(school))


class TransportReportView(BaseReportView):
    permission_classes = [CanViewTransportReports]

    def get(self, request):
        school = self.get_school(request)
        return Response(services._transport_summary(school))


class ExportView(APIView):
    """Stream a flat CSV for one of the supported datasets."""

    permission_classes = [CanExportDataset]

    def get(self, request):
        from rest_framework.exceptions import ValidationError

        dataset = request.query_params.get("dataset", "")
        school = services.resolve_school(request)
        if school is None:
            raise ValidationError(
                {"school": "No school in scope. Super administrators must pass ?school=<id>."}
            )
        if not CanExportDataset.allowed(request.user, dataset):
            raise ValidationError({"dataset": "Unsupported dataset."})

        headers, rows = _dataset_rows(dataset, school)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{school.code}-{dataset}.csv"'
        writer = csv.writer(response)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        return response


# ------------------------------------------------------------------- helpers
def _parse_date(value):
    from django.utils.dateparse import parse_date

    return parse_date(value) if value else None


def _dataset_rows(dataset, school):
    """Return ``(headers, iterable_of_rows)`` for a CSV dataset."""
    if dataset == "students":
        from students.models import Student

        headers = ["admission_number", "first_name", "last_name", "gender", "status",
                   "grade_level", "section", "admission_date"]
        qs = Student.objects.filter(school=school).select_related(
            "current_grade_level", "section"
        )
        rows = (
            [
                s.admission_number, s.first_name, s.last_name, s.gender, s.status,
                s.current_grade_level.name if s.current_grade_level else "",
                s.section.name if s.section else "",
                s.admission_date or "",
            ]
            for s in qs
        )
        return headers, rows

    if dataset == "attendance":
        from attendance.models import StudentAttendance

        headers = ["date", "admission_number", "student", "status", "section", "remark"]
        qs = StudentAttendance.objects.filter(school=school).select_related(
            "student", "section"
        ).order_by("-date")
        rows = (
            [
                a.date, a.student.admission_number, a.student.full_name,
                a.status, a.section.name if a.section else "", a.remark,
            ]
            for a in qs
        )
        return headers, rows

    if dataset == "staff":
        from hr.models import StaffProfile

        headers = ["employee_id", "name", "email", "job_title", "employment_type", "status", "hire_date"]
        qs = StaffProfile.objects.filter(school=school).select_related("user")
        rows = (
            [
                p.employee_id, p.user.full_name, p.user.email, p.job_title,
                p.employment_type, p.status, p.hire_date,
            ]
            for p in qs
        )
        return headers, rows

    if dataset == "invoices":
        from finance.models import Invoice

        headers = ["number", "student", "status", "total_amount", "amount_paid", "balance", "due_date"]
        qs = Invoice.objects.filter(school=school).select_related("student")
        rows = (
            [
                i.number, i.student.full_name, i.status, str(money(i.total_amount)),
                str(money(i.amount_paid)), str(money(i.balance)), i.due_date,
            ]
            for i in qs
        )
        return headers, rows

    if dataset == "payments":
        from finance.models import Payment

        headers = ["reference", "invoice", "student", "amount", "method", "status", "paid_at"]
        qs = Payment.objects.filter(school=school).select_related("invoice__student")
        rows = (
            [
                p.reference, p.invoice.number, p.invoice.student.full_name,
                str(money(p.amount)), p.method, p.status, p.paid_at or "",
            ]
            for p in qs
        )
        return headers, rows

    if dataset == "admissions":
        from admissions.models import AdmissionApplication

        headers = ["application_number", "applicant", "gender", "grade_level", "status", "guardian_phone"]
        qs = AdmissionApplication.objects.filter(school=school).select_related("grade_level")
        rows = (
            [
                a.application_number, a.full_name, a.gender,
                a.grade_level.name, a.status, a.guardian_phone,
            ]
            for a in qs
        )
        return headers, rows

    if dataset == "library":
        from library.models import Borrowing

        headers = ["book", "copy", "borrower", "borrowed_at", "due_date", "returned_at", "status", "fine_amount"]
        qs = Borrowing.objects.filter(school=school).select_related(
            "copy__book", "borrower"
        )
        rows = (
            [
                b.copy.book.title, b.copy.copy_code, b.borrower.full_name,
                b.borrowed_at, b.due_date, b.returned_at or "", b.status,
                str(money(b.fine_amount)),
            ]
            for b in qs
        )
        return headers, rows

    from rest_framework.exceptions import ValidationError

    raise ValidationError({"dataset": "Unsupported dataset."})
