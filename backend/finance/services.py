"""Financial operations.

All money is handled with :class:`decimal.Decimal`; floats are never used.
Payments are recorded inside a transaction and invoices are locked with
``select_for_update`` so balances cannot drift under concurrency.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum
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
        payment.notes = (payment.notes + "\n" + reason).strip()
    payment.save(update_fields=["status", "notes", "updated_at"])
    return payment


def collection_summary(school, session=None, start=None, end=None):
    """Aggregate collections and outstanding balances for one school.

    Money is aggregated in the database as :class:`~decimal.Decimal` and
    quantised with ``money()``; floats are never used.
    """
    payments = Payment.objects.filter(school=school, status="COMPLETED")
    if session:
        payments = payments.filter(invoice__session_id=session)
    if start:
        payments = payments.filter(paid_at__date__gte=start)
    if end:
        payments = payments.filter(paid_at__date__lte=end)

    invoices = Invoice.objects.filter(school=school).exclude(status="CANCELLED")
    if session:
        invoices = invoices.filter(session_id=session)

    collected = money(payments.aggregate(t=Sum("amount"))["t"] or 0)
    invoiced = money(invoices.aggregate(t=Sum("total_amount"))["t"] or 0)
    outstanding = money(invoices.aggregate(t=Sum("balance"))["t"] or 0)

    return {
        "total_collected": collected,
        "payments_count": payments.count(),
        "total_invoiced": invoiced,
        "outstanding": outstanding,
        "by_method": [
            {"method": row["method"], "total": money(row["total"] or 0), "count": row["count"]}
            for row in payments.values("method").annotate(total=Sum("amount"), count=Count("id"))
        ],
    }
