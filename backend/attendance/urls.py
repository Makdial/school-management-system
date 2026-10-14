from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AttendanceCorrectionViewSet, StaffAttendanceViewSet, StudentAttendanceViewSet

router = DefaultRouter()
router.register("attendance", StudentAttendanceViewSet, basename="attendance")
router.register("staff-attendance", StaffAttendanceViewSet, basename="staff-attendance")
router.register("attendance-corrections", AttendanceCorrectionViewSet, basename="attendance-correction")

urlpatterns = [path("", include(router.urls))]
