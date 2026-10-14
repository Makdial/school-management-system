from django.urls import path

from .views import (
    AcademicReportView, AttendanceReportView, DashboardView, EnrollmentReportView,
    ExportView, FinanceReportView, HRReportView, LibraryReportView,
    TransportReportView,
)

urlpatterns = [
    path("reports/dashboard/", DashboardView.as_view(), name="report-dashboard"),
    path("reports/attendance/", AttendanceReportView.as_view(), name="report-attendance"),
    path("reports/enrollment/", EnrollmentReportView.as_view(), name="report-enrollment"),
    path("reports/finance/", FinanceReportView.as_view(), name="report-finance"),
    path("reports/hr/", HRReportView.as_view(), name="report-hr"),
    path("reports/academic/", AcademicReportView.as_view(), name="report-academic"),
    path("reports/library/", LibraryReportView.as_view(), name="report-library"),
    path("reports/transport/", TransportReportView.as_view(), name="report-transport"),
    path("reports/export/", ExportView.as_view(), name="report-export"),
]
