"""Generator A: core, schools, accounts foundations."""
import os

ROOT = r"C:\Users\makhf\OneDrive\Desktop\School\backend"
FILES = {}

FILES["core/models.py"] = '''"""Shared abstract base models and helpers."""
import uuid

from django.db import models


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    """UUID primary key + audit timestamps."""

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class SchoolScopedModel(BaseModel):
    """Every business record belongs to exactly one school (tenant)."""

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
        db_index=True,
    )

    class Meta(BaseModel.Meta):
        abstract = True
'''

FILES["core/permissions.py"] = '''"""Role based access control primitives.

Permissions are enforced server side for every protected endpoint. Hiding a
button in the UI is never enough.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

SUPER_ADMIN = "SUPERADMIN"
SCHOOL_ADMIN = "SCHOOL_ADMIN"
PRINCIPAL = "PRINCIPAL"
TEACHER = "TEACHER"
STUDENT = "STUDENT"
PARENT = "PARENT"
ACCOUNTANT = "ACCOUNTANT"
LIBRARIAN = "LIBRARIAN"
TRANSPORT_MANAGER = "TRANSPORT_MANAGER"
HR_MANAGER = "HR_MANAGER"

ALL_ROLES = [
    SUPER_ADMIN, SCHOOL_ADMIN, PRINCIPAL, TEACHER, STUDENT,
    PARENT, ACCOUNTANT, LIBRARIAN, TRANSPORT_MANAGER, HR_MANAGER,
]

ADMIN_ROLES = [SUPER_ADMIN, SCHOOL_ADMIN]
ACADEMIC_ROLES = [SUPER_ADMIN, SCHOOL_ADMIN, PRINCIPAL, TEACHER]
FINANCE_ROLES = [SUPER_ADMIN, SCHOOL_ADMIN, ACCOUNTANT]
HR_ROLES = [SUPER_ADMIN, SCHOOL_ADMIN, HR_MANAGER]
LIBRARY_ROLES = [SUPER_ADMIN, SCHOOL_ADMIN, LIBRARIAN]
TRANSPORT_ROLES = [SUPER_ADMIN, SCHOOL_ADMIN, TRANSPORT_MANAGER]


class HasRole(BasePermission):
    """Allow access when the authenticated user has one of ``allowed_roles``."""

    allowed_roles = tuple(ADMIN_ROLES)
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.user_type == SUPER_ADMIN:
            return True
        return user.user_type in self.allowed_roles


def role_permission(*roles):
    return type("HasRoles", (HasRole,), {"allowed_roles": tuple(roles)})


IsSuperAdmin = role_permission(SUPER_ADMIN)
IsSchoolAdmin = role_permission(SUPER_ADMIN, SCHOOL_ADMIN)
IsAcademicStaff = role_permission(*ACADEMIC_ROLES)
IsFinance = role_permission(*FINANCE_ROLES)
IsHR = role_permission(*HR_ROLES)
IsLibrarian = role_permission(*LIBRARY_ROLES)
IsTransportManager = role_permission(*TRANSPORT_ROLES)
IsAnyRole = role_permission(*ALL_ROLES)


class IsSchoolMember(BasePermission):
    """Requires an authenticated user attached to a school."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and (user.is_superuser or user.school_id))


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class IsOwnerOrStaff(BasePermission):
    """Object level guard used for student/parent private data."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.user_type in ADMIN_ROLES or user.is_superuser:
            return True
        owner = getattr(obj, "user_id", None)
        if owner and owner == user.id:
            return True
        student_user = getattr(getattr(obj, "student", None), "user_id", None)
        if student_user and student_user == user.id:
            return True
        school_id = getattr(obj, "school_id", None)
        if school_id:
            return school_id == user.school_id
        return False
'''

FILES["core/pagination.py"] = '''from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200
'''

FILES["core/mixins.py"] = '''from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .pagination import StandardPagination
from .permissions import IsSchoolMember


class SchoolScopedQuerysetMixin:
    """Restrict a queryset to the caller's school.

    Super administrators may pass ``?school=<id>`` to inspect a single
    institution; otherwise they see every institution. Regular users are
    always hard scoped to their own school which prevents cross-tenant
    leakage through URL manipulation.
    """

    school_lookup_field = "school_id"

    def get_school_id(self):
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return None
        if user.is_superuser or user.user_type == "SUPERADMIN":
            return self.request.query_params.get("school")
        return user.school_id

    def get_queryset(self):
        qs = super().get_queryset()
        school_id = self.get_school_id()
        user = self.request.user
        is_super = user.is_superuser or user.user_type == "SUPERADMIN"
        if school_id:
            qs = qs.filter(**{self.school_lookup_field: school_id})
        elif not is_super:
            return qs.none()
        return qs

    def perform_create(self, serializer):
        if "school" in serializer.validated_data:
            return super().perform_create(serializer)
        school_id = self.get_school_id()
        user = self.request.user
        if not school_id and not (user.is_superuser or user.user_type == "SUPERADMIN"):
            school_id = user.school_id
        return super().perform_create(serializer.save(school_id=school_id))


class SchoolScopedViewSetMixin(SchoolScopedQuerysetMixin):
    permission_classes = [IsSchoolMember]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
'''

FILES["core/services.py"] = '''"""Small cross cutting helpers used by several domain services."""
from datetime import date

from django.utils import timezone


def today():
    return timezone.localdate()


def money(value):
    """Quantise a value to two decimal places without floating point drift."""
    from decimal import Decimal, ROUND_HALF_UP

    return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def generate_sequence_number(prefix, model, field, school=None, width=5):
    """Create a human friendly sequential document number.

    Wrapped by the caller in a transaction so concurrent inserts do not
    collide on the unique constraint.
    """
    year = date.today().year
    base = f"{prefix}-{year}-"
    qs = model.objects.filter(**{f"{field}__startswith": base})
    if school is not None:
        qs = qs.filter(school=school)
    last = qs.order_by(f"-{field}").values_list(field, flat=True).first()
    tail = 1
    if last:
        try:
            tail = int(str(last).rsplit("-", 1)[-1]) + 1
        except (ValueError, IndexError):
            tail = 1
    return f"{base}{tail:0{width}d}"


def percent(part, whole):
    if not whole:
        return 0.0
    return round((float(part) / float(whole)) * 100, 2)
'''

FILES["core/serializers.py"] = '''from rest_framework import serializers


class MessageSerializer(serializers.Serializer):
    detail = __import__("rest_framework").serializers.CharField()
'''

FILES["core/views.py"] = '''from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


def health(request):
    """Liveness/readiness probe used by docker and the frontend."""
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:  # pragma: no cover - defensive
        db_ok = False
    from django.http import JsonResponse

    return JsonResponse({"status": "ok" if db_ok else "degraded", "database": db_ok})
'''

FILES["core/urls.py"] = '''from django.urls import path

from .views import health

urlpatterns = [
    path("health/", health, name="health"),
]
'''

FILES["core/apps.py"] = '''from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
'''

FILES["core/tests/__init__.py"] = ""
FILES["core/tests/test_health.py"] = '''import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_endpoint(client):
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
'''

# ------------------------------------------------------------------ schools
FILES["schools/models.py"] = '''"""School configuration / tenant models."""
from django.db import models

from core.models import BaseModel


class School(BaseModel):
    """A school institution. Root of the tenancy tree."""

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=32, unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    logo = models.ImageField(upload_to="schools/logos/", blank=True, null=True)
    motto = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    currency = models.CharField(max_length=8, default="USD")
    timezone = models.CharField(max_length=64, default="UTC")
    date_format = models.CharField(max_length=20, default="YYYY-MM-DD")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Campus(BaseModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="campuses")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_main = models.BooleanField(default=False)

    class Meta:
        unique_together = [("school", "code")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.school.code}/{self.name}"


class AcademicSession(BaseModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="sessions")
    name = models.CharField(max_length=64)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        unique_together = [("school", "name")]
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_current:
            AcademicSession.objects.filter(school=self.school, is_current=True).exclude(
                pk=self.pk
            ).update(is_current=False)


class Term(BaseModel):
    TERM_CHOICES = [("FIRST", "First Term"), ("SECOND", "Second Term"), ("THIRD", "Third Term")]

    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name="terms")
    name = models.CharField(max_length=32, choices=TERM_CHOICES, default="FIRST")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        unique_together = [("session", "name")]
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.session.name} {self.get_name_display()}"


class Department(BaseModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="departments")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [("school", "code")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class GradeLevel(BaseModel):
    """A class / grade level e.g. Grade 1 or Form 4."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="grade_levels")
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=32)
    level_order = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    next_level = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="previous_levels"
    )

    class Meta:
        unique_together = [("school", "code")]
        ordering = ["level_order", "name"]

    def __str__(self):
        return self.name


class Section(BaseModel):
    """A section / stream inside a grade level."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="sections")
    grade_level = models.ForeignKey(GradeLevel, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=60)
    capacity = models.PositiveIntegerField(default=40)
    class_teacher = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sections_led",
    )

    class Meta:
        unique_together = [("school", "grade_level", "name")]
        ordering = ["grade_level__level_order", "name"]

    def __str__(self):
        return f"{self.grade_level.name} {self.name}"


class Classroom(BaseModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="classrooms")
    name = models.CharField(max_length=80)
    capacity = models.PositiveIntegerField(default=40)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class GradingScale(BaseModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="grading_scales")
    name = models.CharField(max_length=80)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class GradingBand(BaseModel):
    scale = models.ForeignKey(GradingScale, on_delete=models.CASCADE, related_name="bands")
    grade = models.CharField(max_length=8)
    min_score = models.DecimalField(max_digits=6, decimal_places=2)
    max_score = models.DecimalField(max_digits=6, decimal_places=2)
    remark = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["-min_score"]
        unique_together = [("scale", "grade")]

    def __str__(self):
        return f"{self.grade} ({self.min_score}-{self.max_score})"

    @classmethod
    def grade_for(cls, scale, score):
        from decimal import Decimal

        score = Decimal(str(score))
        band = scale.bands.filter(min_score__lte=score, max_score__gte=score).first()
        return band.grade if band else None


class Holiday(BaseModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="holidays")
    name = models.CharField(max_length=120)
    date = models.DateField()
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["date"]
        unique_together = [("school", "date", "name")]

    def __str__(self):
        return f"{self.name} ({self.date})"


class SchoolEvent(BaseModel):
    EVENT_TYPES = [
        ("GENERAL", "General"),
        ("EXAM", "Examination"),
        ("MEETING", "Parent Meeting"),
        ("ACTIVITY", "School Activity"),
        ("HOLIDAY", "Holiday"),
    ]
    AUDIENCE = [
        ("ALL", "Everyone"),
        ("STAFF", "Staff"),
        ("STUDENTS", "Students"),
        ("PARENTS", "Parents"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=16, choices=EVENT_TYPES, default="GENERAL")
    audience = models.CharField(max_length=16, choices=AUDIENCE, default="ALL")
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=180, blank=True)

    class Meta:
        ordering = ["start"]

    def __str__(self):
        return self.title


class SchoolSetting(BaseModel):
    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name="settings")
    data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Settings for {self.school.code}"
'''

FILES["schools/serializers.py"] = '''from rest_framework import serializers

from .models import (
    AcademicSession, Campus, Classroom, Department, GradeLevel, GradingBand,
    GradingScale, Holiday, School, SchoolEvent, SchoolSetting, Section, Term,
)


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class CampusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campus
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class AcademicSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicSession
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class TermSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source="session.name", read_only=True)

    class Meta:
        model = Term
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class GradeLevelSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = GradeLevel
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class SectionSerializer(serializers.ModelSerializer):
    grade_level_name = serializers.CharField(source="grade_level.name", read_only=True)
    class_teacher_name = serializers.CharField(source="class_teacher.get_full_name", read_only=True)
    enrolled = serializers.IntegerField(read_only=True)

    class Meta:
        model = Section
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ClassroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class GradingBandSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingBand
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class GradingScaleSerializer(serializers.ModelSerializer):
    bands = GradingBandSerializer(many=True, read_only=True)

    class Meta:
        model = GradingScale
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class SchoolEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolEvent
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class SchoolSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolSetting
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
'''

FILES["schools/views.py"] = '''from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedQuerysetMixin
from core.permissions import IsAnyRole, IsSchoolAdmin, IsSuperAdmin

from .models import (
    AcademicSession, Campus, Classroom, Department, GradeLevel, GradingBand,
    GradingScale, Holiday, School, SchoolEvent, SchoolSetting, Section, Term,
)
from .serializers import (
    AcademicSessionSerializer, CampusSerializer, ClassroomSerializer,
    DepartmentSerializer, GradeLevelSerializer, GradingBandSerializer,
    GradingScaleSerializer, HolidaySerializer, SchoolEventSerializer,
    SchoolSerializer, SchoolSettingSerializer, SectionSerializer, TermSerializer,
)


class SchoolViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolSerializer
    permission_classes = [IsSuperAdmin]
    queryset = School.objects.all()
    search_fields = ["name", "code", "email"]
    ordering_fields = ["name", "created_at"]

    @action(detail=False, methods=["get"], permission_classes=[IsAnyRole])
    def current(self, request):
        school = request.user.school
        if school is None:
            return Response({"detail": "No school linked to this account."}, status=404)
        return Response(self.get_serializer(school).data)


class SchoolScopedModelViewSet(SchoolScopedQuerysetMixin, viewsets.ModelViewSet):
    permission_classes = [IsSchoolAdmin]


class CampusViewSet(SchoolScopedModelViewSet):
    queryset = Campus.objects.select_related("school")
    serializer_class = CampusSerializer
    search_fields = ["name", "code"]


class AcademicSessionViewSet(SchoolScopedModelViewSet):
    queryset = AcademicSession.objects.all()
    serializer_class = AcademicSessionSerializer
    permission_classes = [IsAnyRole]
    search_fields = ["name"]
    ordering_fields = ["start_date", "name"]


class TermViewSet(SchoolScopedModelViewSet):
    queryset = Term.objects.select_related("session")
    serializer_class = TermSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["session"]


class DepartmentViewSet(SchoolScopedModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    search_fields = ["name", "code"]


class GradeLevelViewSet(SchoolScopedModelViewSet):
    queryset = GradeLevel.objects.all()
    serializer_class = GradeLevelSerializer
    search_fields = ["name", "code"]


class SectionViewSet(SchoolScopedModelViewSet):
    queryset = Section.objects.select_related("grade_level", "class_teacher")
    serializer_class = SectionSerializer
    filterset_fields = ["grade_level"]
    search_fields = ["name"]


class ClassroomViewSet(SchoolScopedModelViewSet):
    queryset = Classroom.objects.select_related("section")
    serializer_class = ClassroomSerializer
    filterset_fields = ["section"]


class GradingScaleViewSet(SchoolScopedModelViewSet):
    queryset = GradingScale.objects.prefetch_related("bands")
    serializer_class = GradingScaleSerializer


class GradingBandViewSet(SchoolScopedModelViewSet):
    queryset = GradingBand.objects.select_related("scale")
    serializer_class = GradingBandSerializer
    filterset_fields = ["scale"]

    def get_queryset(self):
        return super().get_queryset().filter(scale__school_id=self.get_school_id())


class HolidayViewSet(SchoolScopedModelViewSet):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [IsAnyRole]


class SchoolEventViewSet(SchoolScopedModelViewSet):
    queryset = SchoolEvent.objects.all()
    serializer_class = SchoolEventSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["event_type", "audience"]
    search_fields = ["title", "description"]


class SchoolSettingViewSet(SchoolScopedModelViewSet):
    queryset = SchoolSetting.objects.all()
    serializer_class = SchoolSettingSerializer
'''

FILES["schools/urls.py"] = '''from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AcademicSessionViewSet, CampusViewSet, ClassroomViewSet, DepartmentViewSet,
    GradeLevelViewSet, GradingBandViewSet, GradingScaleViewSet, HolidayViewSet,
    SchoolEventViewSet, SchoolSettingViewSet, SchoolViewSet, SectionViewSet,
    TermViewSet,
)

router = DefaultRouter()
router.register("schools", SchoolViewSet, basename="school")
router.register("campuses", CampusViewSet, basename="campus")
router.register("sessions", AcademicSessionViewSet, basename="session")
router.register("terms", TermViewSet, basename="term")
router.register("departments", DepartmentViewSet, basename="department")
router.register("grade-levels", GradeLevelViewSet, basename="grade-level")
router.register("sections", SectionViewSet, basename="section")
router.register("classrooms", ClassroomViewSet, basename="classroom")
router.register("grading-scales", GradingScaleViewSet, basename="grading-scale")
router.register("grading-bands", GradingBandViewSet, basename="grading-band")
router.register("holidays", HolidayViewSet, basename="holiday")
router.register("events", SchoolEventViewSet, basename="event")
router.register("school-settings", SchoolSettingViewSet, basename="school-setting")

urlpatterns = [path("", include(router.urls))]
'''

FILES["schools/apps.py"] = '''from django.apps import AppConfig


class SchoolsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "schools"
'''

FILES["schools/tests/__init__.py"] = ""
FILES["schools/tests/test_isolation.py"] = '''import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from schools.models import GradeLevel, School


@pytest.fixture
def two_schools(db):
    a = School.objects.create(name="Alpha", code="ALPHA")
    b = School.objects.create(name="Beta", code="BETA")
    return a, b


@pytest.mark.django_db
def test_school_admin_cannot_see_other_school(school_factory, user_factory, api_client, two_schools):
    a, b = two_schools
    GradeLevel.objects.create(school=a, name="G1", code="A1", level_order=1)
    GradeLevel.objects.create(school=b, name="G1", code="B1", level_order=1)
    admin = user_factory(user_type="SCHOOL_ADMIN", school=a)
    client = api_client()
    client.force_authenticate(admin)
    response = client.get("/api/grade-levels/")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["code"] == "A1"
'''

FILES["schools/apps_placeholder.py"] = ""

def write_all():
    for rel, content in FILES.items():
        path = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        print("wrote", rel)


if __name__ == "__main__":
    write_all()
