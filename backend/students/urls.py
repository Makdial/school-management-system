from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    GuardianViewSet, StudentDocumentViewSet, StudentGuardianViewSet,
    StudentStatusHistoryViewSet, StudentViewSet,
)

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")
router.register("guardians", GuardianViewSet, basename="guardian")
router.register("student-guardians", StudentGuardianViewSet, basename="student-guardian")
router.register("student-documents", StudentDocumentViewSet, basename="student-document")
router.register("student-status-history", StudentStatusHistoryViewSet, basename="student-status-history")

urlpatterns = [path("", include(router.urls))]
