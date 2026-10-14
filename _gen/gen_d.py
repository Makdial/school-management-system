"""Generator D: library, hr, transport, audit, reports."""
import os

ROOT = r"C:\Users\makhf\OneDrive\Desktop\School\backend"
FILES = {}

# ------------------------------------------------------------------- library
FILES["library/models.py"] = '''from datetime import timedelta

from django.db import models
from django.utils import timezone

from core.models import BaseModel, SchoolScopedModel


class BookCategory(SchoolScopedModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32, blank=True)

    class Meta:
        unique_together = [("school", "name")]
        ordering = ["name"]
        verbose_name_plural = "Book categories"

    def __str__(self):
        return self.name


class Book(SchoolScopedModel):
    title = models.CharField(max_length=240)
    author = models.CharField(max_length=200, blank=True)
    isbn = models.CharField(max_length=32, blank=True, db_index=True)
    publisher = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(
        BookCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="books"
    )
    published_year = models.PositiveIntegerField(null=True, blank=True)
    total_copies = models.PositiveIntegerField(default=0)
    available_copies = models.PositiveIntegerField(default=0)
    shelf = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["title"]
        indexes = [models.Index(fields=["school", "title"])]

    def __str__(self):
        return self.title


class BookCopy(BaseModel):
    STATUS = [("AVAILABLE", "Available"), ("BORROWED", "Borrowed"), ("LOST", "Lost"), ("DAMAGED", "Damaged")]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="copies")
    copy_code = models.CharField(max_length=60)
    status = models.CharField(max_length=12, choices=STATUS, default="AVAILABLE")
    acquired_on = models.DateField(null=True, blank=True)
    condition_note = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = [("book", "copy_code")]
        ordering = ["copy_code"]

    def __str__(self):
        return f"{self.book.title} #{self.copy_code}"


class Borrowing(SchoolScopedModel):
    STATUS = [("BORROWED", "Borrowed"), ("RETURNED", "Returned"), ("OVERDUE", "Overdue"), ("LOST", "Lost")]

    copy = models.ForeignKey(BookCopy, on_delete=models.PROTECT, related_name="borrowings")
    borrower = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="borrowings")
    borrowed_at = models.DateField(default=timezone.localdate)
    due_date = models.DateField()
    returned_at = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="BORROWED")
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fine_paid = models.BooleanField(default=False)
    issued_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="issued_borrowings"
    )

    class Meta:
        ordering = ["-borrowed_at"]
        indexes = [models.Index(fields=["school", "status"])]

    def __str__(self):
        return f"{self.copy} -> {self.borrower}"

    @property
    def days_overdue(self):
        end = self.returned_at or timezone.localdate()
        if end > self.due_date:
            return (end - self.due_date).days
        return 0


class Reservation(BaseModel):
    STATUS = [("PENDING", "Pending"), ("READY", "Ready"), ("FULFILLED", "Fulfilled"), ("CANCELLED", "Cancelled")]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reservations")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="reservations")
    status = models.CharField(max_length=12, choices=STATUS, default="PENDING")
    reserved_at = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.book} reserved by {self.user}"
'''

FILES["library/serializers.py"] = '''from rest_framework import serializers

from .models import Book, BookCategory, BookCopy, Borrowing


class BookCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookCategory
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class BookCopySerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = BookCopy
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class BookSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    copies = BookCopySerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "available_copies"]


class BorrowingSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="copy.book.title", read_only=True)
    borrower_name = serializers.CharField(source="borrower.full_name", read_only=True)
    copy_code = serializers.CharField(source="copy.copy_code", read_only=True)

    class Meta:
        model = Borrowing
        fields = "__all__"
        read_only_fields = [
            "id", "created_at", "updated_at", "school", "returned_at",
            "status", "fine_amount", "issued_by",
        ]
'''

FILES["library/services.py"] = '''from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.services import money

from .models import Book, BookCopy, Borrowing

DEFAULT_LOAN_DAYS = 14
DEFAULT_FINE_PER_DAY = Decimal("0.50")


def calculate_fine(borrowing, fine_per_day=DEFAULT_FINE_PER_DAY, on_date=None):
    on_date = on_date or timezone.localdate()
    if borrowing.returned_at:
        days_overdue = max((borrowing.returned_at - borrowing.due_date).days, 0)
    else:
        days_overdue = max((on_date - borrowing.due_date).days, 0)
    return money(days_overdue * fine_per_day), days_overdue


@transaction.atomic
def borrow_book(school, borrower, copy, loan_days=DEFAULT_LOAN_DAYS, issued_by=None):
    """Issue a book copy. Guards against borrowing unavailable copies."""
    copy = BookCopy.objects.select_for_update().select_related("book").get(pk=copy.pk)
    if copy.status != "AVAILABLE":
        raise ValueError("This copy is not available for borrowing.")
    existing = Borrowing.objects.filter(copy=copy, status__in=["BORROWED", "OVERDUE"]).exists()
    if existing:
        raise ValueError("This copy is already on loan.")

    borrowing = Borrowing.objects.create(
        school=school,
        copy=copy,
        borrower=borrower,
        borrowed_at=timezone.localdate(),
        due_date=timezone.localdate() + timedelta(days=loan_days),
        status="BORROWED",
        issued_by=issued_by,
    )
    copy.status = "BORROWED"
    copy.save(update_fields=["status", "updated_at"])
    book = Book.objects.select_for_update().get(pk=copy.book_id)
    book.available_copies = max(book.available_copies - 1, 0)
    book.save(update_fields=["available_copies", "updated_at"])
    return borrowing


@transaction.atomic
def return_book(borrowing, fine_per_day=DEFAULT_FINE_PER_DAY):
    """Return a borrowed copy. Duplicate returns are a no-op."""
    borrowing = Borrowing.objects.select_for_update().select_related("copy").get(pk=borrowing.pk)
    if borrowing.status == "RETURNED":
        return borrowing

    borrowing.returned_at = timezone.localdate()
    fine, _ = calculate_fine(borrowing, fine_per_day)
    if borrowing.returned_at > borrowing.due_date:
        borrowing.fine_amount = fine
        borrowing.status = "OVERDUE"
    else:
        borrowing.status = "RETURNED"
    borrowing.save(update_fields=["returned_at", "fine_amount", "status", "updated_at"])

    copy = BookCopy.objects.select_for_update().get(pk=borrowing.copy_id)
    copy.status = "AVAILABLE"
    copy.save(update_fields=["status", "updated_at"])
    book = Book.objects.select_for_update().get(pk=copy.book_id)
    book.available_copies = min(book.available_copies + 1, book.total_copies)
    book.save(update_fields=["available_copies", "updated_at"])
    return borrowing
'''

FILES["library/views.py"] = '''from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsAnyRole, IsLibrarian

from . import services
from .models import Book, BookCategory, BookCopy, Borrowing
from .serializers import (
    BookCategorySerializer, BookCopySerializer, BookSerializer, BorrowingSerializer,
)


class BookCategoryViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = BookCategory.objects.all()
    serializer_class = BookCategorySerializer
    permission_classes = [IsLibrarian]
    search_fields = ["name"]


class BookViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Book.objects.prefetch_related("copies").select_related("category")
    serializer_class = BookSerializer
    permission_classes = [IsLibrarian]
    filterset_fields = ["category"]
    search_fields = ["title", "author", "isbn", "publisher"]

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAnyRole()]
        return super().get_permissions()


class BookCopyViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = BookCopy.objects.select_related("book")
    serializer_class = BookCopySerializer
    permission_classes = [IsLibrarian]
    filterset_fields = ["book", "status"]

    def get_queryset(self):
        return super().get_queryset().filter(book__school_id=self.get_school_id())


class BorrowingViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Borrowing.objects.select_related("copy__book", "borrower", "issued_by")
    serializer_class = BorrowingSerializer
    permission_classes = [IsLibrarian]
    filterset_fields = ["status", "borrower", "copy"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(borrower=user)
        if user.user_type == "PARENT":
            return qs.none()
        return qs

    @action(detail=False, methods=["post"], url_path="borrow")
    def borrow(self, request):
        from students.models import Student

        copy_id = request.data.get("copy")
        borrower_id = request.data.get("borrower") or request.user.id
        copy = BookCopy.objects.filter(
            pk=copy_id, book__school_id=request.user.school_id
        ).first()
        if not copy:
            return Response({"detail": "Copy not found."}, status=404)
        from accounts.models import User

        borrower = User.objects.filter(pk=borrower_id).first()
        if not borrower:
            return Response({"detail": "Borrower not found."}, status=404)
        try:
            borrowing = services.borrow_book(
                request.user.school, borrower, copy, issued_by=request.user
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(borrowing).data, status=201)

    @action(detail=True, methods=["post"])
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        services.return_book(borrowing)
        return Response(self.get_serializer(borrowing).data)

    @action(detail=True, methods=["post"])
    def pay_fine(self, request, pk=None):
        borrowing = self.get_object()
        borrowing.fine_paid = True
        borrowing.save(update_fields=["fine_paid", "updated_at"])
        return Response(self.get_serializer(borrowing).data)

    @action(detail=False, methods=["get"], url_path="overdue")
    def overdue(self, request):
        from django.utils import timezone

        qs = self.get_queryset().filter(
            status__in=["BORROWED", "OVERDUE"], due_date__lt=timezone.localdate()
        )
        return Response(self.get_serializer(qs, many=True).data)
'''

FILES["library/urls.py"] = '''from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookCategoryViewSet, BookCopyViewSet, BookViewSet, BorrowingViewSet

router = DefaultRouter()
router.register("book-categories", BookCategoryViewSet, basename="book-category")
router.register("books", BookViewSet, basename="book")
router.register("book-copies", BookCopyViewSet, basename="book-copy")
router.register("borrowings", BorrowingViewSet, basename="borrowing")

urlpatterns = [path("", include(router.urls))]
'''

FILES["library/apps.py"] = '''from django.apps import AppConfig


class LibraryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "library"
'''

# ------------------------------------------------------------------------ hr
FILES["hr/models.py"] = '''from django.db import models

from core.models import BaseModel, SchoolScopedModel


class StaffProfile(SchoolScopedModel):
    EMPLOYMENT_TYPES = [
        ("FULL_TIME", "Full Time"),
        ("PART_TIME", "Part Time"),
        ("CONTRACT", "Contract"),
        ("INTERN", "Intern"),
    ]
    STATUS = [("ACTIVE", "Active"), ("ON_LEAVE", "On Leave"), ("SUSPENDED", "Suspended"), ("TERMINATED", "Terminated")]

    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="staff_profile"
    )
    employee_id = models.CharField(max_length=40)
    department = models.ForeignKey(
        "schools.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="staff"
    )
    job_title = models.CharField(max_length=120)
    employment_type = models.CharField(max_length=12, choices=EMPLOYMENT_TYPES, default="FULL_TIME")
    hire_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="ACTIVE")
    national_id = models.CharField(max_length=40, blank=True)
    emergency_contact = models.CharField(max_length=120, blank=True)
    emergency_phone = models.CharField(max_length=32, blank=True)
    qualifications = models.TextField(blank=True)

    class Meta:
        unique_together = [("school", "employee_id")]
        ordering = ["user__first_name", "user__last_name"]

    def __str__(self):
        return f"{self.user} ({self.employee_id})"


class Contract(BaseModel):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="contracts")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2)
    document = models.FileField(upload_to="hr/contracts/", blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]


class LeaveType(SchoolScopedModel):
    name = models.CharField(max_length=120)
    max_days_per_year = models.PositiveIntegerField(default=30)
    is_paid = models.BooleanField(default=True)

    class Meta:
        unique_together = [("school", "name")]

    def __str__(self):
        return self.name


class LeaveRequest(SchoolScopedModel):
    STATUS = [("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")]

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="requests")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="PENDING")
    approved_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_leaves"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.staff} {self.leave_type} ({self.status})"

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1
'''

FILES["hr/serializers.py"] = '''from rest_framework import serializers

from .models import Contract, LeaveRequest, LeaveType, StaffProfile


class StaffProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = StaffProfile
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        privileged = request and (
            request.user.is_superuser
            or request.user.user_type in ("SUPERADMIN", "SCHOOL_ADMIN", "HR_MANAGER")
        )
        if not privileged:
            data.pop("salary", None)
            data.pop("national_id", None)
            data.pop("emergency_phone", None)
        return data


class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.user.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    days = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = [
            "id", "created_at", "updated_at", "school", "approved_by", "reviewed_at",
        ]

    def validate(self, attrs):
        start = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        end = attrs.get("end_date") or getattr(self.instance, "end_date", None)
        if start and end and end < start:
            raise serializers.ValidationError("End date cannot be before the start date.")
        return attrs
'''

FILES["hr/views.py"] = '''from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsHR, IsSchoolAdmin

from .models import Contract, LeaveRequest, LeaveType, StaffProfile
from .serializers import ContractSerializer, LeaveRequestSerializer, LeaveTypeSerializer, StaffProfileSerializer


class StaffProfileViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StaffProfile.objects.select_related("user", "department")
    serializer_class = StaffProfileSerializer
    permission_classes = [IsHR]
    filterset_fields = ["department", "status", "employment_type"]
    search_fields = ["user__first_name", "user__last_name", "employee_id", "job_title"]


class ContractViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Contract.objects.select_related("staff__user")
    serializer_class = ContractSerializer
    permission_classes = [IsHR]
    filterset_fields = ["staff"]

    def get_queryset(self):
        return super().get_queryset().filter(staff__school_id=self.get_school_id())


class LeaveTypeViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsSchoolAdmin]


class LeaveRequestViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.select_related("staff__user", "leave_type", "approved_by")
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsHR]
    filterset_fields = ["status", "staff", "leave_type"]

    def perform_create(self, serializer):
        staff = serializer.validated_data.get("staff")
        serializer.save(school_id=staff.school_id)

    @action(detail=True, methods=["post"], permission_classes=[IsSchoolAdmin])
    def approve(self, request, pk=None):
        leave = self.get_object()
        leave.status = "APPROVED"
        leave.approved_by = request.user
        leave.reviewed_at = timezone.now()
        leave.save(update_fields=["status", "approved_by", "reviewed_at", "updated_at"])
        return Response(self.get_serializer(leave).data)

    @action(detail=True, methods=["post"], permission_classes=[IsSchoolAdmin])
    def reject(self, request, pk=None):
        leave = self.get_object()
        leave.status = "REJECTED"
        leave.approved_by = request.user
        leave.reviewed_at = timezone.now()
        leave.save(update_fields=["status", "approved_by", "reviewed_at", "updated_at"])
        return Response(self.get_serializer(leave).data)
'''

FILES["hr/urls.py"] = '''from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ContractViewSet, LeaveRequestViewSet, LeaveTypeViewSet, StaffProfileViewSet

router = DefaultRouter()
router.register("staff", StaffProfileViewSet, basename="staff")
router.register("contracts", ContractViewSet, basename="contract")
router.register("leave-types", LeaveTypeViewSet, basename="leave-type")
router.register("leave-requests", LeaveRequestViewSet, basename="leave-request")

urlpatterns = [path("", include(router.urls))]
'''

FILES["hr/apps.py"] = '''from django.apps import AppConfig


class HrConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hr"
'''

# ------------------------------------------------------------------ transport
FILES["transport/models.py"] = '''from django.db import models

from core.models import BaseModel, SchoolScopedModel


class Vehicle(SchoolScopedModel):
    STATUS = [("ACTIVE", "Active"), ("MAINTENANCE", "Under Maintenance"), ("INACTIVE", "Inactive"), ("SOLD", "Sold")]

    plate_number = models.CharField(max_length=40)
    make = models.CharField(max_length=80, blank=True)
    model = models.CharField(max_length=80, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    capacity = models.PositiveIntegerField(default=40)
    driver_name = models.CharField(max_length=120, blank=True)
    driver_phone = models.CharField(max_length=32, blank=True)
    attendant_name = models.CharField(max_length=120, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    inspection_expiry = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="ACTIVE")

    class Meta:
        unique_together = [("school", "plate_number")]
        ordering = ["plate_number"]

    def __str__(self):
        return f"{self.plate_number} ({self.make} {self.model})"


class TransportRoute(SchoolScopedModel):
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=32, blank=True)
    vehicle = models.ForeignKey(
        Vehicle, null=True, blank=True, on_delete=models.SET_NULL, related_name="routes"
    )
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("school", "name")]
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def student_count(self):
        return self.student_assignments.filter(is_active=True).count()


class TransportStop(BaseModel):
    route = models.ForeignKey(TransportRoute, on_delete=models.CASCADE, related_name="stops")
    name = models.CharField(max_length=160)
    pickup_time = models.TimeField(null=True, blank=True)
    dropoff_time = models.TimeField(null=True, blank=True)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sequence = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["sequence", "name"]

    def __str__(self):
        return f"{self.name} ({self.route.name})"


class StudentTransportAssignment(SchoolScopedModel):
    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="transport_assignments"
    )
    route = models.ForeignKey(TransportRoute, on_delete=models.CASCADE, related_name="student_assignments")
    stop = models.ForeignKey(
        TransportStop, null=True, blank=True, on_delete=models.SET_NULL, related_name="student_assignments"
    )
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [("student", "route")]

    def __str__(self):
        return f"{self.student} -> {self.route}"


class VehicleMaintenance(BaseModel):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="maintenance_records")
    description = models.CharField(max_length=240)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    performed_on = models.DateField()
    next_service_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-performed_on"]

    def __str__(self):
        return f"{self.vehicle} {self.description}"
'''

FILES["transport/serializers.py"] = '''from rest_framework import serializers

from .models import StudentTransportAssignment, TransportRoute, TransportStop, Vehicle, VehicleMaintenance


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class TransportStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportStop
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class TransportRouteSerializer(serializers.ModelSerializer):
    stops = TransportStopSerializer(many=True, read_only=True)
    vehicle_plate = serializers.CharField(source="vehicle.plate_number", read_only=True, default=None)
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = TransportRoute
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class StudentTransportAssignmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    route_name = serializers.CharField(source="route.name", read_only=True)
    stop_name = serializers.CharField(source="stop.name", read_only=True, default=None)

    class Meta:
        model = StudentTransportAssignment
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class VehicleMaintenanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleMaintenance
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
'''

FILES["transport/views.py"] = '''from rest_framework import viewsets

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsTransportManager

from .models import StudentTransportAssignment, TransportRoute, TransportStop, Vehicle, VehicleMaintenance
from .serializers import (
    StudentTransportAssignmentSerializer, TransportRouteSerializer,
    TransportStopSerializer, VehicleMaintenanceSerializer, VehicleSerializer,
)


class VehicleViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsTransportManager]
    filterset_fields = ["status"]
    search_fields = ["plate_number", "make", "model"]


class TransportRouteViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = TransportRoute.objects.prefetch_related("stops").select_related("vehicle")
    serializer_class = TransportRouteSerializer
    permission_classes = [IsTransportManager]
    search_fields = ["name", "code"]


class TransportStopViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = TransportStop.objects.select_related("route")
    serializer_class = TransportStopSerializer
    permission_classes = [IsTransportManager]
    filterset_fields = ["route"]

    def get_queryset(self):
        return super().get_queryset().filter(route__school_id=self.get_school_id())


class StudentTransportAssignmentViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentTransportAssignment.objects.select_related("student", "route", "stop")
    serializer_class = StudentTransportAssignmentSerializer
    permission_classes = [IsTransportManager]
    filterset_fields = ["route", "student", "is_active"]

    def perform_create(self, serializer):
        student = serializer.validated_data["student"]
        serializer.save(school_id=student.school_id)


class VehicleMaintenanceViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = VehicleMaintenance.objects.select_related("vehicle")
    serializer_class = VehicleMaintenanceSerializer
    permission_classes = [IsTransportManager]
    filterset_fields = ["vehicle"]
'''

FILES["transport/urls.py"] = '''from django.urls import include, path
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
'''

FILES["transport/apps.py"] = '''from django.apps import AppConfig


class TransportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "transport"
'''

# ---------------------------------------------------------------------- audit
FILES["audit/models.py"] = '''from django.db import models

from core.models import UUIDModel


class AuditLog(UUIDModel):
    school = models.ForeignKey(
        "schools.School", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    actor = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    action = models.CharField(max_length=120)
    model_name = models.CharField(max_length=120, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["school", "action"])]

    def __str__(self):
        return f"{self.action} by {self.actor_id} on {self.created_at:%Y-%m-%d %H:%M}"


class ActivityLog(UUIDModel):
    LEVELS = [("INFO", "Info"), ("WARNING", "Warning"), ("ERROR", "Error")]

    school = models.ForeignKey(
        "schools.School", null=True, blank=True, on_delete=models.SET_NULL, related_name="activity_logs"
    )
    user = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="activity_logs"
    )
    level = models.CharField(max_length=10, choices=LEVELS, default="INFO")
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.level}] {self.message[:60]}"
'''

FILES["audit/services.py"] = '''from .models import ActivityLog, AuditLog


def log_action(actor, action, obj=None, changes=None, school=None, ip_address=None):
    """Persist an immutable audit record for a sensitive operation."""
    return AuditLog.objects.create(
        school=school or getattr(actor, "school", None) or getattr(obj, "school", None),
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        model_name=obj.__class__.__name__ if obj is not None else "",
        object_id=str(getattr(obj, "pk", "") or ""),
        changes=changes or {},
        ip_address=ip_address,
    )


def log_activity(message, user=None, school=None, level="INFO", metadata=None):
    return ActivityLog.objects.create(
        school=school or getattr(user, "school", None),
        user=user if getattr(user, "is_authenticated", False) else None,
        level=level,
        message=message,
        metadata=metadata or {},
    )
'''

FILES["audit/serializers.py"] = '''from rest_framework import serializers

from .models import ActivityLog, AuditLog


class ReadOnlyModelSerializer(serializers.ModelSerializer):
    """Model serializer whose fields can never be written to.

    Used for immutable audit/activity records. ``read_only_fields`` cannot be
    set to the string ``"__all__"`` (DRF requires a list/tuple), so all fields
    are marked read-only in one place here instead.
    """

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


class AuditLogSerializer(ReadOnlyModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = "__all__"


class ActivityLogSerializer(ReadOnlyModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True, default=None)

    class Meta:
        model = ActivityLog
        fields = "__all__"
'''

FILES["audit/views.py"] = '''from rest_framework import viewsets

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsSchoolAdmin

from .models import ActivityLog, AuditLog
from .serializers import ActivityLogSerializer, AuditLogSerializer


class AuditLogViewSet(SchoolScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("actor")
    serializer_class = AuditLogSerializer
    permission_classes = [IsSchoolAdmin]
    filterset_fields = ["action", "model_name", "actor"]
    search_fields = ["action", "model_name", "object_id"]


class ActivityLogViewSet(SchoolScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ActivityLog.objects.select_related("user")
    serializer_class = ActivityLogSerializer
    permission_classes = [IsSchoolAdmin]
    filterset_fields = ["level", "user"]
'''

FILES["audit/urls.py"] = '''from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ActivityLogViewSet, AuditLogViewSet

router = DefaultRouter()
router.register("audit-logs", AuditLogViewSet, basename="audit-log")
router.register("activity-logs", ActivityLogViewSet, basename="activity-log")

urlpatterns = [path("", include(router.urls))]
'''

FILES["audit/apps.py"] = '''from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"
'''

FILES["audit/middleware.py"] = '''"""Lightweight middleware that records write activity for auditing."""

from .services import log_activity

AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class ActivityLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if (
                request.path.startswith("/api/")
                and request.method in AUDITED_METHODS
                and response.status_code >= 400
                and response.status_code != 401
            ):
                user = getattr(request, "user", None)
                log_activity(
                    f"{request.method} {request.path} -> {response.status_code}",
                    user=user if getattr(user, "is_authenticated", False) else None,
                    level="WARNING",
                    metadata={"status": response.status_code},
                )
        except Exception:  # pragma: no cover - never break a request over logging
            pass
        return response
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
