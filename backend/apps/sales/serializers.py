from decimal import Decimal

from rest_framework import serializers

from apps.catalog.models import Product

from .models import Payment, Sale, SaleItem, Shift


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["method", "amount_tendered_paise", "change_paise"]


class SaleItemSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_unit = serializers.CharField(source="product.unit", read_only=True)

    class Meta:
        model = SaleItem
        fields = [
            "id",
            "product",
            "product_sku",
            "product_name",
            "product_unit",
            "qty",
            "unit_price_paise",
            "discount_paise",
            "subtotal_paise",
        ]


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    payment = PaymentSerializer(read_only=True)
    cashier_name = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            "id",
            "sale_number",
            "sale_type",
            "status",
            "cashier",
            "cashier_name",
            "customer",
            "customer_name",
            "customer_phone",
            "return_of",
            "subtotal_paise",
            "discount_paise",
            "tax_paise",
            "total_paise",
            "notes",
            "items",
            "payment",
            "voided_by",
            "voided_at",
            "created_at",
        ]

    def get_cashier_name(self, obj) -> str:
        return obj.cashier.get_full_name() or obj.cashier.email

    def get_customer_name(self, obj) -> str | None:
        return obj.customer.name if obj.customer else None

    def get_customer_phone(self, obj) -> str | None:
        return obj.customer.phone if obj.customer else None


# ── Input serializers ──────────────────────────────────────────────────────


class SaleItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    qty = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal("0.001"))
    unit_price_paise = serializers.IntegerField(min_value=0)
    discount_paise = serializers.IntegerField(min_value=0, default=0)

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError(f"Product {value} does not exist or is inactive.")
        return value


class CreateSaleSerializer(serializers.Serializer):
    items = SaleItemInputSerializer(many=True)
    payment_method = serializers.ChoiceField(choices=Payment.Method.choices, default="cash")
    amount_tendered_paise = serializers.IntegerField(min_value=0)
    discount_paise = serializers.IntegerField(min_value=0, default=0)
    notes = serializers.CharField(max_length=500, allow_blank=True, default="")

    tax_paise  = serializers.IntegerField(min_value=0, default=0)
    customer_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("A sale must have at least one item.")
        return value


# ── Return serializers ────────────────────────────────────────────────────────


class ReturnItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    qty = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal("0.001"))


class CreateReturnSerializer(serializers.Serializer):
    items = ReturnItemSerializer(many=True)
    notes = serializers.CharField(max_length=500, allow_blank=True, default="")

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item must be returned.")
        return value


# ── Shift serializers ──────────────────────────────────────────────────────────


class ShiftSerializer(serializers.ModelSerializer):
    cashier_name = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()

    class Meta:
        model = Shift
        fields = [
            "id",
            "cashier",
            "cashier_name",
            "opened_at",
            "closed_at",
            "opening_float_paise",
            "closing_cash_paise",
            "closing_notes",
            "notes",
            "is_open",
        ]

    def get_cashier_name(self, obj) -> str:
        return obj.cashier.get_full_name() or obj.cashier.email

    def get_is_open(self, obj) -> bool:
        return obj.closed_at is None


class OpenShiftSerializer(serializers.Serializer):
    opening_float_paise = serializers.IntegerField(min_value=0, default=0)
    notes = serializers.CharField(max_length=500, allow_blank=True, default="")


class CloseShiftSerializer(serializers.Serializer):
    closing_cash_paise = serializers.IntegerField(min_value=0)
    closing_notes = serializers.CharField(max_length=500, allow_blank=True, default="")
