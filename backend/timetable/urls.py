from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RoomViewSet, TimetableEntryViewSet, TimetablePeriodViewSet

router = DefaultRouter()
router.register("rooms", RoomViewSet, basename="room")
router.register("timetable-periods", TimetablePeriodViewSet, basename="timetable-period")
router.register("timetable", TimetableEntryViewSet, basename="timetable-entry")

urlpatterns = [path("", include(router.urls))]
