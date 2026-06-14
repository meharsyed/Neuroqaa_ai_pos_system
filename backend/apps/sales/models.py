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
    total_paise = models.BigIntegerField(default=0)

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


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        UPI = "upi", "UPI"

    sale = models.OneToOneField(Sale, on_delete=models.CASCADE, related_name="payment")
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.CASH)
    amount_tendered_paise = models.BigIntegerField()
    change_paise = models.BigIntegerField(default=0)

    def __str__(self):
        return f"{self.method} payment — {self.sale.sale_number}"
