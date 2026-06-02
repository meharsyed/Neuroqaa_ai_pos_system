from django.db import models


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
