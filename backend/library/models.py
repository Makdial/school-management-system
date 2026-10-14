from datetime import timedelta

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
