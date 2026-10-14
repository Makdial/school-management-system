from django.urls import include, path
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
