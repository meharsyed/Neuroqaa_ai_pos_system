from datetime import timedelta

from django.db.models import Count, Min, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsOwnerOrManager

from .models import CreditLedgerEntry, Customer, PaymentReceived
from .serializers import (
    CreatePaymentReceivedSerializer,
    CreditLedgerEntrySerializer,
    CustomerSerializer,
    PaymentReceivedSerializer,
)
from .services import customer_credit_summary, post_credit_entry


def _with_totals(qs):
    """
    Annotate sales count / revenue / first-credit-date with subqueries.

    The khata report used to loop every customer and let the serializer fire
    four queries each, unpaginated, refetched every 30 seconds. Subqueries are
    used rather than joined aggregates so the counts don't fan out.
    """
    from apps.sales.models import Sale

    completed = Sale.objects.filter(customer=OuterRef("pk"), status="completed")
    return qs.annotate(
        sales_count=Coalesce(
            Subquery(completed.values("customer").annotate(n=Count("id")).values("n")[:1]), 0
        ),
        sales_revenue=Coalesce(
            Subquery(
                completed.values("customer").annotate(t=Sum("total_paise")).values("t")[:1]
            ),
            0,
        ),
        first_credit_at=Subquery(
            CreditLedgerEntry.objects.filter(
                customer=OuterRef("pk"), kind=CreditLedgerEntry.Kind.SALE
            )
            .order_by("created_at")
            .values("created_at")[:1]
        ),
    )


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
    ordering_fields = ["created_at", "name", "outstanding_paise"]

    def get_queryset(self):
        return _with_totals(Customer.objects.all())

    def get_permissions(self):
        # Writing off credit is a money operation, not a cashier one.
        if self.action == "record_payment":
            return [IsOwnerOrManager()]
        return super().get_permissions()

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
            customer = self.get_queryset().get(phone=phone)
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

    # ── Khata detail ────────────────────────────────────────────────────────

    @action(detail=True, methods=["get"], url_path="khata")
    def khata_detail(self, request, pk=None):
        """
        Everything behind one customer's balance: the running ledger, the
        credit bills that created it, and the payments made against it.
        """
        from apps.sales.models import Sale

        customer = self.get_object()

        ledger = (
            CreditLedgerEntry.objects.filter(customer=customer)
            .select_related("sale", "created_by")
            .order_by("-created_at", "-id")[:200]
        )

        credit_sales = (
            Sale.objects.filter(customer=customer, payment__method="credit")
            .select_related("payment")
            .annotate(item_count=Count("items"))
            .order_by("-created_at")[:100]
        )

        payments = (
            PaymentReceived.objects.filter(customer=customer)
            .select_related("received_by")
            .order_by("-received_date")[:100]
        )

        summary = customer_credit_summary(customer)
        first = summary["first_credit_at"]
        summary["days_since_first_credit"] = (
            (timezone.now() - first).days if first else None
        )

        return Response(
            {
                "customer": CustomerSerializer(customer).data,
                "summary": summary,
                "ledger": CreditLedgerEntrySerializer(ledger, many=True).data,
                "credit_sales": [
                    {
                        "id": str(s.pk),
                        "sale_number": s.sale_number,
                        "created_at": s.created_at,
                        "total_paise": s.total_paise,
                        "item_count": s.item_count,
                        "status": s.status,
                    }
                    for s in credit_sales
                ],
                "payments": PaymentReceivedSerializer(payments, many=True).data,
            }
        )

    @action(detail=True, methods=["get"], url_path="khata/statement")
    def khata_statement(self, request, pk=None):
        """Printable khata statement — hand it to the customer."""
        from .statement import render_khata_statement

        customer = self.get_object()
        pdf = render_khata_statement(customer)
        resp = HttpResponse(pdf, content_type="application/pdf")
        name = (customer.name or customer.phone or f"customer-{customer.pk}").replace(" ", "-")
        resp["Content-Disposition"] = f'inline; filename="khata-{name}.pdf"'
        return resp

    # ── Payments ────────────────────────────────────────────────────────────

    @action(detail=False, methods=["post"], url_path="record-payment")
    def record_payment(self, request):
        """Record a payment received against a customer's khata."""
        serializer = CreatePaymentReceivedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer = serializer.validated_data["customer"]
        amount_paise = serializer.validated_data["amount_paise"]
        notes = serializer.validated_data.get("notes", "")

        payment = PaymentReceived.objects.create(
            customer=customer,
            amount_paise=amount_paise,
            notes=notes,
            received_by=request.user,
        )
        post_credit_entry(
            customer=customer,
            kind=CreditLedgerEntry.Kind.PAYMENT,
            delta_paise=-amount_paise,
            payment=payment,
            note=notes or "Payment received",
            created_by=request.user,
        )

        customer.refresh_from_db()
        return Response(
            {
                "payment": PaymentReceivedSerializer(payment).data,
                "customer": CustomerSerializer(customer).data,
            },
            status=status.HTTP_201_CREATED,
        )

    # ── Aging report ────────────────────────────────────────────────────────

    @action(detail=False, methods=["get"], url_path="khata-report")
    def khata_report(self, request):
        """Aged receivables across every customer carrying a balance."""
        customers = list(
            _with_totals(Customer.objects.filter(outstanding_paise__gt=0)).order_by(
                "-outstanding_paise"
            )[:500]
        )

        now = timezone.now()
        buckets = {"current": [], "30": [], "60": [], "90": []}

        for c in customers:
            first = getattr(c, "first_credit_at", None)
            days = (now - first).days if first else 0
            if days >= 90:
                buckets["90"].append(c)
            elif days >= 60:
                buckets["60"].append(c)
            elif days >= 30:
                buckets["30"].append(c)
            else:
                buckets["current"].append(c)

        month_start = now - timedelta(days=30)
        collected_30d = PaymentReceived.objects.filter(
            received_date__gte=month_start
        ).aggregate(t=Coalesce(Sum("amount_paise"), 0))["t"]

        charged_30d = CreditLedgerEntry.objects.filter(
            kind=CreditLedgerEntry.Kind.SALE, created_at__gte=month_start
        ).aggregate(t=Coalesce(Sum("delta_paise"), 0))["t"]

        oldest = (
            CreditLedgerEntry.objects.filter(kind=CreditLedgerEntry.Kind.SALE)
            .filter(customer__outstanding_paise__gt=0)
            .aggregate(d=Min("created_at"))["d"]
        )

        return Response(
            {
                "current": CustomerSerializer(buckets["current"], many=True).data,
                "days_30": CustomerSerializer(buckets["30"], many=True).data,
                "days_60": CustomerSerializer(buckets["60"], many=True).data,
                "days_90_plus": CustomerSerializer(buckets["90"], many=True).data,
                "total_outstanding_paise": sum(c.outstanding_paise for c in customers),
                "customer_count": len(customers),
                # Insight strip
                "collected_30d_paise": collected_30d,
                "charged_30d_paise": charged_30d,
                "net_30d_paise": charged_30d - collected_30d,
                "largest_balance_paise": customers[0].outstanding_paise if customers else 0,
                "largest_balance_name": customers[0].display_name if customers else None,
                "oldest_credit_days": (now - oldest).days if oldest else None,
            }
        )
