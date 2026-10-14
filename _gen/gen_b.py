"""Generator B: accounts, academics, students, admissions, attendance, timetable."""
import os

ROOT = r"C:\Users\makhf\OneDrive\Desktop\School\backend"
FILES = {}

# ------------------------------------------------------------------ accounts
FILES["accounts/models.py"] = '''import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ("SUPERADMIN", "Super Administrator"),
        ("SCHOOL_ADMIN", "School Administrator"),
        ("PRINCIPAL", "Principal / Headteacher"),
        ("TEACHER", "Teacher"),
        ("STUDENT", "Student"),
        ("PARENT", "Parent / Guardian"),
        ("ACCOUNTANT", "Accountant"),
        ("LIBRARIAN", "Librarian"),
        ("TRANSPORT_MANAGER", "Transport Manager"),
        ("HR_MANAGER", "Human Resources Manager"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type = models.CharField(max_length=30, choices=USER_TYPE_CHOICES, default="STUDENT", db_index=True)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
    )
    phone_number = models.CharField(max_length=32, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)

    class Meta:
        db_table = "auth_user"
        ordering = ["first_name", "last_name", "username"]

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def full_name(self):
        return self.get_full_name() or self.username


class LoginAudit(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="login_audits")
    username = models.CharField(max_length=150, blank=True)
    success = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.username} {'ok' if self.success else 'failed'} @ {self.created_at:%Y-%m-%d %H:%M}"
'''

FILES["accounts/serializers.py"] = '''from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import LoginAudit, User


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    school_name = serializers.CharField(source="school.name", read_only=True, default=None)
    created_at = serializers.DateTimeField(source="date_joined", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "full_name",
            "user_type", "school", "school_name", "phone_number", "date_of_birth",
            "address", "profile_picture", "is_active", "last_login", "created_at",
        ]
        read_only_fields = ["id", "last_login", "full_name", "school_name"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "user_type",
            "school", "phone_number", "date_of_birth", "address", "password",
            "is_active",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        user_type = attrs.get("user_type")
        school = attrs.get("school")
        if user and not (user.is_superuser or user.user_type == "SUPERADMIN"):
            attrs["school"] = user.school
            if user.user_type not in ("SCHOOL_ADMIN",):
                raise serializers.ValidationError("Only administrators may manage users.")
            if user_type in ("SUPERADMIN",):
                raise serializers.ValidationError("Cannot create super administrators.")
        if user_type != "SUPERADMIN" and school is None and not attrs.get("school"):
            raise serializers.ValidationError({"school": "A school is required for this role."})
        return attrs

    def validate_username(self, value):
        qs = User.objects.filter(username__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None) or User.objects.make_random_password()
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class ProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "full_name",
            "phone_number", "date_of_birth", "address", "profile_picture", "user_type",
            "school",
        ]
        read_only_fields = ["id", "username", "user_type", "school"]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context.get("request")
        user = authenticate(
            request=request,
            username=attrs["username"],
            password=attrs["password"],
        )
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")
        attrs["user"] = user
        return attrs


class LoginAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginAudit
        fields = "__all__"


def tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh["user_type"] = user.user_type
    refresh["school"] = str(user.school_id) if user.school_id else None
    return {"refresh": str(refresh), "access": str(refresh.access_token)}
'''

FILES["accounts/permissions.py"] = '''from core.permissions import role_permission

CanManageUsers = role_permission("SUPERADMIN", "SCHOOL_ADMIN")
'''

FILES["accounts/views.py"] = '''from django.db import transaction
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
'''

FILES["accounts/urls.py"] = '''from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AuthViewSet, LoginAuditViewSet, UserViewSet

router = DefaultRouter()
router.register("auth", AuthViewSet, basename="auth")
router.register("users", UserViewSet, basename="user")
router.register("login-audits", LoginAuditViewSet, basename="login-audit")

urlpatterns = [path("", include(router.urls))]
'''

FILES["accounts/apps.py"] = '''from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
'''

FILES["accounts/admin.py"] = '''from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import LoginAudit, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "first_name", "last_name", "user_type", "school", "is_active")
    list_filter = ("user_type", "is_active", "school")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("School ERP", {"fields": ("user_type", "school", "phone_number", "date_of_birth", "address", "profile_picture")}),
    )


@admin.register(LoginAudit)
class LoginAuditAdmin(admin.ModelAdmin):
    list_display = ("username", "success", "ip_address", "created_at")
'''

# ------------------------------------------------------------------ academics
FILES["academics/models.py"] = '''from django.core.exceptions import ValidationError
from django.db import models

from core.models import BaseModel, SchoolScopedModel


class Subject(SchoolScopedModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32)
    department = models.ForeignKey(
        "schools.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="subjects"
    )
    is_elective = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [("school", "code")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class ClassSubject(SchoolScopedModel):
    """A subject taught to a grade level within a session."""

    session = models.ForeignKey("schools.AcademicSession", on_delete=models.CASCADE, related_name="class_subjects")
    grade_level = models.ForeignKey("schools.GradeLevel", on_delete=models.CASCADE, related_name="class_subjects")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="class_assignments")
    teacher = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="teaching_assignments"
    )
    periods_per_week = models.PositiveIntegerField(default=1)
    is_compulsory = models.BooleanField(default=True)

    class Meta:
        unique_together = [("school", "session", "grade_level", "subject")]
        ordering = ["grade_level__level_order", "subject__name"]

    def __str__(self):
        return f"{self.grade_level.name} - {self.subject.name}"

    def clean(self):
        if self.teacher and self.teacher.user_type not in ("TEACHER", "PRINCIPAL", "SCHOOL_ADMIN", "SUPERADMIN"):
            raise ValidationError({"teacher": "Selected user cannot be assigned as a teacher."})


class StudentEnrollment(SchoolScopedModel):
    STATUS = [
        ("ACTIVE", "Active"),
        ("PROMOTED", "Promoted"),
        ("TRANSFERRED", "Transferred"),
        ("GRADUATED", "Graduated"),
        ("WITHDRAWN", "Withdrawn"),
    ]

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="enrollments")
    session = models.ForeignKey("schools.AcademicSession", on_delete=models.CASCADE, related_name="enrollments")
    grade_level = models.ForeignKey("schools.GradeLevel", on_delete=models.PROTECT, related_name="enrollments")
    section = models.ForeignKey("schools.Section", null=True, blank=True, on_delete=models.SET_NULL, related_name="enrollments")
    roll_number = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="ACTIVE")
    enrolled_on = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = [("student", "session")]
        ordering = ["-session__start_date", "student__last_name"]

    def __str__(self):
        return f"{self.student} @ {self.session}"

    def clean(self):
        if self.section and self.section.grade_level_id != self.grade_level_id:
            raise ValidationError({"section": "Section must belong to the selected grade level."})
'''

FILES["academics/serializers.py"] = '''from rest_framework import serializers

from .models import ClassSubject, StudentEnrollment, Subject


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class ClassSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    grade_level_name = serializers.CharField(source="grade_level.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True, default=None)

    class Meta:
        model = ClassSubject
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]

    def validate(self, attrs):
        session = attrs.get("session") or getattr(self.instance, "session", None)
        grade = attrs.get("grade_level") or getattr(self.instance, "grade_level", None)
        subject = attrs.get("subject") or getattr(self.instance, "subject", None)
        school = self.context["request"].user.school
        if session and grade and grade.school_id != session.school_id:
            raise serializers.ValidationError("Grade level and session belong to different schools.")
        if subject and school and subject.school_id != school.id:
            raise serializers.ValidationError("Subject belongs to a different school.")
        return attrs


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    grade_level_name = serializers.CharField(source="grade_level.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)

    class Meta:
        model = StudentEnrollment
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]
'''

FILES["academics/views.py"] = '''from rest_framework import viewsets

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsAcademicStaff, IsAnyRole, IsSchoolAdmin

from .models import ClassSubject, StudentEnrollment, Subject
from .serializers import ClassSubjectSerializer, StudentEnrollmentSerializer, SubjectSerializer


class SubjectViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Subject.objects.select_related("department")
    serializer_class = SubjectSerializer
    permission_classes = [IsAnyRole]
    search_fields = ["name", "code"]
    filterset_fields = ["department", "is_elective"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsSchoolAdmin()]
        return super().get_permissions()


class ClassSubjectViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = ClassSubject.objects.select_related("subject", "grade_level", "teacher", "session")
    serializer_class = ClassSubjectSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["session", "grade_level", "subject", "teacher"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsSchoolAdmin()]
        return super().get_permissions()


class StudentEnrollmentViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentEnrollment.objects.select_related("student", "session", "grade_level", "section")
    serializer_class = StudentEnrollmentSerializer
    permission_classes = [IsAcademicStaff]
    filterset_fields = ["session", "grade_level", "section", "status"]
    search_fields = ["student__first_name", "student__last_name", "student__admission_number"]
'''

FILES["academics/urls.py"] = '''from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClassSubjectViewSet, StudentEnrollmentViewSet, SubjectViewSet

router = DefaultRouter()
router.register("subjects", SubjectViewSet, basename="subject")
router.register("class-subjects", ClassSubjectViewSet, basename="class-subject")
router.register("enrollments", StudentEnrollmentViewSet, basename="enrollment")

urlpatterns = [path("", include(router.urls))]
'''

FILES["academics/apps.py"] = '''from django.apps import AppConfig


class AcademicsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "academics"
'''

# ------------------------------------------------------------------ students
FILES["students/models.py"] = '''from django.db import models

from core.models import BaseModel, SchoolScopedModel


class Student(SchoolScopedModel):
    GENDER = [("M", "Male"), ("F", "Female"), ("O", "Other")]
    STATUS = [
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("GRADUATED", "Graduated"),
        ("TRANSFERRED", "Transferred"),
        ("SUSPENDED", "Suspended"),
    ]

    user = models.OneToOneField(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="student_profile"
    )
    admission_number = models.CharField(max_length=32)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    other_names = models.CharField(max_length=80, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER, default="M")
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=80, blank=True)
    religion = models.CharField(max_length=60, blank=True)
    blood_group = models.CharField(max_length=8, blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    photo = models.ImageField(upload_to="students/photos/", blank=True, null=True)
    current_grade_level = models.ForeignKey(
        "schools.GradeLevel", null=True, blank=True, on_delete=models.SET_NULL, related_name="students"
    )
    section = models.ForeignKey(
        "schools.Section", null=True, blank=True, on_delete=models.SET_NULL, related_name="students"
    )
    status = models.CharField(max_length=16, choices=STATUS, default="ACTIVE", db_index=True)
    admission_date = models.DateField(null=True, blank=True)
    medical_notes = models.TextField(blank=True)
    previous_school = models.CharField(max_length=180, blank=True)
    blood_group_note = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = [("school", "admission_number")]
        ordering = ["last_name", "first_name"]
        indexes = [models.Index(fields=["school", "status"])]

    def __str__(self):
        return f"{self.full_name} ({self.admission_number})"

    @property
    def full_name(self):
        return " ".join(part for part in [self.first_name, self.other_names, self.last_name] if part)


class Guardian(SchoolScopedModel):
    user = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="guardian_profiles"
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    relationship = models.CharField(max_length=40, default="Parent")
    phone_number = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    occupation = models.CharField(max_length=120, blank=True)
    address = models.TextField(blank=True)
    national_id = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class StudentGuardian(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="guardian_links")
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name="student_links")
    is_primary = models.BooleanField(default=False)

    class Meta:
        unique_together = [("student", "guardian")]

    def __str__(self):
        return f"{self.guardian} -> {self.student}"


class StudentDocument(SchoolScopedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=160)
    file = models.FileField(upload_to="student_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title


class StudentStatusHistory(SchoolScopedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=16)
    note = models.TextField(blank=True)
    changed_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
'''

FILES["students/serializers.py"] = '''from rest_framework import serializers

from .models import Guardian, Student, StudentDocument, StudentGuardian, StudentStatusHistory


class GuardianSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    children_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Guardian
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class StudentGuardianSerializer(serializers.ModelSerializer):
    guardian_detail = GuardianSerializer(source="guardian", read_only=True)

    class Meta:
        model = StudentGuardian
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentDocument
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "uploaded_at"]


class StudentStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentStatusHistory
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "changed_at"]


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    current_section_name = serializers.SerializerMethodField()
    guardians = StudentGuardianSerializer(source="guardian_links", many=True, read_only=True)

    class Meta:
        model = Student
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]

    def get_current_section_name(self, obj):
        enrollment = obj.enrollments.filter(status="ACTIVE").select_related("section", "grade_level").first()
        if enrollment and enrollment.section:
            return f"{enrollment.grade_level.name} {enrollment.section.name}"
        return None


class StudentListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Student
        fields = [
            "id", "admission_number", "full_name", "first_name", "last_name", "gender",
            "status", "date_of_birth", "profile_picture_placeholder",
        ] if False else [
            "id", "admission_number", "full_name", "first_name", "last_name", "gender",
            "status", "date_of_birth",
        ]
'''

FILES["students/services.py"] = '''from django.db import transaction

from core.services import generate_sequence_number

from .models import Student


@transaction.atomic
def create_student(school, **kwargs):
    """Create a student, generating a unique admission number when omitted."""
    if not kwargs.get("admission_number"):
        kwargs["admission_number"] = generate_sequence_number(
            "ADM", Student, "admission_number", school=school
        )
    return Student.objects.create(school=school, **kwargs)
'''

FILES["students/views.py"] = '''from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsAcademicStaff, IsAnyRole, IsSchoolAdmin

from .models import Guardian, Student, StudentDocument, StudentGuardian, StudentStatusHistory
from .serializers import (
    GuardianSerializer, StudentDocumentSerializer, StudentGuardianSerializer,
    StudentListSerializer, StudentSerializer, StudentStatusHistorySerializer,
)
from .services import create_student


class StudentViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Student.objects.select_related("user").prefetch_related("guardian_links__guardian")
    permission_classes = [IsAnyRole]
    search_fields = ["first_name", "last_name", "admission_number", "other_names"]
    filterset_fields = ["status", "gender"]
    ordering_fields = ["last_name", "admission_number", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return StudentSerializer
        return StudentSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [viewsets.ModelViewSet.permission_classes[0] if False else __import__("core.permissions", fromlist=["IsSchoolAdmin"]).IsSchoolAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        school = serializer.validated_data.get("school") or self.request.user.school
        instance = serializer.save(school=school)
        return instance

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(user=user)
        if user.user_type == "PARENT":
            return qs.filter(guardian_links__guardian__user=user).distinct()
        if user.user_type == "TEACHER":
            return qs.filter(enrollments__section__class_teacher=user).distinct()
        return qs


class GuardianViewSet(viewsets.ModelViewSet):
    from core.mixins import SchoolScopedQuerysetMixin

    class Meta:
        pass
'''

# The GuardianViewSet above is malformed on purpose placeholder -> overwritten below.
del FILES["students/views.py"]
FILES["students/views.py"] = '''from rest_framework import viewsets

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsAnyRole, IsSchoolAdmin

from .models import Guardian, Student, StudentDocument, StudentGuardian, StudentStatusHistory
from .serializers import (
    GuardianSerializer, StudentDocumentSerializer, StudentSerializer,
    StudentGuardianSerializer, StudentStatusHistorySerializer,
)


class StaffWriteMixin:
    """Any role may read, only school admins may write."""

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsSchoolAdmin()]
        return [IsAnyRole()]


class StudentViewSet(StaffWriteMixin, SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Student.objects.select_related("user", "school")
    serializer_class = StudentSerializer
    permission_classes = [IsAnyRole]
    search_fields = ["first_name", "last_name", "admission_number", "other_names"]
    filterset_fields = ["status", "gender"]
    ordering_fields = ["first_name", "last_name", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(user=user)
        if user.user_type == "PARENT":
            return qs.filter(guardian_links__guardian__user=user).distinct()
        return qs


class GuardianViewSet(StaffWriteMixin, SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Guardian.objects.select_related("user")
    serializer_class = GuardianSerializer
    permission_classes = [IsAnyRole]
    search_fields = ["first_name", "last_name", "phone_number", "email"]
    filterset_fields = ["relationship"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "PARENT":
            return qs.filter(user=user)
        return qs


class StudentGuardianViewSet(StaffWriteMixin, SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentGuardian.objects.select_related("student", "guardian")
    serializer_class = StudentGuardianSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["student", "guardian", "is_primary"]

    def get_school_id(self):
        return self.request.user.school_id


class StudentDocumentViewSet(StaffWriteMixin, SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentDocument.objects.select_related("student")
    serializer_class = StudentDocumentSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["student"]


class StudentStatusHistoryViewSet(SchoolScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = StudentStatusHistory.objects.select_related("student", "changed_by")
    serializer_class = StudentStatusHistorySerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["student", "status"]
'''

FILES["students/urls.py"] = '''from django.urls import include, path
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
'''

FILES["students/apps.py"] = '''from django.apps import AppConfig


class StudentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "students"
'''

# ------------------------------------------------------------------ admissions
FILES["admissions/models.py"] = '''from django.db import models

from core.models import SchoolScopedModel


class AdmissionApplication(SchoolScopedModel):
    STATUS = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("UNDER_REVIEW", "Under Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("ENROLLED", "Enrolled"),
    ]
    GENDER = [("M", "Male"), ("F", "Female"), ("O", "Other")]

    application_number = models.CharField(max_length=32)
    session = models.ForeignKey("schools.AcademicSession", on_delete=models.CASCADE, related_name="applications")
    grade_level = models.ForeignKey("schools.GradeLevel", on_delete=models.PROTECT, related_name="applications")

    applicant_first_name = models.CharField(max_length=80)
    applicant_last_name = models.CharField(max_length=80)
    gender = models.CharField(max_length=1, choices=GENDER, default="M")
    date_of_birth = models.DateField(null=True, blank=True)
    previous_school = models.CharField(max_length=200, blank=True)

    guardian_name = models.CharField(max_length=160)
    guardian_phone = models.CharField(max_length=32, blank=True)
    guardian_email = models.EmailField(blank=True)
    guardian_relationship = models.CharField(max_length=40, default="Parent")
    address = models.TextField(blank=True)

    status = models.CharField(max_length=16, choices=STATUS, default="SUBMITTED", db_index=True)
    notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_applications"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_student = models.ForeignKey(
        "students.Student", null=True, blank=True, on_delete=models.SET_NULL, related_name="admission_application"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["school", "status"])]

    def __str__(self):
        return f"{self.first_name} {self.last_name} [{self.status}]"

    @property
    def first_name(self):
        return self.applicant_first_name

    @property
    def last_name(self):
        return self.applicant_last_name

    @property
    def full_name(self):
        return f"{self.applicant_first_name} {self.applicant_last_name}"


class AdmissionDocument(SchoolScopedModel):
    application = models.ForeignKey(AdmissionApplication, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=160)
    file = models.FileField(upload_to="admission_documents/")

    def __str__(self):
        return self.title
'''

FILES["admissions/serializers.py"] = '''from rest_framework import serializers

from .models import AdmissionApplication, AdmissionDocument


class AdmissionDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionDocument
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class AdmissionApplicationSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    grade_level_name = serializers.CharField(source="grade_level.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)

    class Meta:
        model = AdmissionApplication
        fields = "__all__"
        read_only_fields = [
            "id", "created_at", "updated_at", "school", "reviewed_by",
            "reviewed_at", "created_student",
        ]
'''

FILES["admissions/services.py"] = '''from django.db import transaction
from django.utils import timezone

from academics.models import StudentEnrollment
from core.services import generate_sequence_number
from students.models import Student

from .models import AdmissionApplication


@transaction.atomic
def submit_application(school, **data):
    if not data.get("application_number"):
        data["application_number"] = generate_sequence_number(
            "APP", AdmissionApplication, "application_number", school=school
        )
    data.setdefault("status", "SUBMITTED")
    return AdmissionApplication.objects.create(school=school, **data)


@transaction.atomic
def approve_application(application, user):
    application.status = "APPROVED"
    application.reviewed_by = user
    application.reviewed_at = timezone.now()
    application.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
    return application


@transaction.atomic
def reject_application(application, user, reason=""):
    application.status = "REJECTED"
    application.reviewed_by = user
    application.reviewed_at = timezone.now()
    if reason:
        application.notes = (application.notes + "\\n" + reason).strip()
    application.save(update_fields=["status", "reviewed_by", "reviewed_at", "notes", "updated_at"])
    return application


@transaction.atomic
def enroll_application(application, section=None, user=None):
    """Convert an approved application into an enrolled student record.

    Idempotent: enrolling twice returns the existing student.
    """
    if application.created_student_id:
        return application.created_student
    if application.status not in ("APPROVED", "ENROLLED"):
        raise ValueError("Only approved applications can be enrolled.")

    student = Student.objects.create(
        school=application.school,
        admission_number=generate_sequence_number(
            "ADM", Student, "admission_number", school=application.school
        ),
        first_name=application.applicant_first_name,
        last_name=application.applicant_last_name,
        gender=application.gender,
        date_of_birth=application.date_of_birth,
        status="ACTIVE",
    )
    StudentEnrollment.objects.create(
        school=application.school,
        student=student,
        session=application.session,
        grade_level=application.grade_level,
        section=section,
        status="ACTIVE",
    )
    application.status = "ENROLLED"
    application.created_student = student
    if user:
        application.reviewed_by = user
    application.save(update_fields=["status", "created_student", "reviewed_by", "updated_at"])
    return student
'''

FILES["admissions/views.py"] = '''from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsSchoolAdmin
from students.serializers import StudentSerializer

from . import services
from .models import AdmissionApplication, AdmissionDocument
from .serializers import AdmissionApplicationSerializer, AdmissionDocumentSerializer


class AdmissionApplicationViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = AdmissionApplication.objects.select_related("grade_level", "session", "created_student")
    serializer_class = AdmissionApplicationSerializer
    permission_classes = [IsSchoolAdmin]
    filterset_fields = ["status", "session", "grade_level"]
    search_fields = ["applicant_first_name", "applicant_last_name", "application_number"]
    ordering_fields = ["created_at", "status"]

    def perform_create(self, serializer):
        school = self.request.user.school
        instance = services.submit_application(school=school, **serializer.validated_data)
        serializer.instance = instance

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        app = self.get_object()
        services.approve_application(app, request.user)
        return Response(self.get_serializer(app).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        app = self.get_object()
        services.reject_application(app, request.user, request.data.get("reason", ""))
        return Response(self.get_serializer(app).data)

    @action(detail=True, methods=["post"])
    def enroll(self, request, pk=None):
        app = self.get_object()
        section_id = request.data.get("section")
        section = None
        if section_id:
            from schools.models import Section

            section = Section.objects.filter(pk=section_id, school=request.user.school).first()
        student = services.enroll_application(app, section=section, user=request.user)
        return Response(StudentSerializer(student).data, status=201)


class AdmissionDocumentViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = AdmissionDocument.objects.select_related("application")
    serializer_class = AdmissionDocumentSerializer
    permission_classes = [IsSchoolAdmin]
    filterset_fields = ["application"]
'''

FILES["admissions/urls.py"] = '''from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AdmissionApplicationViewSet, AdmissionDocumentViewSet

router = DefaultRouter()
router.register("admissions", AdmissionApplicationViewSet, basename="admission")
router.register("admission-documents", AdmissionDocumentViewSet, basename="admission-document")

urlpatterns = [path("", include(router.urls))]
'''

FILES["admissions/apps.py"] = '''from django.apps import AppConfig


class AdmissionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "admissions"
'''

# ------------------------------------------------------------------ attendance
FILES["attendance/models.py"] = '''from django.db import models

from core.models import BaseModel, SchoolScopedModel


class StudentAttendance(BaseModel):
    STATUS = [
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
        ("LATE", "Late"),
        ("EXCUSED", "Excused"),
    ]

    school = models.ForeignKey("schools.School", on_delete=models.CASCADE, related_name="student_attendance")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="attendance")
    session = models.ForeignKey("schools.AcademicSession", on_delete=models.CASCADE, related_name="attendance")
    section = models.ForeignKey("schools.Section", null=True, blank=True, on_delete=models.SET_NULL)
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=STATUS, default="PRESENT")
    remark = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = [("student", "session", "date")]
        ordering = ["-date"]
        indexes = [models.Index(fields=["school", "date"]), models.Index(fields=["section", "date"])]

    def __str__(self):
        return f"{self.student} {self.date} {self.status}"


class StaffAttendance(BaseModel):
    STATUS = [
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
        ("LATE", "Late"),
        ("LEAVE", "On Leave"),
        ("EXCUSED", "Excused"),
    ]

    school = models.ForeignKey("schools.School", on_delete=models.CASCADE, related_name="staff_attendance")
    staff = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="staff_attendance")
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=STATUS, default="PRESENT")
    remark = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="recorded_staff_attendance"
    )

    class Meta:
        unique_together = [("staff", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.staff} {self.date} {self.status}"


class AttendanceCorrection(BaseModel):
    """Immutable audit trail for attendance edits."""

    attendance = models.ForeignKey(
        StudentAttendance, on_delete=models.CASCADE, related_name="corrections"
    )
    previous_status = models.CharField(max_length=10)
    new_status = models.CharField(max_length=10)
    reason = models.TextField(blank=True)
    corrected_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]
'''

FILES["attendance/serializers.py"] = '''from rest_framework import serializers

from .models import AttendanceCorrection, StaffAttendance, StudentAttendance


class StudentAttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)

    class Meta:
        model = StudentAttendance
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "recorded_by"]

    def validate(self, attrs):
        session = attrs.get("session") or getattr(self.instance, "session", None)
        date = attrs.get("date") or getattr(self.instance, "date", None)
        student = attrs.get("student") or getattr(self.instance, "student", None)
        if session and date and not (session.start_date <= date <= session.end_date):
            raise serializers.ValidationError("Date falls outside the selected academic session.")
        if student and session and student.school_id != session.school_id:
            raise serializers.ValidationError("Student does not belong to this school.")
        return attrs


class BulkAttendanceItemSerializer(serializers.Serializer):
    student = serializers.UUIDField()
    status = serializers.ChoiceField(choices=[c[0] for c in StudentAttendance.STATUS])
    remark = serializers.CharField(required=False, allow_blank=True)


class BulkAttendanceSerializer(serializers.Serializer):
    session = serializers.UUIDField()
    section = serializers.UUIDField(required=False, allow_null=True)
    date = serializers.DateField()
    records = BulkAttendanceItemSerializer(many=True)


class StaffAttendanceSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.full_name", read_only=True)

    class Meta:
        model = StaffAttendance
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "recorded_by"]


class AttendanceCorrectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceCorrection
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "corrected_by"]
'''

FILES["attendance/services.py"] = '''from django.db import transaction

from academics.models import StudentEnrollment

from .models import AttendanceCorrection, StudentAttendance


@transaction.atomic
def record_bulk_attendance(school, session, date, records, section=None, user=None):
    """Upsert attendance for a batch of students.

    Guarantees one record per student per session+date and records a
    correction audit entry when an existing value is changed.
    """
    results = []
    for item in records:
        student_id = item["student"]
        status = item["status"]
        remark = item.get("remark", "")
        existing = StudentAttendance.objects.filter(
            student_id=student_id, session=session, date=date
        ).first()
        if existing:
            if existing.status != status:
                AttendanceCorrection.objects.create(
                    school=student_school(student_id),
                    attendance=existing,
                    previous_status=existing.status,
                    new_status=status,
                    reason=attrs_reason(remark),
                    corrected_by=None,
                ) if False else None
                AttendanceCorrection.objects.create(
                    attendance=existing,
                    previous_status=existing.status,
                    new_status=status,
                    reason=remark or "Bulk update",
                    corrected_by=None,
                )
                existing.status = status
                existing.remark = remark or existing.remark
                existing.save(update_fields=["status", "remark", "updated_at"])
            record = existing
        else:
            record = StudentAttendance.objects.create(
                school_id=student_school(student_id),
                student_id=student_id,
                session_id=session,
                section_id=None,
                date=None,
                status=status,
            ) if False else None
        if record is None:
            pass
        yield_stub = None
    raise NotImplementedError


def student_school(student_id):
    from students.models import Student

    return Student.objects.values_list("school_id", flat=True).get(pk=student_id)


def attrs_reason(remark):
    return remark or "Bulk update"
'''

# attendance/services.py placeholder above is replaced below.
del FILES["attendance/services.py"]
FILES["attendance/services.py"] = '''from django.db import transaction

from .models import AttendanceCorrection, StudentAttendance


@transaction.atomic
def bulk_upsert_attendance(school, session, attendance_date, section, records, user):
    """Create/update attendance for a list of ``{student, status, remark}``.

    * Idempotent per (student, session, date) thanks to the unique constraint.
    * Any status change is recorded in ``AttendanceCorrection`` for auditing.
    * Only students enrolled at ``school`` are accepted.
    """
    from students.models import Student

    ids = [str(r["student"]) for r in records]
    valid = set(
        Student.objects.filter(school=school, id__in=ids).values_list("id", flat=True)
    )
    saved = []
    for row in records:
        student_id = row["student"]
        if student_id not in valid:
            # Ignore cross school references rather than leaking their existence.
            continue
        status = row["status"]
        remark = row.get("remark", "") or ""
        existing = StudentAttendance.objects.filter(
            student_id=student_id, session=session, date=attendance_date
        ).first()
        if existing:
            if existing.status != status:
                AttendanceCorrection.objects.create(
                    attendance=existing,
                    previous_status=existing.status,
                    new_status=status,
                    reason=remark or "Attendance correction",
                    corrected_by=user,
                )
            existing.status = status
            if remark:
                existing.remark = remark
            existing.section = section or existing.section
            existing.recorded_by = user
            existing.save()
            saved.append(existing)
        else:
            saved.append(
                StudentAttendance.objects.create(
                    school=school,
                    student_id=student_id,
                    session=session,
                    section=section,
                    date=attendance_date,
                    status=status,
                    remark=remark,
                    recorded_by=user,
                )
            )
    return saved


def attendance_summary(school, session=None, section=None, student=None):
    """Return counts per status plus a percentage for the supplied filters."""
    qs = StudentAttendance.objects.filter(school=school)
    if session:
        qs = qs.filter(session_id=session)
    if section:
        qs = qs.filter(section_id=section)
    if student:
        qs = qs.filter(student_id=student)
    total = qs.count()
    present = qs.filter(status="PRESENT").count()
    late = qs.filter(status="LATE").count()
    absent = qs.filter(status="ABSENT").count()
    excused = qs.filter(status="EXCUSED").count()
    attended = present + late + excused
    percentage = round((attended / total) * 100, 2) if total else 0
    return {
        "total": total,
        "present": present,
        "late": late,
        "absent": absent,
        "excused": excused,
        "percentage": percentage,
    }
'''

FILES["attendance/views.py"] = '''from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsAcademicStaff, IsAnyRole, IsSchoolAdmin

from . import services
from .models import AttendanceCorrection, StaffAttendance, StudentAttendance
from .serializers import (
    AttendanceCorrectionSerializer, BulkAttendanceSerializer,
    StaffAttendanceSerializer, StudentAttendanceSerializer,
)


class StudentAttendanceViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentAttendance.objects.select_related("student", "session", "section")
    serializer_class = StudentAttendanceSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["date", "status", "section", "session", "student"]
    search_fields = ["student__first_name", "student__last_name", "student__admission_number"]
    ordering_fields = ["date", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(student__user=user)
        if user.user_type == "PARENT":
            return qs.filter(student__guardian_links__guardian__user=user).distinct()
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "bulk"):
            return [IsAcademicStaff()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(
            school=self.request.user.school,
            recorded_by=self.request.user,
        )

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk(self, request):
        serializer = BulkAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        from schools.models import AcademicSession, Section

        school = request.user.school
        session = AcademicSession.objects.get(pk=data["session"], school=school)
        section = None
        if data.get("section"):
            section = Section.objects.filter(pk=data["section"], school=school).first()
        saved = services.bulk_upsert_attendance(
            school=school,
            session=session,
            attendance_date=data["date"],
            section=section,
            records=data["records"],
            user=request.user,
        )
        return Response({"saved": len(saved)}, status=201)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        return Response(
            services.attendance_summary(
                school=request.user.school,
                session=request.query_params.get("session"),
                section=request.query_params.get("section"),
                student=request.query_params.get("student"),
            )
        )


class StaffAttendanceViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StaffAttendance.objects.select_related("staff")
    serializer_class = StaffAttendanceSerializer
    permission_classes = [IsSchoolAdmin]
    filterset_fields = ["date", "status", "staff"]

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school, recorded_by=self.request.user)


class AttendanceCorrectionViewSet(SchoolScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AttendanceCorrection.objects.select_related("attendance", "corrected_by")
    serializer_class = AttendanceCorrectionSerializer
    permission_classes = [IsSchoolAdmin]
    filterset_fields = ["attendance"]

    def get_queryset(self):
        return super().get_queryset().filter(attendance__school_id=self.get_school_id())
'''

FILES["attendance/urls.py"] = '''from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AttendanceCorrectionViewSet, StaffAttendanceViewSet, StudentAttendanceViewSet

router = DefaultRouter()
router.register("attendance", StudentAttendanceViewSet, basename="attendance")
router.register("staff-attendance", StaffAttendanceViewSet, basename="staff-attendance")
router.register("attendance-corrections", AttendanceCorrectionViewSet, basename="attendance-correction")

urlpatterns = [path("", include(router.urls))]
'''

FILES["attendance/apps.py"] = '''from django.apps import AppConfig


class AttendanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "attendance"
'''

# ------------------------------------------------------------------ timetable
FILES["timetable/models.py"] = '''from django.db import models

from core.models import BaseModel, SchoolScopedModel


class Room(SchoolScopedModel):
    name = models.CharField(max_length=80)
    capacity = models.PositiveIntegerField(default=40)
    building = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = [("school", "name")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class TimetablePeriod(SchoolScopedModel):
    name = models.CharField(max_length=60)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_break = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order", "start_time"]
        unique_together = [("school", "name")]

    def __str__(self):
        return f"{self.name} ({self.start_time}-{self.end_time})"


class TimetableEntry(SchoolScopedModel):
    DAYS = [
        (0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"),
        (4, "Friday"), (5, "Saturday"), (6, "Sunday"),
    ]

    session = models.ForeignKey("schools.AcademicSession", on_delete=models.CASCADE, related_name="timetable_entries")
    section = models.ForeignKey("schools.Section", on_delete=models.CASCADE, related_name="timetable_entries")
    day_of_week = models.PositiveSmallIntegerField(choices=DAYS)
    period = models.ForeignKey(TimetablePeriod, on_delete=models.CASCADE, related_name="entries")
    subject = models.ForeignKey("academics.Subject", on_delete=models.CASCADE, related_name="timetable_entries")
    teacher = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="timetable_entries"
    )
    room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL, related_name="entries")
    is_published = models.BooleanField(default=False)

    class Meta:
        unique_together = [
            ("session", "section", "day_of_week", "period"),
        ]
        ordering = ["day_of_week", "period__order"]
        indexes = [models.Index(fields=["school", "session", "section"])]

    def __str__(self):
        return f"{self.section} {self.get_day_of_week_display()} {self.period}"
'''

FILES["timetable/serializers.py"] = '''from rest_framework import serializers

from .models import Room, TimetableEntry, TimetablePeriod


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class TimetablePeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimetablePeriod
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class TimetableEntrySerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True, default=None)
    room_name = serializers.CharField(source="room.name", read_only=True, default=None)
    section_name = serializers.CharField(source="section.name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    day_name = serializers.CharField(source="get_day_of_week_display", read_only=True)

    class Meta:
        model = TimetableEntry
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]

    def validate(self, attrs):
        def pick(field):
            return attrs.get(field) if attrs.get(field) is not None else getattr(self.instance, field, None)

        session = pick("session")
        section = pick("section")
        day = pick("day_of_week")
        period = pick("period")
        teacher = pick("teacher")
        room = pick("room")
        school = self.context["request"].user.school
        school_id = school.id if school else None

        if session and school_id and session.school_id != school_id:
            raise serializers.ValidationError("Session belongs to another school.")
        if section and session and section.grade_level.school_id != session.school_id:
            raise serializers.ValidationError("Section and session belong to different schools.")

        clashes = TimetableEntry.objects.filter(
            session=session, day_of_week=day, period=period
        )
        if self.instance:
            clashes = clashes.exclude(pk=self.instance.pk)

        if teacher and clashes.filter(teacher=teacher).exists():
            raise serializers.ValidationError("This teacher is already booked for that period.")
        if room and clashes.filter(room=room).exists():
            raise serializers.ValidationError("This room is already booked for that period.")
        if school_id and room and room.school_id != school_id:
            raise serializers.ValidationError("Room belongs to another school.")
        return attrs
'''

FILES["timetable/views.py"] = '''from rest_framework import viewsets
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
'''

FILES["timetable/services.py"] = '''def detect_conflicts(entries):
    """Return a list of teacher/room double bookings within a queryset."""
    seen = {}
    conflicts = []
    for entry in entries:
        if entry.is_break if hasattr(entry, "is_break") else False:
            continue
        key_base = (entry.session_id, entry.day_of_week, entry.period_id)
        if entry.teacher_id:
            key = ("teacher", entry.teacher_id, key_base)
            if key in seen:
                conflicts.append(
                    {
                        "type": "teacher",
                        "teacher": entry.teacher_id,
                        "entry": str(entry.id),
                        "conflicts_with": str(seen[key].id),
                    }
                )
            else:
                seen[key] = entry
        if entry.room_id:
            key = ("room", entry.room_id, key_base)
            if key in seen:
                conflicts.append(
                    {
                        "type": "room",
                        "room": entry.room_id,
                        "entry": str(entry.id),
                        "conflicts_with": str(seen[key].id),
                    }
                )
            else:
                seen[key] = entry
    return conflicts
'''

FILES["timetable/urls.py"] = '''from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RoomViewSet, TimetableEntryViewSet, TimetablePeriodViewSet

router = DefaultRouter()
router.register("rooms", RoomViewSet, basename="room")
router.register("timetable-periods", TimetablePeriodViewSet, basename="timetable-period")
router.register("timetable", TimetableEntryViewSet, basename="timetable-entry")

urlpatterns = [path("", include(router.urls))]
'''

FILES["timetable/apps.py"] = '''from django.apps import AppConfig


class TimetableConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "timetable"
'''


def write_all():
    for rel, content in FILES.items():
        path = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        print("wrote", rel)


if __name__ == "__main__":
    write_all()
