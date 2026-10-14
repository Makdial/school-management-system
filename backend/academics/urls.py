from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClassSubjectViewSet, StudentEnrollmentViewSet, SubjectViewSet

router = DefaultRouter()
router.register("subjects", SubjectViewSet, basename="subject")
router.register("class-subjects", ClassSubjectViewSet, basename="class-subject")
router.register("enrollments", StudentEnrollmentViewSet, basename="enrollment")

urlpatterns = [path("", include(router.urls))]
