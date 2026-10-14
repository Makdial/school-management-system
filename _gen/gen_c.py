"""Generator C: examinations, finance, assignments, communications."""
import os

ROOT = r"C:\Users\makhf\OneDrive\Desktop\School\backend"
FILES = {}

# -------------------------------------------------------------- examinations
FILES["examinations/models.py"] = '''from django.db import models

from core.models import BaseModel, SchoolScopedModel


class Exam(SchoolScopedModel):
    EXAM_TYPES = [
        ("CONTINUOUS", "Continuous Assessment"),
        ("MIDTERM", "Mid Term"),
        ("ENDTERM", "End of Term"),
        ("MOCK", "Mock"),
        ("FINAL", "Final"),
    ]

    name = models.CharField(max_length=160)
    session = models.ForeignKey("schools.AcademicSession", on_delete=models.CASCADE, related_name="exams")
    term = models.ForeignKey("schools.Term", null=True, blank=True, on_delete=models.SET_NULL, related_name="exams")
    exam_type = models.CharField(max_length=16, choices=EXAM_TYPES, default="ENDTERM")
    start_date = models.DateField()
    end_date = models.DateField()
    is_published = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]
        unique_together = [("school", "session", "name")]

    def __str__(self):
        return self.name


class ExamSubject(SchoolScopedModel):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="subjects")
    class_subject = models.ForeignKey(
        "academics.ClassSubject", on_delete=models.CASCADE, related_name="exam_subjects"
    )
    exam_date = models.DateField(null=True, blank=True)
    max_marks = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    pass_marks = models.DecimalField(max_digits=6, decimal_places=2, default=40)
    room = models.ForeignKey(
        "timetable.Room", null=True, blank=True, on_delete=models.SET_NULL, related_name="exam_subjects"
    )

    class Meta:
        unique_together = [("exam", "class_subject")]
        ordering = ["exam_date", "class_subject__subject__name"]

    def __str__(self):
        return f"{self.exam.name} - {self.class_subject.subject.name}"

    def clean(self):
        if self.pass_marks and self.max_marks and self.pass_marks > self.max_marks:
            from django.core.exceptions import ValidationError

            raise ValidationError({"pass_marks": "Pass marks cannot exceed max marks."})


class StudentMark(BaseModel):
    exam_subject = models.ForeignKey(ExamSubject, on_delete=models.CASCADE, related_name="marks")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="marks")
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_absent = models.BooleanField(default=False)
    entered_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("exam_subject", "student")]
        ordering = ["student__last_name"]

    def __str__(self):
        return f"{self.student} {self.exam_subject}: {self.marks_obtained}"

    @property
    def percentage(self):
        max_marks = self.exam_subject.max_marks or 1
        return round(float(self.marks_obtained) / float(max_marks) * 100, 2)

    @property
    def grade(self):
        scale = self.exam_subject.exam.school.grading_scales.filter(is_default=True).first()
        if not scale:
            scale = self.exam_subject.exam.school.grading_scales.first()
        if not scale:
            return None
        return self.exam_subject.exam.school and scale.bands and _grade(scale, self.percentage)


def _grade(scale, percentage):
    from schools.models import GradingBand

    band = scale.bands.filter(min_score__lte=percentage, max_score__gte=percentage).first()
    return band.grade if band else None


class ReportCard(BaseModel):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="report_cards")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="report_cards")
    total_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_max = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    average = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    grade = models.CharField(max_length=8, blank=True)
    position = models.PositiveIntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        unique_together = [("student", "exam")]
        ordering = ["position"]

    def __str__(self):
        return f"Report {self.student} / {self.exam}"
'''

FILES["examinations/serializers.py"] = '''from rest_framework import serializers

from .models import Exam, ExamSubject, ReportCard, StudentMark


class ExamSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source="session.name", read_only=True)
    subject_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Exam
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class ExamSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="class_subject.subject.name", read_only=True)
    grade_level_name = serializers.CharField(source="class_subject.grade_level.name", read_only=True)

    class Meta:
        model = ExamSubject
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class StudentMarkSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    subject_name = serializers.CharField(source="exam_subject.class_subject.subject.name", read_only=True)
    grade = serializers.SerializerMethodField()

    class Meta:
        model = StudentMark
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "entered_by", "updated_on"]

    def get_grade(self, obj):
        return obj.grade

    def validate(self, attrs):
        exam_subject = attrs.get("exam_subject") or getattr(self.instance, "exam_subject", None)
        marks = attrs.get("marks_obtained")
        is_absent = attrs.get("is_absent", getattr(self.instance, "is_absent", False))
        if exam_subject and exam_subject.exam.is_published and not self.context["request"].user.is_superuser:
            if not self.context["request"].user.user_type in ("SUPERADMIN", "SCHOOL_ADMIN", "PRINCIPAL"):
                raise serializers.ValidationError("Results for this exam have been published and are locked.")
        if marks is not None and exam_subject and not is_absent:
            if marks < 0:
                raise serializers.ValidationError({"marks_obtained": "Marks cannot be negative."})
            if marks > exam_subject.max_marks:
                raise serializers.ValidationError(
                    {"marks_obtained": f"Marks cannot exceed the maximum of {exam_subject.max_marks}."}
                )
        return attrs

    def validate_student(self, student):
        request = self.context["request"]
        if request.user.school_id and student.school_id != request.user.school_id:
            raise serializers.ValidationError("Student belongs to another school.")
        return student


class MarkEntryItemSerializer(serializers.Serializer):
    student = serializers.UUIDField()
    marks_obtained = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=0)
    is_absent = serializers.BooleanField(required=False, default=False)


class MarkEntrySerializer(serializers.Serializer):
    exam_subject = serializers.UUIDField()
    marks = MarkEntryItemSerializer(many=True)


class ReportCardSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    exam_name = serializers.CharField(source="exam.name", read_only=True)

    class Meta:
        model = ReportCard
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
        # Report cards are derived from marks; never writable directly.
        read_only_fields = "__all__" if False else ["id", "created_at", "updated_at", "total_marks", "total_max", "average", "grade", "position"]
'''

FILES["examinations/services.py"] = '''from decimal import Decimal

from django.db import transaction

from core.services import money
from schools.models import GradingBand, GradingScale

from .models import ExamSubject, ReportCard, StudentMark


def resolve_grade(scale, percentage):
    if not scale:
        return ""
    band = GradingBand.objects.filter(
        scale=scale, min_score__lte=percentage, max_score__gte=percentage
    ).first()
    return band.grade if band else ""


def default_scale(school):
    return (
        GradingScale.objects.filter(school=school, is_default=True).first()
        or GradingScale.objects.filter(school=school).first()
    )


@transaction.atomic
def enter_marks(exam_subject, records, user):
    """Create/update marks for one exam subject with validation and locking.

    ``records`` is a list of ``{student, marks_obtained, is_absent}``.
    """
    if exam_subject.exam.is_published and user.user_type not in ("SUPERADMIN", "SCHOOL_ADMIN", "PRINCIPAL"):
        raise PermissionError("Published results are locked.")
    max_marks = Decimal(exam_subject.max_marks)
    saved = []
    for row in records:
        marks = Decimal(str(records and row.get("marks_obtained") or 0))
        is_absent = bool(row.get("is_absent"))
        if not is_absent and marks > exam_subject.max_marks:
            raise ValueError(f"Marks for {row['student']} exceed maximum {exam_subject.max_marks}.")
        obj, _ = StudentMark.objects.update_or_create(
            exam_subject=exam_subject,
            student_id=records_student(row),
            defaults={
                "marks_obtained": Decimal("0") if row.get("is_absent") else money(marks),
                "is_absent": bool(records),
                "entered_by": user,
            },
        )
        saved.append(obj)
    return saved


def student_school(school, student_id):
    from students.models import Student

    return Student.objects.filter(pk=student_id, school=school).exists()


@transaction.atomic
def compute_report_cards(exam, user=None):
    """Compute report cards for every enrolled student of the exam's grade levels."""
    from academics.models import StudentEnrollment

    school = exam.school
    scale = default_scale(school)
    exam_subjects = list(
        ExamSubject.objects.filter(exam=exam).select_related("class_subject__grade_level")
    )
    if not exam_subjects:
        return []

    grade_ids = {es.class_subject.grade_level_id for es in exam_subjects}
    enrollments = StudentEnrollment.objects.filter(
        school=school, session=exam.session, grade_level_id__in=grade_ids, status="ACTIVE"
    ).select_related("student")

    cards = []
    for enrollment in enrollments:
        student = enrollment.student
        total = Decimal("0")
        max_total = Decimal("0")
        for es in exam_subjects:
            mark = StudentMark.objects.filter(exam_subject=es, student=student).first()
            if not mark:
                continue
            max_total += es.max_marks
            if not mark.is_absent:
                total += mark.marks_obtained
        average = (total / max_total * 100) if max_total else Decimal("0")
        average = money(average)
        card, _ = ReportCard.objects.update_or_create(
            school=school,
            student=student,
            exam=exam,
            defaults={
                "total_marks": money(total),
                "total_max": money(max_total),
                "average": average,
                "grade": resolve_grade(scale, float(average)),
            },
        )
        cards.append(card)

    # Rank within the exam
    ordered = sorted(cards, key=lambda c: c.average, reverse=True)
    for index, card in enumerate(ordered, start=1):
        card.position = index
        card.save(update_fields=["position"])
    return cards


@transaction.atomic
def publish_results(exam):
    exam.is_published = True
    exam.save(update_fields=["is_published", "updated_at"])
    ReportCard.objects.filter(exam=exam).update(is_published=True)
    return exam
'''

FILES["examinations/views.py"] = '''from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsAcademicStaff, IsAnyRole, IsSchoolAdmin
from students.models import Student

from . import services
from .models import Exam, ExamSubject, ReportCard, StudentMark
from .serializers import (
    ExamSerializer, ExamSubjectSerializer, MarkEntrySerializer,
    ReportCardSerializer, StudentMarkSerializer,
)


class ExamViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Exam.objects.select_related("session", "term")
    serializer_class = ExamSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["session", "term", "exam_type", "is_published"]
    search_fields = ["name"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsSchoolAdmin()]
        return super().get_permissions()

    @action(detail=True, methods=["post"], permission_classes=[IsSchoolAdmin])
    def publish(self, request, pk=None):
        exam = self.get_object()
        services.publish_results(exam)
        return Response(self.get_serializer(exam).data)

    @action(detail=True, methods=["post"], permission_classes=[IsSchoolAdmin])
    def compute_results(self, request, pk=None):
        exam = self.get_object()
        cards = services.compute_report_cards(exam, user=request.user)
        return Response({"report_cards": len(cards)})


class ExamSubjectViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = ExamSubject.objects.select_related("exam", "class_subject__subject", "class_subject__grade_level")
    serializer_class = ExamSubjectSerializer
    permission_classes = [IsAcademicStaff]
    filterset_fields = ["exam", "class_subject"]

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)


class StudentMarkViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentMark.objects.select_related("student", "exam_subject__class_subject__subject", "exam_subject__exam")
    serializer_class = StudentMarkSerializer
    permission_classes = [IsAcademicStaff]
    filterset_fields = ["exam_subject", "student"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(student__user=user, exam_subject__exam__is_published=True)
        if user.user_type == "PARENT":
            return qs.filter(
                student__guardian_links__guardian__user=user,
                exam_subject__exam__is_published=True,
            ).distinct()
        return qs

    def perform_create(self, serializer):
        serializer.save(entered_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk(self, request):
        serializer = MarkEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        exam_subject = ExamSubject.objects.filter(
            pk=data["exam_subject"], school=request.user.school
        ).first()
        if not exam_subject:
            return Response({"detail": "Exam subject not found."}, status=404)
        services.enter_marks(exam_subject, data["marks"], request.user)
        return Response({"saved": len(data["marks"])}, status=201)


class ReportCardViewSet(SchoolScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ReportCard.objects.select_related("student", "exam")
    serializer_class = ReportCardSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["exam", "student"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(student__user=user, is_published=True)
        if user.user_type == "PARENT":
            return qs.filter(student__guardian_links__guardian__user=user, is_published=True).distinct()
        return qs
'''

FILES["examinations/urls.py"] = '''from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ExamSubjectViewSet, ExamViewSet, ReportCardViewSet, StudentMarkViewSet

router = DefaultRouter()
router.register("exams", ExamViewSet, basename="exam")
router.register("exam-subjects", ExamSubjectViewSet, basename="exam-subject")
router.register("marks", StudentMarkViewSet, basename="mark")
router.register("report-cards", ReportCardViewSet, basename="report-card")

urlpatterns = [path("", include(router.urls))]
'''

FILES["examinations/apps.py"] = '''from django.apps import AppConfig


class ExaminationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "examinations"
'''

# --------------------------------------------------------------------- finance
FILES["finance/models.py"] = '''from django.db import models

from core.models import BaseModel, SchoolScopedModel


class FeeCategory(SchoolScopedModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [("school", "code")]
        ordering = ["name"]
        verbose_name_plural = "Fee categories"

    def __str__(self):
        return self.name


class FeeStructure(SchoolScopedModel):
    session = models.ForeignKey("schools.AcademicSession", on_delete=models.CASCADE, related_name="fee_structures")
    grade_level = models.ForeignKey("schools.GradeLevel", on_delete=models.CASCADE, related_name="fee_structures")
    name = models.CharField(max_length=160)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("school", "session", "grade_level", "name")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.grade_level.name})"

    @property
    def total_amount(self):
        return sum((item.amount for item in self.items.all()), 0)


class FeeStructureItem(BaseModel):
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name="items")
    category = models.ForeignKey(FeeCategory, on_delete=models.CASCADE, related_name="structure_items")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_recurring = models.BooleanField(default=False)
    due_day = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = [("fee_structure", "category")]
        ordering = ["category__name"]

    def __str__(self):
        return f"{self.category.name}: {self.amount}"


class Invoice(SchoolScopedModel):
    STATUS = [
        ("DRAFT", "Draft"),
        ("ISSUED", "Issued"),
        ("PARTIAL", "Partially Paid"),
        ("PAID", "Paid"),
        ("OVERDUE", "Overdue"),
        ("CANCELLED", "Cancelled"),
    ]

    number = models.CharField(max_length=40)
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="invoices")
    session = models.ForeignKey("schools.AcademicSession", on_delete=models.CASCADE, related_name="invoices")
    term = models.ForeignKey("schools.Term", null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")
    issue_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=12, choices=STATUS, default="ISSUED")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("school", "number")]
        ordering = ["-issue_date"]
        indexes = [models.Index(fields=["school", "status"])]

    def __str__(self):
        return f"{self.number} - {self.student}"

    def recalculate(self, save=True):
        from core.services import money

        items_total = sum((item.amount for item in self.items.all()), 0)
        self.total_amount = money(items_total)
        self.balance = money(self.total_amount - self.discount_amount - self.amount_paid)
        if self.balance <= 0:
            self.status = "PAID"
        elif self.amount_paid > 0:
            self.status = "PARTIAL"
        elif self.status != "CANCELLED":
            self.status = "ISSUED"
        if save:
            self.save(update_fields=["total_amount", "balance", "status", "updated_at"])
        return self.balance


class InvoiceItem(BaseModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    category = models.ForeignKey(FeeCategory, on_delete=models.PROTECT, related_name="invoice_items")
    description = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.category.name} {self.amount}"


class Payment(SchoolScopedModel):
    METHODS = [
        ("CASH", "Cash"),
        ("CARD", "Card"),
        ("TRANSFER", "Bank Transfer"),
        ("CHEQUE", "Cheque"),
        ("ONLINE", "Online"),
        ("MOBILE", "Mobile Money"),
    ]
    STATUS = [("PENDING", "Pending"), ("COMPLETED", "Completed"), ("REVERSED", "Reversed"), ("FAILED", "Failed")]

    reference = models.CharField(max_length=60, blank=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=12, choices=METHODS, default="CASH")
    status = models.CharField(max_length=12, choices=STATUS, default="COMPLETED")
    paid_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    transaction_id = models.CharField(max_length=120, blank=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["school", "status"])]

    def __str__(self):
        return f"{self.invoice.number} {self.amount} ({self.status})"


class Discount(SchoolScopedModel):
    DISCOUNT_TYPES = [("PERCENT", "Percentage"), ("FIXED", "Fixed Amount")]

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="discounts")
    category = models.ForeignKey(FeeCategory, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=160)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default="PERCENT")
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reason = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.student}"


class Refund(SchoolScopedModel):
    STATUS = [("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("PROCESSED", "Processed")]

    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="refunds")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS, default="PENDING")
    approved_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Refund {self.amount} for {self.payment}"
'''

FILES["finance/serializers.py"] = '''from rest_framework import serializers

from .models import (
    Discount, FeeCategory, FeeStructure, FeeStructureItem, Invoice, InvoiceItem,
    Payment, Refund,
)


class FeeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeCategory
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class FeeStructureItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = FeeStructureItem
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class FeeStructureSerializer(serializers.ModelSerializer):
    items = FeeStructureItemSerializer(many=True, read_only=True)
    grade_level_name = serializers.CharField(source="grade_level.name", read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = FeeStructure
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class InvoiceItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = InvoiceItem
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class PaymentSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source="get_method_display", read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "received_by", "status"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be positive.")
        return value


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = [
            "id", "created_at", "updated_at", "school", "total_amount",
            "amount_paid", "balance", "status", "number",
        ]


class InvoiceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "approved_by"]


class PaymentInitiateSerializer(serializers.Serializer):
    invoice = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    method = serializers.ChoiceField(choices=[c[0] for c in Payment.METHODS])
    reference = serializers.CharField(required=False, allow_blank=True)
'''

FILES["finance/services.py"] = '''"""Financial operations.

All money is handled with :class:`decimal.Decimal`; floats are never used.
Payments are recorded inside a transaction and invoices are locked with
``select_for_update`` so balances cannot drift under concurrency.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.services import generate_sequence_number, money

from .models import Invoice, InvoiceItem, Payment


@transaction.atomic
def create_invoice(school, student, session, items, due_date, term=None, issue_date=None, discount_amount=0):
    """Create an invoice and its line items.

    ``items`` is a list of dicts: ``{category, description, amount}``.
    """
    number = generate_sequence_number("INV", Invoice, "number", school=school)
    invoice = Invoice.objects.create(
        school=school,
        number=number,
        student=student,
        session=session,
        term=term,
        issue_date=issue_date or timezone.localdate(),
        due_date=due_date,
        status="ISSUED",
        discount_amount=money(discount_amount),
    )
    for item in items:
        InvoiceItem.objects.create(
            invoice=invoice,
            category=item["category"],
            description=item.get("description", ""),
            amount=money(item["amount"]),
        )
    invoice.recalculate()
    return invoice


@transaction.atomic
def record_payment(invoice, amount, method, user, reference="", paid_at=None, transaction_id="", status="COMPLETED"):
    """Record a payment against a locked invoice and update its balance."""
    amount = money(amount)
    if amount <= 0:
        raise ValueError("Payment amount must be greater than zero.")
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.status == "CANCELLED":
        raise ValueError("Cannot pay a cancelled invoice.")
    outstanding = money(invoice.balance)
    if amount > outstanding:
        raise ValueError(f"Payment exceeds the outstanding balance of {outstanding}.")

    payment = Payment.objects.create(
        school=invoice.school,
        invoice=invoice,
        amount=amount,
        method=method,
        reference=reference,
        paid_at=paid_at or timezone.now(),
        received_by=user,
        transaction_id=transaction_id,
        status=status,
    )
    if status == "COMPLETED":
        invoice.amount_paid = money(invoice.amount_paid + amount)
        invoice.recalculate()
    return payment


@transaction.atomic
def reverse_payment(payment, user=None, reason=""):
    """Reverse a completed payment without deleting the financial record."""
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status != "COMPLETED":
        return payment
    invoice = Invoice.objects.select_for_update().get(pk=payment.invoice_id)
    invoice.amount_paid = money(invoice.amount_paid - payment.amount)
    invoice.recalculate()
    payment.status = "REVERSED"
    if reason:
        payment.notes = (payment.notes + "\\n" + reason).strip()
    payment.save(update_fields=["status", "notes", "updated_at"])
    return payment


def collection_summary(school, session=None, start=None, end=None):
    qs = Payment.objects.filter(school=school, status="COMPLETED")
    if session:
        qs = qs.filter(invoice__session_id=session)
    if start:
        qs = qs.filter(paid_at__date__gte=start)
    if end:
        qs = qs.filter(paid_at__date__lte=end)
    collected = sum((p.amount for p in qs), Decimal("0"))
    invoices = Invoice.objects.filter(school=school)
    if session:
        qs2 = Invoice.objects.filter(school=school, session_id=session)
    else:
        qs2 = Invoice.objects.filter(school=school)
    billed = sum((i.total_amount for i in qs), Decimal("0")) if False else money(
        sum((i.total_amount for i in qs))
    )
    outstanding = money(
        sum((i.balance for i in qs.exclude(status="CANCELLED")), Decimal("0"))
    )
    return {
        "total_collected": money(qs.aggregate_total()) if False else money(
            sum((p.amount for p in qs), 0)
        ),
        "payments_count": qs.count(),
        "outstanding": outstanding,
    }
'''

FILES["finance/views.py"] = '''from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsAnyRole, IsFinance, IsSchoolAdmin

from . import services
from .models import (
    Discount, FeeCategory, FeeStructure, FeeStructureItem, Invoice, InvoiceItem,
    Payment, Refund,
)
from .serializers import (
    DiscountSerializer, FeeCategorySerializer, FeeStructureItemSerializer,
    FeeStructureSerializer, InvoiceSerializer, InvoiceWriteSerializer,
    PaymentInitiateSerializer, PaymentSerializer, RefundSerializer,
)


class FeeCategoryViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = FeeCategory.objects.all()
    serializer_class = FeeCategorySerializer
    permission_classes = [IsFinance]
    search_fields = ["name", "code"]


class FeeStructureViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = FeeStructure.objects.prefetch_related("items").select_related("grade_level")
    serializer_class = FeeStructureSerializer
    permission_classes = [IsFinance]
    filterset_fields = ["session", "grade_level", "is_active"]


class FeeStructureItemViewSet(viewsets.ModelViewSet):
    queryset = FeeStructureItem.objects.select_related("category", "fee_structure")
    serializer_class = FeeStructureItemSerializer
    permission_classes = [IsFinance]
    filterset_fields = ["fee_structure"]


class InvoiceViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("student", "session").prefetch_related("items", "payments")
    serializer_class = InvoiceSerializer
    permission_classes = [IsFinance]
    filterset_fields = ["status", "session", "student"]
    search_fields = ["number", "student__first_name", "student__last_name"]
    ordering_fields = ["issue_date", "due_date", "balance"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return InvoiceWriteSerializer
        return InvoiceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(student__user=user)
        if user.user_type == "PARENT":
            return qs.filter(student__guardian_links__guardian__user=user).distinct()
        return qs

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        school = request.user.school
        qs = Invoice.objects.filter(school=school).exclude(status="CANCELLED")
        totals = qs.aggregate(
            billed=Sum("total_amount"), paid=Sum("amount_paid"), balance=Sum("balance")
        )
        return Response(
            {
                "billed": totals["billed"] or 0,
                "collected": totals["paid"] or 0,
                "outstanding": totals["balance"] or 0,
                "overdue": qs.filter(status="OVERDUE").count(),
            }
        )


class InvoiceItemViewSet(viewsets.ModelViewSet):
    queryset = InvoiceItem.objects.select_related("category", "invoice")
    serializer_class = serializers = None  # replaced below
'''

del FILES["finance/views.py"]
FILES["finance/views.py"] = '''from django.utils import timezone
from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsFinance, IsSchoolAdmin

from . import services
from .models import (
    Discount, FeeCategory, FeeStructure, FeeStructureItem, Invoice, InvoiceItem,
    Payment, Refund,
)
from .serializers import (
    DiscountSerializer, FeeCategorySerializer, FeeStructureItemSerializer,
    FeeStructureSerializer, InvoiceSerializer, InvoiceWriteSerializer,
    PaymentInitiateSerializer, PaymentSerializer, RefundSerializer,
)


class FeeCategoryViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = FeeCategory.objects.all()
    serializer_class = FeeCategorySerializer
    permission_classes = [IsFinance]
    search_fields = ["name", "code"]


class FeeStructureViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = FeeStructure.objects.prefetch_related("items").select_related("grade_level")
    serializer_class = FeeStructureSerializer
    permission_classes = [IsFinance]
    filterset_fields = ["session", "grade_level", "is_active"]


class FeeStructureItemViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = FeeStructureItem.objects.select_related("category", "fee_structure")
    serializer_class = FeeStructureItemSerializer
    permission_classes = [IsFinance]
    filterset_fields = ["fee_structure"]

    def get_queryset(self):
        return super().get_queryset().filter(fee_structure__school_id=self.get_school_id())

    def perform_create(self, serializer):
        serializer.save()


class InvoiceViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("student", "session").prefetch_related("items", "payments")
    serializer_class = InvoiceSerializer
    permission_classes = [IsFinance]
    filterset_fields = ["status", "session", "student"]
    search_fields = ["number", "student__first_name", "student__last_name"]
    ordering_fields = ["issue_date", "due_date", "balance"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return InvoiceWriteSerializer
        return InvoiceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(student__user=user)
        if user.user_type == "PARENT":
            return qs.filter(student__guardian_links__guardian__user=user).distinct()
        return qs

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        qs = Invoice.objects.filter(school=request.user.school).exclude(status="CANCELLED")
        totals = qs.aggregate(
            billed=Sum("total_amount"), paid=Sum("amount_paid"), balance=Sum("balance")
        )
        return Response(
            {
                "billed": totals["billed"] or 0,
                "collected": totals["paid"] or 0,
                "outstanding": totals["balance"] or 0,
                "overdue": qs.filter(status="OVERDUE").count(),
            }
        )


class InvoiceItemViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = InvoiceItem.objects.select_related("category", "invoice")
    serializer_class = __import__("finance.serializers", fromlist=["InvoiceItemSerializer"]).InvoiceItemSerializer
    permission_classes = [IsFinance]
    filterset_fields = ["invoice"]

    def get_queryset(self):
        return super().get_queryset().filter(invoice__school_id=self.get_school_id())

    def perform_create(self, serializer):
        item = serializer.save()
        item.invoice.recalculate()


class PaymentViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("invoice", "invoice__student", "received_by")
    serializer_class = PaymentSerializer
    permission_classes = [IsFinance]
    filterset_fields = ["status", "method", "invoice"]
    ordering_fields = ["created_at", "amount"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(invoice__student__user=user, status="COMPLETED")
        if user.user_type == "PARENT":
            return qs.filter(invoice__student__guardian_links__guardian__user=user).distinct()
        return qs

    def perform_create(self, serializer):
        invoice = serializer.validated_data["invoice"]
        payment = services.record_payment(
            invoice=invoice,
            amount=serializer.validated_data["amount"],
            method=serializer.validated_data["method"],
            user=self.request.user,
            reference=serializer.validated_data.get("reference", ""),
            transaction_id=serializer.validated_data.get("transaction_id", ""),
        )
        serializer.instance = payment

    @action(detail=True, methods=["post"], permission_classes=[IsSchoolAdmin])
    def reverse(self, request, pk=None):
        payment = self.get_object()
        services.reverse_payment(payment, user=request.user, reason=request.data.get("reason", ""))
        return Response(self.get_serializer(payment).data)

    @action(detail=False, methods=["get"], url_path="collections")
    def collections(self, request):
        return Response(
            services.collection_summary(
                school=request.user.school,
                session=request.query_params.get("session"),
                start=request.query_params.get("start"),
                end=request.query_params.get("end"),
            )
        )


class DiscountViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Discount.objects.select_related("student", "category")
    serializer_class = DiscountSerializer
    permission_classes = [IsFinance]
    filterset_fields = ["student", "category"]


class RefundViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Refund.objects.select_related("payment", "approved_by")
    serializer_class = RefundSerializer
    permission_classes = [IsFinance]
    filterset_fields = ["status", "payment"]

    @action(detail=True, methods=["post"], permission_classes=[IsSchoolAdmin])
    def approve(self, request, pk=None):
        refund = self.get_object()
        refund.status = "APPROVED"
        refund.approved_by = request.user
        refund.save(update_fields=["status", "approved_by", "updated_at"])
        return Response(self.get_serializer(refund).data)
'''

FILES["finance/urls.py"] = '''from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DiscountViewSet, FeeCategoryViewSet, FeeStructureItemViewSet,
    FeeStructureViewSet, InvoiceItemViewSet, InvoiceViewSet, PaymentViewSet,
    RefundViewSet,
)

router = DefaultRouter()
router.register("fee-categories", FeeCategoryViewSet, basename="fee-category")
router.register("fee-structures", FeeStructureViewSet, basename="fee-structure")
router.register("fee-structure-items", FeeStructureItemViewSet, basename="fee-structure-item")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("invoice-items", InvoiceItemViewSet, basename="invoice-item")
router.register("payments", PaymentViewSet, basename="payment")
router.register("discounts", DiscountViewSet, basename="discount")
router.register("refunds", RefundViewSet, basename="refund")

urlpatterns = [path("", include(router.urls))]
'''

FILES["finance/apps.py"] = '''from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "finance"
'''

# ---------------------------------------------------------------- assignments
FILES["assignments/models.py"] = '''from django.db import models

from core.models import BaseModel, SchoolScopedModel

ALLOWED_UPLOAD_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "txt", "png", "jpg", "jpeg", "zip"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def validate_upload(file):
    import os

    from django.core.exceptions import ValidationError

    ext = action = ext_of(item=file.name)
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError("Unsupported file type.")
    if file.size and file.size > MAX_UPLOAD_SIZE:
        raise ValidationError("File is too large (max 10 MB).")


class Assignment(SchoolScopedModel):
    class_subject = models.ForeignKey(
        "academics.ClassSubject", on_delete=models.CASCADE, related_name="assignments"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField()
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    attachment = models.FileField(upload_to="assignments/", blank=True, null=True)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-due_date"]

    def __str__(self):
        return self.title


class Submission(BaseModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="submissions")
    content = models.TextField(blank=True)
    file = models.FileField(upload_to="submissions/", blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    graded_at = models.DateTimeField(null=True, blank=True)
    is_late = models.BooleanField(default=False)

    class Meta:
        unique_together = [("assignment", "student")]
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.student} -> {self.assignment}"
'''

FILES["assignments/serializers.py"] = '''from django.utils import timezone
from rest_framework import serializers

from .models import Assignment, Submission


class SubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = Submission
        fields = "__all__"
        read_only_fields = [
            "id", "created_at", "updated_at", "submitted_at", "score",
            "feedback", "graded_by", "graded_at", "is_late", "student",
        ]


class AssignmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="class_subject.subject.name", read_only=True)
    grade_level_name = serializers.CharField(source="class_subject.grade_level.name", read_only=True)
    submission_count = serializers.IntegerField(read_only=True)
    teacher_name = serializers.CharField(source="created_by.full_name", read_only=True, default=None)

    class Meta:
        model = Assignment
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "created_by"]

    def validate_max_score(self, value):
        if value <= 0:
            raise serializers.ValidationError("Maximum score must be positive.")
        return value


class GradeSubmissionSerializer(serializers.Serializer):
    score = serializers.DecimalField(max_digits=6, decimal_places=2)
    feedback = serializers.CharField(required=False, allow_blank=True)

    def validate_score(self, value):
        if value < 0:
            raise serializers.ValidationError("Score cannot be negative.")
        return value
'''

FILES["assignments/views.py"] = '''from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.mixins import SchoolScopedViewSetMixin
from core.permissions import IsAcademicStaff, IsAnyRole

from .models import Assignment, Submission
from .serializers import AssignmentSerializer, SubmissionSerializer


class AssignmentViewSet(SchoolScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Assignment.objects.select_related("class_subject__subject", "class_subject__grade_level", "created_by")
    serializer_class = AssignmentSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["class_subject", "is_published"]
    search_fields = ["title", "description"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAcademicStaff()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(
                is_published=True,
                class_subject__grade_level__enrollments__student__user=user,
            ).distinct()
        if user.user_type == "PARENT":
            return qs.filter(
                is_published=True,
                class_subject__grade_level__enrollments__student__guardian_links__guardian__user=user,
            ).distinct()
        return qs

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school, created_by=self.request.user)


class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["assignment", "student"]

    def get_queryset(self):
        from core.mixins import SchoolScopedQuerysetMixin

        qs = Submission.objects.select_related("student", "assignment")
        user = self.request.user
        school_id = user.school_id
        if school_id:
            qs = qs.filter(assignment__school_id=school_id)
        elif not (user.is_superuser or user.user_type == "SUPERADMIN"):
            return qs.none()
        if user.user_type == "STUDENT":
            return qs.filter(student__user=user)
        if user.user_type == "PARENT":
            return qs.filter(student__guardian_links__guardian__user=user).distinct()
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        assignment = serializer.validated_data["assignment"]
        if assignment.school_id != user.school_id and not user.is_superuser:
            raise PermissionError("Invalid assignment.")
        student = None
        if user.user_type == "STUDENT":
            student = getattr(user, "student_profile", None)
        if student is None:
            student = serializer.validated_data.get("student")
        if student is None:
            raise serializers_validation_error()
        is_late = assignment.due_date and timezone.now() > assignment.due_date
        serializer.save(student=student, is_late=bool(is_late))
'''

# Clean replacement for the malformed module above.
del FILES["assignments/views.py"]
FILES["assignments/views.py"] = '''from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.permissions import IsAcademicStaff, IsAnyRole

from .models import Assignment, Submission
from .serializers import AssignmentSerializer, SubmissionSerializer


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.select_related(
        "class_subject__subject", "class_subject__grade_level", "created_by"
    )
    serializer_class = AssignmentSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["class_subject", "is_published"]
    search_fields = ["title", "description"]
    pagination_class = __import__("core.pagination", fromlist=["StandardPagination"]).StandardPagination

    def get_school_id(self):
        user = self.request.user
        if user.is_superuser or user.user_type == "SUPERADMIN":
            return self.request.query_params.get("school")
        return user.school_id

    def get_queryset(self):
        qs = super().get_queryset()
        school_id = self.get_school_id()
        if school_id:
            qs = qs.filter(school_id=school_id)
        elif not (self.request.user.is_superuser or self.request.user.user_type == "SUPERADMIN"):
            return qs.none()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(
                is_published=True,
                class_subject__grade_level__enrollments__student__user=user,
            ).distinct()
        if user.user_type == "PARENT":
            return qs.filter(
                is_published=True,
                class_subject__grade_level__enrollments__student__guardian_links__guardian__user=user,
            ).distinct()
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAcademicStaff()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(school_id=self.request.user.school_id, created_by=self.request.user)


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.select_related("student", "assignment")
    serializer_class = SubmissionSerializer
    permission_classes = [IsAnyRole]
    filterset_fields = ["assignment", "student"]
    pagination_class = __import__("core.pagination", fromlist=["StandardPagination"]).StandardPagination

    def get_school_id(self):
        user = self.request.user
        if user.is_superuser or user.user_type == "SUPERADMIN":
            return self.request.query_params.get("school")
        return user.school_id

    def get_queryset(self):
        qs = super().get_queryset()
        school_id = self.get_school_id()
        if school_id:
            qs = qs.filter(assignment__school_id=school_id)
        elif not (self.request.user.is_superuser or self.request.user.user_type == "SUPERADMIN"):
            return qs.none()
        user = self.request.user
        if user.user_type == "STUDENT":
            return qs.filter(student__user=user)
        if user.user_type == "PARENT":
            return qs.filter(student__guardian_links__guardian__user=user).distinct()
        return qs

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy", "grade"):
            return [IsAcademicStaff()]
        return super().get_permissions()

    def perform_create(self, serializer):
        user = self.request.user
        assignment = serializer.validated_data["assignment"]
        if user.school_id and assignment.school_id != user.school_id:
            raise PermissionDenied("Assignment belongs to another school.")
        student = getattr(user, "student_profile", None)
        if student is None:
            student = serializer.validated_data.get("student")
        if student is None:
            raise serializers.ValidationError({"student": "A student is required."})
        is_late = bool(assignment.due_date and timezone.now() > assignment.due_date)
        serializer.save(student=student, is_late=is_late)

    @action(detail=True, methods=["post"], permission_classes=[IsAcademicStaff])
    def grade(self, request, pk=None):
        submission = self.get_object()
        score = request.data.get("score")
        if score is None:
            raise serializers.ValidationError({"score": "Score is required."})
        max_score = submission.assignment.max_score
        if float(score) > float(max_score):
            raise serializers.ValidationError({"score": f"Cannot exceed {max_score}."})
        submission.score = score
        submission.feedback = request.data.get("feedback", "")
        submission.graded_by = request.user
        submission.graded_at = timezone.now()
        submission.save(update_fields=["score", "feedback", "graded_by", "graded_at", "updated_at"])
        return Response(self.get_serializer(submission).data)
'''

FILES["assignments/urls.py"] = '''from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AssignmentViewSet, SubmissionViewSet

router = DefaultRouter()
router.register("assignments", AssignmentViewSet, basename="assignment")
router.register("submissions", SubmissionViewSet, basename="submission")

urlpatterns = [path("", include(router.urls))]
'''

FILES["assignments/apps.py"] = '''from django.apps import AppConfig


class AssignmentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "assignments"
'''

# ------------------------------------------------------------- communications
FILES["communications/models.py"] = '''from django.db import models

from core.models import BaseModel, SchoolScopedModel


class Announcement(SchoolScopedModel):
    AUDIENCE = [
        ("ALL", "Everyone"),
        ("STAFF", "Staff"),
        ("STUDENTS", "Students"),
        ("PARENTS", "Parents"),
        ("TEACHERS", "Teachers"),
    ]

    title = models.CharField(max_length=200)
    body = models.TextField()
    audience = models.CharField(max_length=16, choices=AUDIENCE, default="ALL")
    attachment = models.FileField(upload_to="announcements/", blank=True, null=True)
    author = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    grade_level = models.ForeignKey(
        "schools.GradeLevel", null=True, blank=True, on_delete=models.SET_NULL, related_name="announcements"
    )
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Notification(BaseModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self):
        return self.title


class Message(BaseModel):
    sender = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="sent_messages")
    recipient = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="received_messages")
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sender} -> {self.recipient}"
'''

FILES["communications/serializers.py"] = '''from rest_framework import serializers

from .models import Announcement, Message, Notification


class AnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True, default=None)

    class Meta:
        model = Announcement
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "author"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "user"]


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)
    recipient_name = serializers.CharField(source="recipient.full_name", read_only=True)

    class Meta:
        model = Message
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "sender"]
'''

FILES["communications/views.py"] = '''from django.utils import timezone
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
'''

FILES["communications/services.py"] = '''from .models import Notification


def notify_users(users, title, message="", link=""):
    """Create in-app notifications for a list of users."""
    objs = [
        Notification(user=user, title=title, message=message, link=link)
        for user in users
    ]
    return Notification.objects.bulk_create(objs)
'''

FILES["communications/urls.py"] = '''from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AnnouncementViewSet, MessageViewSet, NotificationViewSet

router = DefaultRouter()
router.register("announcements", AnnouncementViewSet, basename="announcement")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("messages", MessageViewSet, basename="message")

urlpatterns = [path("", include(router.urls))]
'''

FILES["communications/apps.py"] = '''from django.apps import AppConfig


class CommunicationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "communications"
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
