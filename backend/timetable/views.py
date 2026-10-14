from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsAnyRole, IsSchoolAdmin

from .models import Room, TimetableEntry, TimetablePeriod
from .serializers import RoomSerializer, TimetableEntrySerializer, TimetablePeriodSerializer
from .services import detect_conflicts


class RoomViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsSchoolAdmin]
    search_fields = ["name"]


class TimetablePeriodViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = TimetablePeriod.objects.all()
    serializer_class = TimetablePeriodSerializer
    permission_classes = [IsAnyRole]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsSchoolAdmin()]
        return super().get_permissions()


class TimetableEntryViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = TimetableEntry.objects.select_related("subject", "teacher", "room", "section", "period", "session")
    serializer_class = TimetableEntrySerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["session", "section", "teacher", "day_of_week", "room"]
    ordering_fields = ["day_of_week"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "publish"):
            return [IsSchoolAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "TEACHER":
            return qs.filter(teacher=user)
        if user.user_type == "STUDENT":
            return qs.filter(section__enrollments__student__user=user).distinct()
        if user.user_type == "PARENT":
            return qs.filter(
                section__enrollments__student__guardian_links__guardian__user=user
            ).distinct()
        return qs

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)

    @action(detail=False, methods=["post"], url_path="publish")
    def publish(self, request):
        session = request.data.get("session")
        section = request.data.get("section")
        qs = self.get_queryset()
        if session:
            qs = qs.filter(session_id=session)
        if section:
            qs = qs.filter(section_id=section)
        updated = qs.update(is_published=True)
        return Response({"published": updated})

    @action(detail=False, methods=["get"], url_path="conflicts")
    def conflicts(self, request):
        return Response({"conflicts": detect_conflicts(self.get_queryset())})
