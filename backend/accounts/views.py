from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from core.mixins import SchoolScopedQuerysetMixin
from core.permissions import IsSchoolAdmin, IsSuperAdmin

from .models import LoginAudit, User
from .permissions import CanManageUsers
from .serializers import (
    ChangePasswordSerializer, LoginAuditSerializer, LoginSerializer,
    ProfileSerializer, UserCreateSerializer, UserSerializer, tokens_for_user,
)


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class AuthViewSet(viewsets.ViewSet):
    """Authentication endpoints. Public where appropriate, protected otherwise."""

    def get_permissions(self):
        if self.action in ("login", "refresh"):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        return LoginSerializer

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        LoginAudit.objects.create(
            user=user,
            username=user.username,
            success=True,
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
        )
        payload = tokens_for_user(user)
        payload["user"] = UserSerializer(user).data
        return Response(payload)

    @action(detail=False, methods=["post"], url_path="refresh")
    def refresh(self, request):
        token = request.data.get("refresh")
        if not token:
            return Response({"detail": "Refresh token required."}, status=400)
        try:
            refresh = RefreshToken(token)
            access = str(refresh.access_token)
            if getattr(refresh, "access_token", None) is None:
                return Response({"detail": "Invalid token."}, status=400)
            return Response({"access": access})
        except TokenError as exc:
            return Response({"detail": str(exc)}, status=401)

    @action(detail=False, methods=["post"], url_path="logout")
    def logout(self, request):
        token = request.data.get("refresh")
        if token:
            try:
                RefreshToken(token).blacklist()
            except TokenError:
                pass
        return Response({"detail": "Logged out."}, status=status.HTTP_205_RESET_CONTENT)

    @action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request):
        if request.method == "PATCH":
            serializer = ProfileSerializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated."})


class UserViewSet(SchoolScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = User.objects.select_related("school")
    permission_classes = [CanManageUsers]
    search_fields = ["username", "first_name", "last_name", "email"]
    filterset_fields = ["user_type", "is_active"]
    ordering_fields = ["first_name", "last_name", "created_at"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return UserCreateSerializer
        return UserSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not (user.is_superuser or user.user_type == "SUPERADMIN"):
            qs = qs.exclude(user_type="SUPERADMIN")
        return qs

    @action(detail=True, methods=["post"], permission_classes=[IsSchoolAdmin])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response({"detail": "You cannot deactivate yourself."}, status=400)
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response({"detail": "Account deactivated."})

    @action(detail=True, methods=["post"], permission_classes=[IsSchoolAdmin])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response({"detail": "Account activated."})

    @action(detail=True, methods=["post"], permission_classes=[IsSchoolAdmin])
    def set_password(self, request, pk=None):
        user = self.get_object()
        password = request.data.get("password")
        if not password:
            return Response({"detail": "Password required."}, status=400)
        user.set_password(password)
        user.save(update_fields=["password"])
        return Response({"detail": "Password reset."})


class LoginAuditViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LoginAudit.objects.select_related("user")
    serializer_class = LoginAuditSerializer
    permission_classes = [IsSchoolAdmin]
    filterset_fields = ["success"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.user_type == "SUPERADMIN":
            return qs
        return qs.filter(user__school=user.school)
