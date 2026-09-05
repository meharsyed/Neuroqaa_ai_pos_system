from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import serializers

from .models import CreditLedgerEntry, Customer, PaymentReceived


class CustomerSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    total_sales = serializers.SerializerMethodField()
    total_revenue_paise = serializers.SerializerMethodField()
    days_overdue = serializers.SerializerMethodField()
    effective_credit_limit_paise = serializers.SerializerMethodField()
    available_credit_paise = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "phone",
            "gender",
            "notes",
            "display_name",
            "outstanding_paise",
            "credit_limit_paise",
            "effective_credit_limit_paise",
            "available_credit_paise",
            "days_overdue",
            "total_sales",
            "total_revenue_paise",
            "created_at",
        ]

    # These three used to fire a query each, per customer, on a list endpoint
    # that had no pagination. The viewset now annotates them; the fallbacks
    # only run for a single serialized instance.
    def get_total_sales(self, obj) -> int:
        cached = getattr(obj, "sales_count", None)
        if cached is not None:
            return cached
        return obj.sales.filter(status="completed").count()

    def get_total_revenue_paise(self, obj) -> int:
        cached = getattr(obj, "sales_revenue", None)
        if cached is not None:
            return cached
        return obj.sales.filter(status="completed").aggregate(
            total=Coalesce(Sum("total_paise"), 0)
        )["total"]

    def validate_credit_limit_paise(self, value):
        # Raising a customer's ceiling is a money decision, not a counter one.
        request = self.context.get("request")
        role = getattr(getattr(request, "user", None), "role", None)
        if role not in ("owner", "manager"):
            raise serializers.ValidationError(
                "Only an owner or manager can change a credit limit."
            )
        if value is not None and value < 0:
            raise serializers.ValidationError("A credit limit cannot be negative.")
        return value

    def get_effective_credit_limit_paise(self, obj) -> int | None:
        """The limit actually in force. None means unlimited."""
        from .services import effective_credit_limit

        return effective_credit_limit(obj)

    def get_available_credit_paise(self, obj) -> int | None:
        """How much more may be put on khata. None means unlimited."""
        from .services import available_credit

        return available_credit(obj)

    def get_days_overdue(self, obj) -> int | None:
        """Days since the oldest credit charge that is still outstanding."""
        if obj.outstanding_paise <= 0:
            return None
        first = getattr(obj, "first_credit_at", None)
        if first is None:
            entry = (
                obj.ledger.filter(kind=CreditLedgerEntry.Kind.SALE)
                .order_by("created_at")
                .first()
            )
            first = entry.created_at if entry else None
        if first is None:
            # Pre-ledger balances have an opening entry instead.
            opening = obj.ledger.order_by("created_at").first()
            first = opening.created_at if opening else None
        if first is None:
            return None
        return max(0, (timezone.now() - first).days)


class CreditLedgerEntrySerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    sale_number = serializers.CharField(source="sale.sale_number", read_only=True, default=None)

    class Meta:
        model = CreditLedgerEntry
        fields = [
            "id",
            "kind",
            "kind_display",
            "delta_paise",
            "balance_after_paise",
            "note",
            "sale",
            "sale_number",
            "payment",
            "created_by_name",
            "created_at",
        ]

    def get_created_by_name(self, obj) -> str:
        if not obj.created_by:
            return "—"
        return obj.created_by.get_full_name() or obj.created_by.email


class PaymentReceivedSerializer(serializers.ModelSerializer):
    received_by_name = serializers.CharField(source="received_by.get_full_name", read_only=True)

    class Meta:
        model = PaymentReceived
        fields = [
            "id",
            "customer",
            "amount_paise",
            "received_date",
            "notes",
            "received_by",
            "received_by_name",
        ]
        read_only_fields = ["id", "received_date", "received_by", "received_by_name"]


class CreatePaymentReceivedSerializer(serializers.Serializer):
    """Recording a payment received against a customer's khata."""

    customer_id = serializers.IntegerField()
    amount_paise = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate(self, attrs):
        # The old code clamped an overpayment with max(0, ...) while still
        # writing a PaymentReceived row for the full amount, so the ledger and
        # the balance drifted apart permanently and silently.
        try:
            customer = Customer.objects.get(pk=attrs["customer_id"])
        except Customer.DoesNotExist:
            raise serializers.ValidationError({"customer_id": "Customer not found."})

        if customer.outstanding_paise <= 0:
            raise serializers.ValidationError(
                {"amount_paise": "This customer has no outstanding balance."}
            )
        if attrs["amount_paise"] > customer.outstanding_paise:
            owed = customer.outstanding_paise / 100
            raise serializers.ValidationError(
                {"amount_paise": f"Amount exceeds the outstanding balance of Rs {owed:,.2f}."}
            )
        attrs["customer"] = customer
        return attrs
