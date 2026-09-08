import uuid

from django.conf import settings
from django.db import models


def _temp_sale_number():
    """Temporary unique placeholder; overwritten with a readable number after first save."""
    return f"TEMP-{uuid.uuid4().hex[:12]}"


class Shift(models.Model):
    """
    Placeholder for cashier shift tracking.
    Open/close enforcement is not wired up until Phase 4 — this model just records shift data.
    """

    tenant_id = models.IntegerField(default=1, db_index=True)
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shifts",
    )
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    opening_float_paise = models.BigIntegerField(default=0)
    closing_cash_paise = models.BigIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    closing_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-opened_at"]

    def __str__(self):
        return f"Shift #{self.pk} — {self.cashier} @ {self.opened_at:%Y-%m-%d %H:%M}"


class Sale(models.Model):
    class Status(models.TextChoices):
        COMPLETED = "completed", "Completed"
        VOIDED = "voided", "Voided"

    tenant_id = models.IntegerField(default=1, db_index=True)
    sale_number = models.CharField(
        max_length=50, unique=True, db_index=True, default=_temp_sale_number
    )
    shift = models.ForeignKey(
        Shift, on_delete=models.PROTECT, null=True, blank=True, related_name="sales"
    )
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales"
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
    )
    class SaleType(models.TextChoices):
        SALE = "sale", "Sale"
        RETURN = "return", "Return"

    sale_type = models.CharField(max_length=10, choices=SaleType.choices, default=SaleType.SALE)
    return_of = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="returns",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)

    # All monetary values stored as integer paise (1 Rs = 100 paise)
    subtotal_paise = models.BigIntegerField(default=0)
    discount_paise = models.BigIntegerField(default=0)
    tax_paise = models.BigIntegerField(default=0)
    # The rate actually used on THIS bill, not whatever the shop setting says
    # today. Receipts printed "Tax (17%)" from the live setting, so changing
    # the rate silently rewrote the percentage on every past invoice — and a
    # tax entered as a flat amount printed a percentage that was simply wrong.
    # Null means the tax was entered as an amount, with no rate behind it.
    tax_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    # total_paise is the GOODS total — subtotal - discount + tax. It is the
    # revenue figure, and every report sums it, so its meaning must not change.
    total_paise = models.BigIntegerField(default=0)

    # Installation / labour charged on this bill and passed straight through to
    # the technician who did the work. The customer pays it, so it is part of
    # what is owed and what goes on the khata — but it is NOT the shop's
    # revenue and must never be added to total_paise. It is charged after tax:
    # labour is not taxed as goods.
    installation_paise = models.BigIntegerField(default=0)
    installation_note = models.CharField(
        max_length=200, blank=True,
        help_text="Who did the installation, or what the labour was for.",
    )

    # Sum of every non-credit tender. The khata remainder is
    # amount_due_paise - amount_paid_paise.
    amount_paid_paise = models.BigIntegerField(default=0)

    notes = models.TextField(blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="voided_sales",
    )
    voided_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Sale {self.sale_number}"

    @property
    def amount_due_paise(self) -> int:
        """What the customer actually has to pay: goods plus installation."""
        return self.total_paise + self.installation_paise

    @property
    def credit_paise(self) -> int:
        """How much of this sale went onto the customer's khata."""
        return max(0, self.amount_due_paise - self.amount_paid_paise)

    @property
    def installation_unpaid_paise(self) -> int:
        """
        The installation still owed on this bill.

        Money taken at the till settles the installation first, so the
        technician can be paid without waiting for the customer to clear the
        goods as well. Flip the two lines below to settle goods first.
        """
        return max(0, self.installation_paise - self.amount_paid_paise)

    @property
    def installation_collected_paise(self) -> int:
        """Installation money already in hand for this bill."""
        return min(self.installation_paise, self.amount_paid_paise)

    @property
    def primary_payment(self):
        """
        The one tender to show where only one fits — the largest non-credit
        tender, else the credit line. Reads from the prefetched list, so it
        costs nothing extra when the queryset used prefetch_related("payments").
        """
        pays = list(self.payments.all())
        if not pays:
            return None
        non_credit = [p for p in pays if p.method != Payment.Method.CREDIT]
        return max(non_credit or pays, key=lambda p: p.amount_paise)


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.PROTECT, related_name="sale_items"
    )
    qty = models.DecimalField(max_digits=10, decimal_places=3)
    unit_price_paise = models.BigIntegerField()
    discount_paise = models.BigIntegerField(default=0)
    subtotal_paise = models.BigIntegerField()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.qty} × {self.product.sku} @ {self.sale.sale_number}"


class SaleItemSerial(models.Model):
    sale_item = models.ForeignKey(SaleItem, on_delete=models.CASCADE, related_name="serials")
    serial = models.CharField(max_length=255, db_index=True)
    warranty_months = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            # A serial identifies one physical unit, so it can be sold exactly
            # once across the whole system. Scoping uniqueness to the sale_item
            # let the same camera be sold on unlimited separate invoices, which
            # defeats warranty lookup.
            models.UniqueConstraint(name="uniq_serial_global", fields=["serial"]),
        ]

    def __str__(self):
        return f"Serial {self.serial} for {self.sale_item}"


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        UPI = "upi", "UPI"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        CREDIT = "credit", "Khata / Credit"

    # A sale can be settled by several tenders — "Rs 2,000 cash now, the rest
    # on khata" is the normal pattern here, and a OneToOne could not express it.
    sale = models.ForeignKey(
        Sale, on_delete=models.CASCADE, related_name="payments", null=True, blank=True
    )
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.CASH)
    # What this tender actually settled. Every payment on a sale sums to
    # sale.total_paise, credit included.
    amount_paise = models.BigIntegerField(default=0)
    amount_tendered_paise = models.BigIntegerField()
    change_paise = models.BigIntegerField(default=0)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        # sale is nullable, so this must not assume one exists.
        ref = self.sale.sale_number if self.sale_id else "unlinked"
        return f"{self.method} payment — {ref}"


# Quotations live in their own module — they share nothing with Sale but the
# app they sit in, and keeping them apart is what stops them leaking into
# revenue. Imported here so Django discovers the models.
from .quotations import BusinessProfile, Quotation, QuotationItem  # noqa: E402,F401
