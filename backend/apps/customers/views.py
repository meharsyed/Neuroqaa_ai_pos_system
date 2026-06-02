from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["gender"]
    search_fields = ["name", "phone"]
    ordering_fields = ["created_at", "name"]

    @action(detail=False, methods=["get"], url_path="lookup")
    def lookup(self, request):
        """Return a customer by exact phone number, or null if not found."""
        phone = request.query_params.get("phone", "").strip()
        if not phone:
            return Response(
                {"detail": "phone query parameter required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            customer = Customer.objects.get(phone=phone)
            return Response(CustomerSerializer(customer).data)
        except Customer.DoesNotExist:
            return Response(None)

    @action(detail=True, methods=["get"], url_path="sales")
    def sales_history(self, request, pk=None):
        """Paginated sales history for a specific customer."""
        from apps.sales.models import Sale
        from apps.sales.serializers import SaleSerializer

        customer = self.get_object()
        qs = (
            Sale.objects.filter(customer=customer)
            .select_related("cashier", "payment", "customer")
            .prefetch_related("items__product")
            .order_by("-created_at")
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(SaleSerializer(page, many=True).data)
        return Response(SaleSerializer(qs, many=True).data)
