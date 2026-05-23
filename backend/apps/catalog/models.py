from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from simple_history.models import HistoricalRecords


class Category(models.Model):
    tenant_id = models.IntegerField(default=1, db_index=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    class Unit(models.TextChoices):
        PCS = "pcs", "Pieces"
        KG = "kg", "Kilograms"
        LITRE = "litre", "Litres"
        METRE = "metre", "Metres"
        SQ_METRE = "sq_metre", "Square Metres"
        BOX = "box", "Box"
        DOZEN = "dozen", "Dozen"
        BUNDLE = "bundle", "Bundle"

    tenant_id = models.IntegerField(default=1, db_index=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=300)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    barcode = models.CharField(max_length=100, blank=True, db_index=True)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.PCS)

    # Prices stored as integer paise (1 Rs = 100 paise). Never use FloatField for money.
    cost_price_paise = models.BigIntegerField(default=0)
    sell_price_paise = models.BigIntegerField(default=0)

    low_stock_threshold = models.DecimalField(
        max_digits=10, decimal_places=3, default=Decimal("0.000")
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()  # audit trail for price changes

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.sku} — {self.name}"

    @property
    def margin_paise(self) -> int:
        return self.sell_price_paise - self.cost_price_paise


class Inventory(models.Model):
    tenant_id = models.IntegerField(default=1, db_index=True)
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="inventory"
    )
    # DecimalField supports fractional units (kg, litres); 3 decimal places.
    stock_qty = models.DecimalField(
        max_digits=10, decimal_places=3, default=Decimal("0.000")
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Inventories"

    def __str__(self) -> str:
        return f"{self.product.sku}: {self.stock_qty} {self.product.unit}"

    @property
    def is_low_stock(self) -> bool:
        return (
            self.product.low_stock_threshold > 0
            and self.stock_qty <= self.product.low_stock_threshold
        )


class StockMovement(models.Model):
    """
    Append-only ledger of every inventory change.
    Never update or delete rows — use apply_stock_movement() in services.py.
    """

    class MovementType(models.TextChoices):
        OPENING = "opening", "Opening Stock"
        STOCK_IN = "stock_in", "Stock In"
        SALE = "sale", "Sale"
        RETURN = "return", "Return"
        ADJUSTMENT = "adjustment", "Adjustment"
        DAMAGE = "damage", "Damage"

    tenant_id = models.IntegerField(default=1, db_index=True)
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="movements"
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    qty_change = models.DecimalField(max_digits=10, decimal_places=3)
    qty_after = models.DecimalField(max_digits=10, decimal_places=3)
    # Cost price snapshot at the time of the movement (optional — used for stock-in valuation)
    cost_price_paise = models.BigIntegerField(null=True, blank=True)
    reference = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        sign = "+" if self.qty_change >= 0 else ""
        return f"{self.movement_type} {sign}{self.qty_change} × {self.product.sku}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("StockMovement is append-only — updates are forbidden.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("StockMovement is append-only — deletes are forbidden.")