import tablib
from django.db.models import F
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from .filters import ProductFilter
from .models import Category, Inventory, Product, StockMovement
from .resources import ProductResource
from .serializers import (
    CategorySerializer,
    InventorySerializer,
    ProductSerializer,
    StockInSerializer,
    StockMovementSerializer,
)
from .services import apply_stock_movement


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(is_active=True).order_by("name")
    serializer_class = CategorySerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = (
        Product.objects.select_related("category", "inventory")
        .filter(is_active=True)
        .order_by("name")
    )
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "sku", "barcode"]
    ordering_fields = ["name", "sku", "sell_price_paise", "created_at"]

    def get_queryset(self):
        # Allow ?include_inactive=true for admin use
        qs = Product.objects.select_related("category", "inventory").order_by("name")
        if self.request.query_params.get("include_inactive") != "true":
            qs = qs.filter(is_active=True)
        return qs

    @extend_schema(
        summary="Bulk import products from CSV",
        request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}},
        responses={200: {"type": "object", "properties": {"imported": {"type": "integer"}, "updated": {"type": "integer"}, "skipped": {"type": "integer"}}}},
    )
    @action(detail=False, methods=["post"], url_path="import", parser_classes=[MultiPartParser])
    def import_csv(self, request):
        """
        Bulk-import products from a CSV file.
        Accepts columns: name, sku, barcode, category, unit,
                         cost_price, sell_price, low_stock_threshold, is_active
        Performs a dry-run first; only commits if zero errors.
        """
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            content = file.read().decode("utf-8-sig")  # handles Excel BOM
            dataset = tablib.Dataset().load(content, headers=True)
        except Exception as exc:
            return Response({"detail": f"Could not parse file: {exc}"}, status=status.HTTP_400_BAD_REQUEST)

        resource = ProductResource()

        # Dry-run: detect errors without writing anything
        dry_result = resource.import_data(dataset, dry_run=True, raise_errors=False)
        if dry_result.has_errors():
            # In django-import-export 4.x, row_errors() yields (row_num, list_of_errors).
            # The second element is the plain list — no .errors attribute.
            errors = [
                {"row": row_num + 2, "errors": [str(e.error) for e in row_errs]}
                for row_num, row_errs in dry_result.row_errors()
            ]
            return Response(
                {"detail": "CSV contains errors. Nothing was imported.", "errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Real import
        result = resource.import_data(dataset, dry_run=False, raise_errors=True)
        return Response({
            "imported": result.totals.get("new", 0),
            "updated": result.totals.get("update", 0),
            "skipped": result.totals.get("skip", 0),
        })

    @extend_schema(summary="Look up an active product by barcode (used by checkout scanner)")
    @action(detail=False, methods=["get"], url_path=r"barcode/(?P<barcode>[^/.]+)")
    def by_barcode(self, request, barcode=None):
        qs = self.get_queryset()
        try:
            product = qs.get(barcode=barcode.strip())
        except Product.DoesNotExist:
            return Response(
                {"detail": f"No active product with barcode '{barcode}'."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Product.MultipleObjectsReturned:
            return Response(
                {"detail": f"Multiple products share barcode '{barcode}'. Fix in admin."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(self.get_serializer(product).data)

    @extend_schema(summary="Products below their low-stock threshold")
    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        qs = (
            Product.objects.select_related("category", "inventory")
            .filter(
                is_active=True,
                low_stock_threshold__gt=0,
                inventory__stock_qty__lte=F("low_stock_threshold"),
            )
            .order_by("name")
        )
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class InventoryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Inventory.objects.select_related("product", "product__category").order_by("product__name")
    serializer_class = InventorySerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["product__sku", "product__name"]
    ordering_fields = ["stock_qty", "updated_at"]

    @extend_schema(
        summary="Record stock-in for a product",
        request=StockInSerializer,
        responses={201: StockMovementSerializer},
    )
    @action(detail=False, methods=["post"], url_path="stock-in")
    def stock_in(self, request):
        serializer = StockInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        movement = apply_stock_movement(
            product=d["product"],
            movement_type=StockMovement.MovementType.STOCK_IN,
            qty_change=d["qty"],
            cost_price_paise=d.get("cost_price_paise"),
            reference=d.get("reference", ""),
            notes=d.get("notes", ""),
            created_by=request.user,
        )
        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)


class StockMovementViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = StockMovement.objects.select_related("product", "created_by").order_by("-created_at")
    serializer_class = StockMovementSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["product", "movement_type"]
    search_fields = ["product__sku", "product__name", "reference"]
    ordering_fields = ["created_at"]