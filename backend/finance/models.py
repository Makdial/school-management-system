from django.db import models

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
