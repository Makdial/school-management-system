from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    StudentTransportAssignmentViewSet, TransportRouteViewSet,
    TransportStopViewSet, VehicleMaintenanceViewSet, VehicleViewSet,
)

router = DefaultRouter()
router.register("vehicles", VehicleViewSet, basename="vehicle")
router.register("transport-routes", TransportRouteViewSet, basename="transport-route")
router.register("transport-stops", TransportStopViewSet, basename="transport-stop")
router.register("transport-assignments", StudentTransportAssignmentViewSet, basename="transport-assignment")
router.register("vehicle-maintenance", VehicleMaintenanceViewSet, basename="vehicle-maintenance")

urlpatterns = [path("", include(router.urls))]
