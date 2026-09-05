from django.db import models
from django.conf import settings


class Customer(models.Model):
    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"
        OTHER = "O", "Other / Unspecified"

    tenant_id = models.IntegerField(default=1, db_index=True)
    name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices, default=Gender.OTHER)
    notes = models.TextField(blank=True)
    outstanding_paise = models.BigIntegerField(default=0, db_index=True)  # Khata / credit balance
    # None = fall back to the shop-wide default. 0 = no credit allowed at all.
    credit_limit_paise = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.display_name

    @property
    def display_name(self) -> str:
        if self.name and self.phone:
            return f"{self.name} ({self.phone})"
        return self.name or self.phone or f"Customer #{self.pk}"


class PaymentReceived(models.Model):
    """Track payments received against customer credit (Khata)"""

    tenant_id = models.IntegerField(default=1, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="payments_received")
    amount_paise = models.BigIntegerField()  # Amount paid towards outstanding balance
    received_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-received_date"]

    def __str__(self):
        return f"Payment {self.id}: {self.customer.display_name} — {self.amount_paise} paise"


class CreditLedgerEntry(models.Model):
    """
    Append-only record of every movement in a customer's khata balance.

    `Customer.outstanding_paise` is a cache of this ledger. Before it existed a
    wrong balance could not be explained or repaired, and voiding a credit sale
    left the customer owing money forever. Never write it directly — go through
    apps.customers.services.post_credit_entry().
    """

    class Kind(models.TextChoices):
        SALE = "sale", "Credit sale"
        PAYMENT = "payment", "Payment received"
        RETURN = "return", "Return"
        VOID = "void", "Sale voided"
        ADJUSTMENT = "adjustment", "Manual adjustment"
        OPENING = "opening", "Opening balance"

    tenant_id = models.IntegerField(default=1, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="ledger")
    kind = models.CharField(max_length=20, choices=Kind.choices)

    sale = models.ForeignKey(
        "sales.Sale", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="credit_entries",
    )
    payment = models.ForeignKey(
        PaymentReceived, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ledger_entries",
    )

    # Positive = customer owes more. Negative = customer owes less.
    delta_paise = models.BigIntegerField()
    balance_after_paise = models.BigIntegerField()

    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="credit_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["customer", "-created_at"])]
        verbose_name_plural = "credit ledger entries"

    def __str__(self):
        sign = "+" if self.delta_paise >= 0 else ""
        return f"{self.customer_id} {self.kind} {sign}{self.delta_paise}"

    def save(self, *args, **kwargs):
        # Append-only, same contract as catalog.StockMovement.
        if self.pk is not None:
            raise ValueError(
                "CreditLedgerEntry is append-only. Post a compensating entry instead."
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("CreditLedgerEntry is append-only and cannot be deleted.")
