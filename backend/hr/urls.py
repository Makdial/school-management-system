from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ContractViewSet, LeaveRequestViewSet, LeaveTypeViewSet, StaffProfileViewSet

router = DefaultRouter()
router.register("staff", StaffProfileViewSet, basename="staff")
router.register("contracts", ContractViewSet, basename="contract")
router.register("leave-types", LeaveTypeViewSet, basename="leave-type")
router.register("leave-requests", LeaveRequestViewSet, basename="leave-request")

urlpatterns = [path("", include(router.urls))]
