"""Small cross cutting helpers used by several domain services."""
from datetime import date

from django.utils import timezone


def today():
    return timezone.localdate()


def money(value):
    """Quantise a value to two decimal places without floating point drift."""
    from decimal import Decimal, ROUND_HALF_UP

    return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def generate_sequence_number(prefix, model, field, school=None, width=5):
    """Create a human friendly sequential document number.

    Wrapped by the caller in a transaction so concurrent inserts do not
    collide on the unique constraint.
    """
    year = date.today().year
    base = f"{prefix}-{year}-"
    qs = model.objects.filter(**{f"{field}__startswith": base})
    if school is not None:
        qs = qs.filter(school=school)
    last = qs.order_by(f"-{field}").values_list(field, flat=True).first()
    tail = 1
    if last:
        try:
            tail = int(str(last).rsplit("-", 1)[-1]) + 1
        except (ValueError, IndexError):
            tail = 1
    return f"{base}{tail:0{width}d}"


def percent(part, whole):
    if not whole:
        return 0.0
    return round((float(part) / float(whole)) * 100, 2)
