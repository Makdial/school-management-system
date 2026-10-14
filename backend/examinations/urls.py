from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ExamSubjectViewSet, ExamViewSet, ReportCardViewSet, StudentMarkViewSet

router = DefaultRouter()
router.register("exams", ExamViewSet, basename="exam")
router.register("exam-subjects", ExamSubjectViewSet, basename="exam-subject")
router.register("marks", StudentMarkViewSet, basename="mark")
router.register("report-cards", ReportCardViewSet, basename="report-card")

urlpatterns = [path("", include(router.urls))]
