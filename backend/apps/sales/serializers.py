from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.catalog.models import Product

from .models import Payment, Sale, SaleItem, SaleItemSerial, Shift


class SaleItemSerialSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItemSerial
        fields = ["id", "serial", "warranty_months"]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "method", "amount_paise", "amount_tendered_paise", "change_paise"]


class SaleItemSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_unit = serializers.CharField(source="product.unit", read_only=True)
    serials = SaleItemSerialSerializer(many=True, read_only=True)

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
            "serials",
        ]


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    # A bill can be settled by several tenders now. `payment` is kept as the
    # primary one — the largest non-credit tender — so every screen that showed
    # a single method still works; `payments` is the full truth.
    payment = serializers.SerializerMethodField()
    credit_paise = serializers.SerializerMethodField()
    amount_due_paise = serializers.SerializerMethodField()
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
            "tax_pct",
            "total_paise",
            "installation_paise",
            "installation_note",
            "amount_due_paise",
            "notes",
            "items",
            "payment",
            "payments",
            "amount_paid_paise",
            "credit_paise",
            "voided_by",
            "voided_at",
            "created_at",
        ]

    @extend_schema_field(PaymentSerializer(allow_null=True))
    def get_payment(self, obj):
        primary = obj.primary_payment
        return PaymentSerializer(primary).data if primary else None

    def get_credit_paise(self, obj) -> int:
        return obj.credit_paise

    def get_amount_due_paise(self, obj) -> int:
        """Goods plus installation — what the customer actually pays."""
        return obj.amount_due_paise

    def get_cashier_name(self, obj) -> str:
        return obj.cashier.get_full_name() or obj.cashier.email

    def get_customer_name(self, obj) -> str | None:
        return obj.customer.name if obj.customer else None

    def get_customer_phone(self, obj) -> str | None:
        return obj.customer.phone if obj.customer else None


# ── Input serializers ──────────────────────────────────────────────────────


class SaleItemSerialInputSerializer(serializers.Serializer):
    serial = serializers.CharField(max_length=255)
    warranty_months = serializers.IntegerField(required=False, allow_null=True)


class SaleItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    qty = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal("0.001"))
    unit_price_paise = serializers.IntegerField(min_value=0)
    discount_paise = serializers.IntegerField(min_value=0, default=0)
    serials = SaleItemSerialInputSerializer(many=True, required=False, default=list)

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError(f"Product {value} does not exist or is inactive.")
        return value


class TenderInputSerializer(serializers.Serializer):
    """One way the cashier settled part of the bill."""

    method = serializers.ChoiceField(choices=Payment.Method.choices)
    amount_paise = serializers.IntegerField(min_value=1)
    # Only meaningful for cash: what the customer actually handed over, so
    # change can be worked out. Defaults to the amount for everything else.
    amount_tendered_paise = serializers.IntegerField(min_value=0, required=False)

    def validate_method(self, value):
        if value == Payment.Method.CREDIT:
            raise serializers.ValidationError(
                "Khata is not a tender — whatever is left unpaid goes on khata "
                "automatically."
            )
        return value


class CreateSaleSerializer(serializers.Serializer):
    items = SaleItemInputSerializer(many=True)
    payment_method = serializers.ChoiceField(choices=Payment.Method.choices, default="cash")
    amount_tendered_paise = serializers.IntegerField(min_value=0, required=False, default=0)
    # When present this replaces payment_method/amount_tendered_paise entirely:
    # the bill is settled by these tenders and any shortfall goes on khata.
    tenders = TenderInputSerializer(many=True, required=False)
    discount_paise = serializers.IntegerField(min_value=0, default=0)
    notes = serializers.CharField(max_length=500, allow_blank=True, default="")

    # Give a rate and the server computes the amount; give an amount and it is
    # taken as a flat figure. Give neither and the shop's default rate applies.
    tax_pct = serializers.DecimalField(
        max_digits=5, decimal_places=2,
        min_value=Decimal("0"), max_value=Decimal("100"),
        required=False, allow_null=True,
    )
    tax_paise = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    # Labour charged on this bill and paid on to the technician. Part of what
    # the customer owes, never part of the shop's revenue.
    installation_paise = serializers.IntegerField(min_value=0, default=0)
    installation_note = serializers.CharField(
        max_length=200, allow_blank=True, default="", required=False
    )
    customer_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("A sale must have at least one item.")
        return value

    def validate(self, attrs):
        # A credit sale with no customer completes, deducts stock and books
        # revenue while billing nobody. Refuse it. With explicit tenders the
        # shortfall is only known once the cart is priced, so create_sale
        # raises there instead; this catches the unambiguous legacy case.
        tenders = attrs.get("tenders")
        if not tenders and attrs.get("payment_method") == "credit" and not attrs.get("customer_id"):
            raise serializers.ValidationError(
                {"customer_id": "A credit (khata) sale requires a customer."}
            )
        if tenders is not None and len(tenders) == 0:
            raise serializers.ValidationError(
                {"tenders": "Give at least one tender, or leave this out entirely."}
            )
        return attrs


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
