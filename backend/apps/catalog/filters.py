import django_filters
from django.db.models import F

from .models import Product


class ProductFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    sku = django_filters.CharFilter(lookup_expr="icontains")
    barcode = django_filters.CharFilter(lookup_expr="exact")
    category = django_filters.NumberFilter(field_name="category__id")
    is_active = django_filters.BooleanFilter()
    low_stock = django_filters.BooleanFilter(method="filter_low_stock")

    class Meta:
        model = Product
        fields = ["name", "sku", "barcode", "category", "is_active"]

    def filter_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(
                low_stock_threshold__gt=0,
                inventory__stock_qty__lte=F("low_stock_threshold"),
            )
        return queryset
