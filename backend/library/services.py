from datetime import timedelta
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
