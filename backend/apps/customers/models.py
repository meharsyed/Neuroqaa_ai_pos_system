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
