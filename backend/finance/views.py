from django.utils import timezone
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
