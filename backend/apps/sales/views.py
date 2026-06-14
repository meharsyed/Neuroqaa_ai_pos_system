from datetime import date

import django_filters
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Sale, Shift
from .receipts import print_receipt_network, render_pdf_receipt, render_text_receipt
from .reports import (
    audit_report,
    audit_report_pdf,
    daily_summary,
    daily_summary_csv,
    date_range_summary,
    inventory_valuation,
    inventory_valuation_csv,
)
from .serializers import (
    CloseShiftSerializer,
    CreateReturnSerializer,
    CreateSaleSerializer,
    OpenShiftSerializer,
    SaleSerializer,
    ShiftSerializer,
)
from .services import close_shift, create_return, create_sale, get_shift_reconciliation, open_shift, void_sale

# ── Date-range filter for sales list ─────────────────────────────────────────


class SaleFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    customer = django_filters.NumberFilter(field_name="customer__id")

    class Meta:
        model = Sale
        fields = ["status", "cashier"]


# ── Sale ──────────────────────────────────────────────────────────────────────


class SaleViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        Sale.objects.select_related("cashier", "payment", "voided_by", "customer")
        .prefetch_related("items__product")
        .order_by("-created_at")
    )
    serializer_class = SaleSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SaleFilter
    search_fields = ["sale_number", "customer__name", "customer__phone"]
    ordering_fields = ["created_at", "total_paise"]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateSaleSerializer
        return SaleSerializer

    @extend_schema(
        summary="Create a completed sale (atomic)",
        request=CreateSaleSerializer,
        responses={201: SaleSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = CreateSaleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            sale = create_sale(
                cashier=request.user,
                items=[dict(i) for i in d["items"]],
                payment_method=d["payment_method"],
                amount_tendered_paise=d["amount_tendered_paise"],
                discount_paise=d.get("discount_paise", 0),
                tax_paise=d.get("tax_paise", 0),
                notes=d.get("notes", ""),
                customer_id=d.get("customer_id"),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        sale_data = (
            Sale.objects.select_related("cashier", "payment", "voided_by", "customer")
            .prefetch_related("items__product")
            .get(pk=sale.pk)
        )
        return Response(SaleSerializer(sale_data).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Void a completed sale — owner/manager only",
        responses={200: SaleSerializer},
    )
    @action(detail=True, methods=["post"], url_path="void")
    def void(self, request, pk=None):
        if request.user.role not in ("owner", "manager"):
            return Response(
                {"detail": "Only owner or manager can void a sale."},
                status=status.HTTP_403_FORBIDDEN,
            )
        sale = self.get_object()
        try:
            sale = void_sale(sale=sale, voided_by=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        sale_data = (
            Sale.objects.select_related("cashier", "payment", "voided_by", "customer")
            .prefetch_related("items__product")
            .get(pk=sale.pk)
        )
        return Response(SaleSerializer(sale_data).data)

    @extend_schema(summary="Process a partial or full return against a completed sale")
    @action(detail=True, methods=["post"], url_path="return")
    def process_return(self, request, pk=None):
        original_sale = self.get_object()
        serializer = CreateReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            return_sale = create_return(
                cashier=request.user,
                original_sale=original_sale,
                items=[dict(i) for i in d["items"]],
                notes=d.get("notes", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return_data = (
            Sale.objects
            .select_related("cashier", "payment", "voided_by", "customer")
            .prefetch_related("items__product")
            .get(pk=return_sale.pk)
        )
        return Response(SaleSerializer(return_data).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Plain-text receipt (ESC/POS-compatible)")
    @action(detail=True, methods=["get"], url_path="receipt/text")
    def receipt_text(self, request, pk=None):
        sale = (
            Sale.objects.select_related("cashier", "payment")
            .prefetch_related("items__product")
            .get(pk=pk)
        )
        text = render_text_receipt(sale)
        return HttpResponse(text, content_type="text/plain; charset=utf-8")

    @extend_schema(summary="PDF receipt (80 mm thermal)")
    @action(detail=True, methods=["get"], url_path="receipt/pdf")
    def receipt_pdf(self, request, pk=None):
        sale = (
            Sale.objects.select_related("cashier", "payment")
            .prefetch_related("items__product")
            .get(pk=pk)
        )
        try:
            pdf_bytes = render_pdf_receipt(sale)
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="receipt-{sale.sale_number}.pdf"'
        return response

    @extend_schema(summary="Send receipt to thermal printer over network")
    @action(detail=True, methods=["post"], url_path="receipt/print")
    def receipt_print(self, request, pk=None):
        sale = (
            Sale.objects.select_related("cashier", "payment")
            .prefetch_related("items__product")
            .get(pk=pk)
        )
        try:
            print_receipt_network(sale)
        except (RuntimeError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"detail": "Receipt sent to printer."})


# ── Shift ─────────────────────────────────────────────────────────────────────


class ShiftViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ShiftSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["cashier"]
    ordering_fields = ["opened_at"]

    def get_queryset(self):
        qs = Shift.objects.select_related("cashier").order_by("-opened_at")
        if self.request.user.role not in ("owner", "manager"):
            qs = qs.filter(cashier=self.request.user)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return OpenShiftSerializer
        if self.action == "close":
            return CloseShiftSerializer
        return ShiftSerializer

    @extend_schema(summary="Open a new shift")
    def create(self, request, *args, **kwargs):
        serializer = OpenShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        shift = open_shift(
            cashier=request.user,
            opening_float_paise=d.get("opening_float_paise", 0),
            notes=d.get("notes", ""),
        )
        return Response(ShiftSerializer(shift).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Close a shift and get variance summary")
    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        shift = self.get_object()
        serializer = CloseShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            summary = close_shift(
                shift=shift,
                closing_cash_paise=d["closing_cash_paise"],
                closing_notes=d.get("closing_notes", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        shift.refresh_from_db()
        return Response({"shift": ShiftSerializer(shift).data, "summary": summary})

    @extend_schema(summary="Pre-close cash reconciliation for an open shift")
    @action(detail=True, methods=["get"], url_path="reconciliation")
    def reconciliation(self, request, pk=None):
        shift = self.get_object()
        if shift.closed_at is not None:
            return Response(
                {"detail": "Shift is already closed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(get_shift_reconciliation(shift=shift))

    @extend_schema(summary="Get the caller's currently open shift, if any")
    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        shift = (
            Shift.objects.filter(cashier=request.user, closed_at__isnull=True)
            .order_by("-opened_at")
            .first()
        )
        if shift is None:
            return Response({"detail": "No open shift."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ShiftSerializer(shift).data)


# ── Reports ───────────────────────────────────────────────────────────────────


@extend_schema(summary="Daily revenue summary")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_daily(request):
    date_str = request.query_params.get("date", date.today().isoformat())
    try:
        report_date = date.fromisoformat(date_str)
    except ValueError:
        return Response(
            {"detail": "Invalid date. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST
        )

    data = daily_summary(report_date)

    if request.query_params.get("export") == "csv":
        csv_text = daily_summary_csv(data)
        resp = HttpResponse(csv_text, content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="daily-{report_date}.csv"'
        return resp

    return Response(data)


@extend_schema(summary="Revenue summary for a date range")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_date_range(request):
    start_str = request.query_params.get("start", date.today().isoformat())
    end_str = request.query_params.get("end", date.today().isoformat())
    try:
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)
    except ValueError:
        return Response(
            {"detail": "Invalid date. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST
        )
    if end < start:
        return Response(
            {"detail": "end must be on or after start."}, status=status.HTTP_400_BAD_REQUEST
        )
    return Response(date_range_summary(start, end))


@extend_schema(summary="Audit / closing report — owner/manager only")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_audit(request):
    from apps.config.utils import get_setting

    if request.user.role not in ("owner", "manager"):
        return Response(
            {"detail": "Only owner or manager can access the audit report."},
            status=status.HTTP_403_FORBIDDEN,
        )

    start_str = request.query_params.get("start", date.today().replace(day=1).isoformat())
    end_str = request.query_params.get("end", date.today().isoformat())

    try:
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)
    except ValueError:
        return Response({"detail": "Invalid date. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

    if end < start:
        return Response({"detail": "end must be on or after start."}, status=status.HTTP_400_BAD_REQUEST)

    data = audit_report(start, end)

    if request.query_params.get("export") == "pdf":
        try:
            pdf_bytes = audit_report_pdf(
                data,
                shop_name=get_setting("shop_name", "POS"),
                shop_address=get_setting("shop_address", ""),
                shop_phone=get_setting("shop_phone", ""),
            )
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        fname = f"audit-{start_str}-to-{end_str}.pdf"
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{fname}"'
        return resp

    return Response(data)


@extend_schema(summary="Current inventory valuation")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_inventory(request):
    data = inventory_valuation()

    if request.query_params.get("export") == "csv":
        csv_text = inventory_valuation_csv(data)
        resp = HttpResponse(csv_text, content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="inventory-valuation.csv"'
        return resp

    return Response(data)
