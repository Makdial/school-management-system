from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AuthViewSet, LoginAuditViewSet, UserViewSet

router = DefaultRouter()
router.register("auth", AuthViewSet, basename="auth")
router.register("users", UserViewSet, basename="user")
router.register("login-audits", LoginAuditViewSet, basename="login-audit")

urlpatterns = [path("", include(router.urls))]
