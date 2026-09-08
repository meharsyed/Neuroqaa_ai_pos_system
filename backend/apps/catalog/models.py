from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from simple_history.models import HistoricalRecords

# A phone photo of a product easily runs 4-6MB — capped well above that so a
# real product photo is never rejected, but a multi-hundred-MB upload (by
# accident or on purpose) can't fill the disk. Format is checked by the
# browser-supplied content type here and, independently, by Pillow itself —
# DRF's ImageField only accepts a file it can actually decode as one of these,
# so a renamed non-image file is rejected regardless of what this check says.
MAX_PRODUCT_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_PRODUCT_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}


def validate_product_image(file) -> None:
    if file.size > MAX_PRODUCT_IMAGE_BYTES:
        limit_mb = MAX_PRODUCT_IMAGE_BYTES // (1024 * 1024)
        raise ValidationError(f"Image is too large — please use one under {limit_mb} MB.")
    content_type = getattr(file, "content_type", None)
    if content_type and content_type not in ALLOWED_PRODUCT_IMAGE_TYPES:
        raise ValidationError(
            "Unsupported image format — please use JPEG, PNG, WEBP or HEIC/HEIF."
        )


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
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
        validators=[validate_product_image],
    )
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
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="inventory")
    # DecimalField supports fractional units (kg, litres); 3 decimal places.
    stock_qty = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0.000"))
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


class Supplier(models.Model):
    """
    A vendor/seller a shop restocks from.

    Deliberately plain — see the design note on StockMovement.supplier below
    for why this doesn't carry a running balance or per-product pricing of
    its own; that history lives on the movements, not here.
    """

    tenant_id = models.IntegerField(default=1, db_index=True)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


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
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    # Only ever set for STOCK_IN movements — who a batch of stock was bought
    # from. PROTECT so a supplier with purchase history can't be deleted out
    # from under it (deactivate via is_active instead, same convention as
    # archiving a Product).
    supplier = models.ForeignKey(
        "Supplier", on_delete=models.PROTECT, null=True, blank=True, related_name="stock_movements"
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
