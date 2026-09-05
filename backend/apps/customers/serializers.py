from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework import serializers

from .models import Customer, PaymentReceived


class CustomerSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    total_sales = serializers.SerializerMethodField()
    total_revenue_paise = serializers.SerializerMethodField()
    days_overdue = serializers.SerializerMethodField()

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
            "days_overdue",
            "total_sales",
            "total_revenue_paise",
            "created_at",
        ]

    def get_total_sales(self, obj) -> int:
        return obj.sales.filter(status="completed").count()

    def get_total_revenue_paise(self, obj) -> int:
        return obj.sales.filter(status="completed").aggregate(
            total=Coalesce(Sum("total_paise"), 0)
        )["total"]

    def get_days_overdue(self, obj) -> int | None:
        """Days since first unpaid credit sale"""
        if obj.outstanding_paise <= 0:
            return None
        # Find first credit sale for this customer
        first_credit = obj.sales.filter(
            payment__method="credit", status="completed"
        ).order_by("created_at").first()
        if first_credit:
            from django.utils import timezone
            days = (timezone.now() - first_credit.created_at).days
            return max(0, days)
        return None


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
    """Input serializer for recording a payment received against customer credit"""
    customer_id = serializers.IntegerField()
    amount_paise = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
