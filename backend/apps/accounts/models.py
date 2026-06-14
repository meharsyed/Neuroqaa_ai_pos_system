from django.contrib.auth.models import AbstractUser
from django.db import models
from simple_history.models import HistoricalRecords


class User(AbstractUser):
    """
    Custom user model — extended from AbstractUser so we keep all built-in
    auth machinery (password hashing, permissions, admin integration) while
    having full control over the schema from day one.
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MANAGER = "manager", "Manager"
        CASHIER = "cashier", "Cashier"
        STOCK_CLERK = "stock_clerk", "Stock Clerk"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CASHIER)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}>"

    @property
    def full_name(self):
        return self.get_full_name() or self.email


class ActivityLog(models.Model):
    """Security and operational audit trail — visible to owner/manager only."""

    class Action(models.TextChoices):
        LOGIN          = "login",           "User Login"
        LOGOUT         = "logout",          "User Logout"
        SALE_CREATED   = "sale_created",    "Sale Created"
        SALE_VOIDED    = "sale_voided",     "Sale Voided"
        RETURN_CREATED = "return_created",  "Return Processed"
        STOCK_IN       = "stock_in",        "Stock Added"
        SETTING_CHANGED = "setting_changed", "Setting Changed"
        SHIFT_OPENED   = "shift_opened",    "Shift Opened"
        SHIFT_CLOSED   = "shift_closed",    "Shift Closed"
        CUSTOMER_CREATED = "customer_created", "Customer Created"

    user       = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="activity_logs",
    )
    action     = models.CharField(max_length=30, choices=Action.choices, db_index=True)
    details    = models.JSONField(default=dict)
    ip_address = models.CharField(max_length=45, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    tenant_id  = models.IntegerField(default=1, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        who = self.user.email if self.user else "system"
        return f"{self.get_action_display()} by {who} at {self.created_at:%Y-%m-%d %H:%M}"
