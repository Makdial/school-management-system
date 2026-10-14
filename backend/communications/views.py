from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsAnyRole, IsSchoolAdmin

from .models import Announcement, Message, Notification
from .serializers import AnnouncementSerializer, MessageSerializer, NotificationSerializer
from .services import notify_users


class AnnouncementViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Announcement.objects.select_related("author", "grade_level")
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["audience", "is_published", "grade_level"]
    search_fields = ["title", "body"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsSchoolAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset().filter(is_published=True)
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(audience__in=["ALL", "STUDENTS"])
        if user.user_type == "PARENT":
            return qs.filter(audience__in=["ALL", "PARENTS"])
        if user.user_type == "TEACHER":
            return qs.filter(audience__in=["ALL", "STAFF", "TEACHERS"])
        return qs

    def perform_create(self, serializer):
        serializer.save(
            school_id=self.request.user.school_id,
            author=self.request.user,
            published_at=timezone.now(),
        )


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAnyRole]
    pagination_class = __import__("core.pagination", fromlist=["StandardPagination"]).StandardPagination

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at", "updated_at"])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({"detail": "All notifications marked as read."})

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"count": Notification.objects.filter(user=request.user, is_read=False).count()})


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAnyRole]
    pagination_class = __import__("core.pagination", fromlist=["StandardPagination"]).StandardPagination

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(sender=user) | Message.objects.filter(recipient=user)

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        message = self.get_object()
        if message.recipient_id != request.user.id:
            return Response({"detail": "Not permitted."}, status=403)
        message.is_read = True
        message.save(update_fields=["is_read", "updated_at"])
        return Response(self.get_serializer(message).data)
