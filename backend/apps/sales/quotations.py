"""
Quotations.

Deliberately NOT a Sale with a status flag. A quotation must not touch stock,
must not appear in revenue, must not take a SALE- number, and must be able to
list things the shop does not stock at all. Bolting a flag onto Sale would mean
auditing every query in the system for "and not a quotation" — the same trap as
folding installation charges into total_paise.
"""

from django.conf import settings
from django.db import models


def _temp_number():
    from uuid import uuid4

    return f"TEMP-{uuid4().hex[:12]}"


class BusinessProfile(models.Model):
    """
    A letterhead to quote under.

    The client asked to change the shop name and details per quotation. Free
    text on every quotation means retyping an address wrong on a tender
    document and no record of which identity a quotation went out under, so
    the identities are defined once and picked from a list.
    """

    tenant_id = models.IntegerField(default=1, db_index=True)
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    tax_number = models.CharField(max_length=100, blank=True, help_text="NTN / STRN")
    footer = models.TextField(blank=True, help_text="Printed under the totals.")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Exactly one default, or the quotation form has nothing to preselect.
        if self.is_default:
            BusinessProfile.objects.exclude(pk=self.pk).filter(is_default=True).update(
                is_default=False
            )


class Quotation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"

    tenant_id = models.IntegerField(default=1, db_index=True)
    number = models.CharField(max_length=50, unique=True, db_index=True, default=_temp_number)
    # A negotiation is one thread, not a new document each time.
    revision = models.PositiveIntegerField(default=1)

    profile = models.ForeignKey(
        BusinessProfile, on_delete=models.PROTECT, null=True, blank=True,
        related_name="quotations",
    )
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="quotations",
    )
    # A quotation often goes to a company that is not yet a customer.
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=50, blank=True)
    customer_address = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    valid_days = models.PositiveIntegerField(
        default=15, help_text="Printed on the quotation. Stops a January price being held to in March."
    )

    subtotal_paise = models.BigIntegerField(default=0)
    discount_paise = models.BigIntegerField(default=0)
    tax_paise = models.BigIntegerField(default=0)
    tax_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    installation_paise = models.BigIntegerField(default=0)
    installation_note = models.CharField(max_length=200, blank=True)
    total_paise = models.BigIntegerField(default=0)

    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="quotations"
    )
    # Set when a quotation is turned into a real sale, so the shop can see
    # what its quoting actually converts.
    converted_sale = models.ForeignKey(
        "sales.Sale", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="from_quotation",
    )
    converted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.display_number

    @property
    def display_number(self) -> str:
        return f"{self.number} rev {self.revision}" if self.revision > 1 else self.number

    @property
    def valid_until(self):
        from datetime import timedelta

        if not self.created_at:
            return None
        return (self.created_at + timedelta(days=self.valid_days)).date()

    @property
    def is_expired(self) -> bool:
        from django.utils import timezone

        until = self.valid_until
        return bool(until and until < timezone.localdate())

    def recalculate(self) -> None:
        """Totals from the lines. Same arithmetic as a sale, same order."""
        from decimal import ROUND_HALF_UP, Decimal

        self.subtotal_paise = sum(i.line_total_paise for i in self.items.all())
        taxable = self.subtotal_paise - self.discount_paise
        if self.tax_pct is not None:
            self.tax_paise = int(
                (Decimal(taxable) * Decimal(self.tax_pct) / 100).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
        self.total_paise = taxable + self.tax_paise + self.installation_paise


class QuotationItem(models.Model):
    """
    A line on a quotation.

    `product` is nullable on purpose: a quotation routinely lists work the shop
    does not stock — "Cat-6 cable, 90m, supplied and laid" — and being unable
    to write that line is what sends people back to Word.
    """

    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="quotation_items",
    )
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=255, blank=True)

    qty = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    unit = models.CharField(max_length=20, blank=True)
    unit_price_paise = models.BigIntegerField(default=0)
    discount_paise = models.BigIntegerField(default=0)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.name} × {self.qty}"

    @property
    def line_total_paise(self) -> int:
        return int(self.qty * self.unit_price_paise) - self.discount_paise

    @property
    def is_off_catalogue(self) -> bool:
        return self.product_id is None
