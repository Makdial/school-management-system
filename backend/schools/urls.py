from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AcademicSessionViewSet, CampusViewSet, ClassroomViewSet, DepartmentViewSet,
    GradeLevelViewSet, GradingBandViewSet, GradingScaleViewSet, HolidayViewSet,
    SchoolEventViewSet, SchoolSettingViewSet, SchoolViewSet, SectionViewSet,
    TermViewSet,
)

router = DefaultRouter()
router.register("schools", SchoolViewSet, basename="school")
router.register("campuses", CampusViewSet, basename="campus")
router.register("sessions", AcademicSessionViewSet, basename="session")
router.register("terms", TermViewSet, basename="term")
router.register("departments", DepartmentViewSet, basename="department")
router.register("grade-levels", GradeLevelViewSet, basename="grade-level")
router.register("sections", SectionViewSet, basename="section")
router.register("classrooms", ClassroomViewSet, basename="classroom")
router.register("grading-scales", GradingScaleViewSet, basename="grading-scale")
router.register("grading-bands", GradingBandViewSet, basename="grading-band")
router.register("holidays", HolidayViewSet, basename="holiday")
router.register("events", SchoolEventViewSet, basename="event")
router.register("school-settings", SchoolSettingViewSet, basename="school-setting")

urlpatterns = [path("", include(router.urls))]
