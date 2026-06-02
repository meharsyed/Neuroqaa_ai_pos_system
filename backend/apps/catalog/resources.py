from decimal import Decimal, InvalidOperation

from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget, Widget

from .models import Category, Inventory, Product


class DecimalToIntPaiseWidget(Widget):
    """
    CSV column stores rupees as a decimal string (e.g., "350.00").
    Widget converts to integer paise for storage (35000).
    On export, renders paise back to rupees string.
    """

    def clean(self, value, row=None, **kwargs):
        if not value and value != 0:
            return 0
        try:
            return int(Decimal(str(value).strip()) * 100)
        except InvalidOperation:
            raise ValueError(f"Invalid price value: {value!r}") from None

    def render(self, value, obj=None):
        if value is None:
            return "0.00"
        return f"{Decimal(value) / 100:.2f}"


class ProductResource(resources.ModelResource):
    """
    Supports bulk CSV import with columns:
        name, sku, barcode, category, unit,
        cost_price (Rs), sell_price (Rs),
        low_stock_threshold, is_active

    cost_price and sell_price are in rupees; stored as paise internally.
    category must match an existing Category.name (case-sensitive).
    sku is the natural key — re-importing updates existing products.
    """

    category = fields.Field(
        column_name="category",
        attribute="category",
        widget=ForeignKeyWidget(Category, "name"),
    )
    cost_price_paise = fields.Field(
        column_name="cost_price",
        attribute="cost_price_paise",
        widget=DecimalToIntPaiseWidget(),
    )
    sell_price_paise = fields.Field(
        column_name="sell_price",
        attribute="sell_price_paise",
        widget=DecimalToIntPaiseWidget(),
    )

    class Meta:
        model = Product
        # "id" is intentionally omitted — sku is the natural import key.
        fields = (
            "name",
            "sku",
            "barcode",
            "category",
            "unit",
            "cost_price_paise",
            "sell_price_paise",
            "low_stock_threshold",
            "is_active",
        )
        import_id_fields = ("sku",)
        skip_unchanged = True
        report_skipped = False
        exclude = ("tenant_id", "description", "history")

    def after_save_instance(self, instance, row, **kwargs):
        """
        Create an Inventory row for every new product automatically.
        django-import-export 4.x passes (instance, row, is_create=, dry_run=, ...).
        """
        if not kwargs.get("dry_run", False):
            Inventory.objects.get_or_create(
                product=instance,
                defaults={"tenant_id": instance.tenant_id},
            )
