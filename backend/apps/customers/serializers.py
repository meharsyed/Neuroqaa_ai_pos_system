from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework import serializers

from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    total_sales = serializers.SerializerMethodField()
    total_revenue_paise = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "phone",
            "gender",
            "notes",
            "display_name",
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
