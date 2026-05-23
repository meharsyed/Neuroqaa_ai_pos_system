from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from .models import Sale
from .serializers import CreateSaleSerializer, SaleSerializer
from .services import create_sale, void_sale


class SaleViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        Sale.objects.select_related("cashier", "payment", "voided_by")
        .prefetch_related("items__product")
        .order_by("-created_at")
    )
    serializer_class = SaleSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "cashier"]
    search_fields = ["sale_number"]
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
                notes=d.get("notes", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        sale_data = Sale.objects.select_related("cashier", "payment", "voided_by").prefetch_related(
            "items__product"
        ).get(pk=sale.pk)
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

        sale_data = Sale.objects.select_related("cashier", "payment", "voided_by").prefetch_related(
            "items__product"
        ).get(pk=sale.pk)
        return Response(SaleSerializer(sale_data).data)