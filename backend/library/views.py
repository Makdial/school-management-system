from rest_framework import viewsets
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
