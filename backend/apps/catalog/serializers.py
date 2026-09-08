from decimal import Decimal

from rest_framework import serializers

from apps.accounts.permissions import can_see_cost_prices

from .models import Category, Inventory, Product, StockMovement, Supplier
from .money import Money


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "is_active"]
        read_only_fields = ["id"]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "id",
            "name",
            "contact_person",
            "phone",
            "email",
            "address",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    cost_price = serializers.SerializerMethodField()
    sell_price = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    stock_qty = serializers.DecimalField(
        source="inventory.stock_qty",
        max_digits=10,
        decimal_places=3,
        read_only=True,
        default=Decimal("0.000"),
    )
    is_low_stock = serializers.BooleanField(
        source="inventory.is_low_stock", read_only=True, default=False
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "barcode",
            "category",
            "category_name",
            "unit",
            "description",
            "cost_price_paise",
            "sell_price_paise",
            "cost_price",
            "sell_price",
            "low_stock_threshold",
            "is_active",
            "image",
            "image_url",
            "stock_qty",
            "is_low_stock",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "image_url", "created_at", "updated_at"]

    def to_representation(self, instance):
        """
        Strip cost and margin for anyone below manager.

        Knowing what a DVR costs tells a cashier exactly how far a price can be
        discounted before anyone notices — so the counter simply never receives
        the number.
        """
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is not None and not can_see_cost_prices(request.user):
            data.pop("cost_price_paise", None)
            data.pop("cost_price", None)
        return data

    def get_cost_price(self, obj) -> str:
        return str(Money(obj.cost_price_paise))

    def get_sell_price(self, obj) -> str:
        return str(Money(obj.sell_price_paise))

    def get_image_url(self, obj) -> str | None:
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def create(self, validated_data):
        product = super().create(validated_data)
        Inventory.objects.create(product=product, tenant_id=product.tenant_id)
        return product


class InventorySerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    unit = serializers.CharField(source="product.unit", read_only=True)
    low_stock_threshold = serializers.DecimalField(
        source="product.low_stock_threshold",
        max_digits=10,
        decimal_places=3,
        read_only=True,
    )
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Inventory
        fields = [
            "id",
            "product",
            "sku",
            "product_name",
            "unit",
            "stock_qty",
            "low_stock_threshold",
            "is_low_stock",
            "updated_at",
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "product",
            "product_sku",
            "product_name",
            "supplier",
            "supplier_name",
            "movement_type",
            "qty_change",
            "qty_after",
            "cost_price_paise",
            "reference",
            "notes",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = fields  # append-only: no writes via API

    def get_created_by_name(self, obj) -> str | None:
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None


class StockInSerializer(serializers.Serializer):
    """Input serializer for the stock-in action. Validates before hitting services.py."""

    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))
    qty = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal("0.001"))
    cost_price_paise = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    # Optional — who this batch was bought from. Ignoring it keeps working
    # exactly as before; the field only ever gets attached to a STOCK_IN
    # movement (see services.apply_stock_movement).
    supplier = serializers.PrimaryKeyRelatedField(
        queryset=Supplier.objects.filter(is_active=True), required=False, allow_null=True
    )
    reference = serializers.CharField(max_length=200, required=False, default="", allow_blank=True)
    notes = serializers.CharField(required=False, default="", allow_blank=True)
