from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AdmissionApplicationViewSet, AdmissionDocumentViewSet

router = DefaultRouter()
router.register("admissions", AdmissionApplicationViewSet, basename="admission")
router.register("admission-documents", AdmissionDocumentViewSet, basename="admission-document")

urlpatterns = [path("", include(router.urls))]
