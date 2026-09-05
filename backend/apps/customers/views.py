from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Customer, PaymentReceived
from .serializers import CustomerSerializer, PaymentReceivedSerializer, CreatePaymentReceivedSerializer


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

    @action(detail=False, methods=["post"], url_path="record-payment")
    def record_payment(self, request):
        """Record a payment received against customer credit balance."""
        serializer = CreatePaymentReceivedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer_id = serializer.validated_data["customer_id"]
        amount_paise = serializer.validated_data["amount_paise"]
        notes = serializer.validated_data.get("notes", "")

        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response(
                {"detail": f"Customer {customer_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if customer has outstanding balance
        if customer.outstanding_paise <= 0:
            return Response(
                {"detail": "Customer has no outstanding balance"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Create payment record
            payment = PaymentReceived.objects.create(
                customer=customer,
                amount_paise=amount_paise,
                notes=notes,
                received_by=request.user,
            )

            # Reduce customer's outstanding balance
            customer.outstanding_paise = max(0, customer.outstanding_paise - amount_paise)
            customer.save(update_fields=["outstanding_paise"])

        return Response(
            {
                "payment": PaymentReceivedSerializer(payment).data,
                "customer": CustomerSerializer(customer).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="khata-report")
    def khata_report(self, request):
        """Get aged payables report for all customers with outstanding balance."""
        from django.utils import timezone
        from datetime import timedelta

        customers = Customer.objects.filter(outstanding_paise__gt=0).order_by(
            "-outstanding_paise"
        )

        aging_buckets = {"current": [], "30_days": [], "60_days": [], "90_plus_days": []}
        now = timezone.now()

        for customer in customers:
            # Find oldest unpaid credit sale
            oldest_sale = customer.sales.filter(
                payment__method="credit", status="completed"
            ).order_by("created_at").first()

            if oldest_sale:
                days_old = (now - oldest_sale.created_at).days
                if days_old >= 90:
                    aging_buckets["90_plus_days"].append(customer)
                elif days_old >= 60:
                    aging_buckets["60_days"].append(customer)
                elif days_old >= 30:
                    aging_buckets["30_days"].append(customer)
                else:
                    aging_buckets["current"].append(customer)
            else:
                aging_buckets["current"].append(customer)

        return Response(
            {
                "current": CustomerSerializer(aging_buckets["current"], many=True).data,
                "days_30": CustomerSerializer(aging_buckets["30_days"], many=True).data,
                "days_60": CustomerSerializer(aging_buckets["60_days"], many=True).data,
                "days_90_plus": CustomerSerializer(aging_buckets["90_plus_days"], many=True).data,
                "total_outstanding_paise": sum(
                    c.outstanding_paise for c in customers
                ),
            }
        )
