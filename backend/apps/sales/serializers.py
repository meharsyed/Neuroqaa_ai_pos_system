from decimal import Decimal

from rest_framework import serializers

from apps.catalog.models import Product

from .models import Payment, Sale, SaleItem


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
            "id", "product", "product_sku", "product_name", "product_unit",
            "qty", "unit_price_paise", "discount_paise", "subtotal_paise",
        ]


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    payment = PaymentSerializer(read_only=True)
    cashier_name = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            "id", "sale_number", "status",
            "cashier", "cashier_name",
            "subtotal_paise", "discount_paise", "tax_paise", "total_paise",
            "notes", "items", "payment",
            "voided_by", "voided_at", "created_at",
        ]

    def get_cashier_name(self, obj) -> str:
        return obj.cashier.get_full_name() or obj.cashier.email


# ── Input serializers ──────────────────────────────────────────────────────


class SaleItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    qty = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal("0.001"))
    unit_price_paise = serializers.IntegerField(min_value=0)
    discount_paise = serializers.IntegerField(min_value=0, default=0)

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError(
                f"Product {value} does not exist or is inactive."
            )
        return value


class CreateSaleSerializer(serializers.Serializer):
    items = SaleItemInputSerializer(many=True)
    payment_method = serializers.ChoiceField(choices=Payment.Method.choices, default="cash")
    amount_tendered_paise = serializers.IntegerField(min_value=0)
    discount_paise = serializers.IntegerField(min_value=0, default=0)
    notes = serializers.CharField(max_length=500, allow_blank=True, default="")

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("A sale must have at least one item.")
        return value