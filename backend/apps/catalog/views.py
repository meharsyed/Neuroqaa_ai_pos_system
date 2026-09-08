import tablib
from django.db.models import F
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.accounts.activity import log_activity
from apps.accounts.permissions import IsOwnerOrManager, IsOwnerOrManagerOrReadOnly

from .filters import ProductFilter
from apps.sales.models import SaleItem

from .models import Category, Inventory, Product, StockMovement, Supplier
from .resources import ProductResource
from .serializers import (
    CategorySerializer,
    InventorySerializer,
    ProductSerializer,
    StockInSerializer,
    StockMovementSerializer,
    SupplierSerializer,
)
from .services import apply_stock_movement


class CategoryViewSet(viewsets.ModelViewSet):
    # Anyone at the till may read the catalogue; only an owner or manager
    # may change a price, add stock, or archive a product.
    permission_classes = [IsOwnerOrManagerOrReadOnly]
    queryset = Category.objects.filter(is_active=True).order_by("name")
    serializer_class = CategorySerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]


class SupplierViewSet(viewsets.ModelViewSet):
    # Anyone signed in may read the supplier list (needed to pick one while
    # stocking a product); only an owner or manager may add, edit, or
    # deactivate a supplier — the same bar as editing the catalogue.
    permission_classes = [IsOwnerOrManagerOrReadOnly]
    queryset = Supplier.objects.order_by("name")
    serializer_class = SupplierSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "contact_person", "phone"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        qs = Supplier.objects.order_by("name")
        # The list hides deactivated suppliers by default, same convention as
        # archived products. Fetching one directly (edit, restore, purchase
        # history) must still find it even after deactivation.
        if self.action != "list":
            return qs
        if self.request.query_params.get("include_inactive") != "true":
            qs = qs.filter(is_active=True)
        return qs

    def destroy(self, request, *args, **kwargs):
        """
        Deactivate by default; delete only a supplier with no purchase history.

        StockMovement.supplier is PROTECT — a supplier with stock movements
        under it can't be hard-deleted at the database level anyway. Without
        this override that surfaces as a raw 500 the first time someone
        clicks delete on a supplier that's actually been used, exactly like
        Product.destroy() exists to prevent for products.
        """
        supplier = self.get_object()
        has_movements = supplier.stock_movements.exists()

        if has_movements:
            if not supplier.is_active:
                return Response(
                    {"detail": f"{supplier.name} is already deactivated."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            supplier.is_active = False
            supplier.save(update_fields=["is_active", "updated_at"])
            return Response(
                {
                    "archived": True,
                    "detail": (
                        f"{supplier.name} has been deactivated. It has purchase "
                        f"history, so it stays on past stock-in records and can "
                        f"be reactivated at any time."
                    ),
                },
                status=status.HTTP_200_OK,
            )

        name = supplier.name
        supplier.delete()
        return Response(
            {"archived": False, "detail": f"{name} was deleted — it had no purchase history."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(summary="Reactivate a deactivated supplier")
    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        supplier = self.get_object()
        if supplier.is_active:
            return Response({"detail": "That supplier is not deactivated."},
                            status=status.HTTP_400_BAD_REQUEST)
        supplier.is_active = True
        supplier.save(update_fields=["is_active", "updated_at"])
        return Response(SupplierSerializer(supplier).data)


class ProductViewSet(viewsets.ModelViewSet):
    # Anyone at the till may read the catalogue; only an owner or manager
    # may change a price, add stock, or archive a product.
    permission_classes = [IsOwnerOrManagerOrReadOnly]
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
        qs = Product.objects.select_related("category", "inventory").order_by("name")
        # The list hides archived products — they are meant to be out of the way
        # of the till. Anything addressing one product by id must still find it,
        # or restoring an archived product would 404 on the way in.
        if self.action != "list":
            return qs
        if self.request.query_params.get("include_inactive") != "true":
            qs = qs.filter(is_active=True)
        return qs

    def destroy(self, request, *args, **kwargs):
        """
        Archive by default; delete only what has no history.

        A product that has ever been sold is referenced by every bill it
        appeared on. Deleting the row would corrupt those bills — and a shop
        that has to produce a two-year-old invoice for a warranty claim needs
        them intact. So the normal answer to "remove this product" is to
        archive it: it leaves the till and the search, and stays on the record.

        A genuinely untouched product — a typo entered five minutes ago — has
        nothing to protect and is deleted properly.
        """
        product = self.get_object()

        has_sales = SaleItem.objects.filter(product=product).exists()
        has_movements = StockMovement.objects.filter(product=product).exists()
        stock = getattr(getattr(product, "inventory", None), "stock_qty", 0) or 0

        if has_sales or has_movements or stock:
            if not product.is_active:
                return Response(
                    {"detail": f"{product.name} is already archived."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            product.is_active = False
            product.save(update_fields=["is_active", "updated_at"])
            log_activity(
                "product_archived", user=request.user,
                details={"sku": product.sku, "name": product.name}, request=request,
            )
            return Response(
                {
                    "archived": True,
                    "detail": (
                        f"{product.name} has been archived. It has been sold or "
                        f"stocked before, so it stays on old bills and reports and "
                        f"can be restored at any time."
                    ),
                },
                status=status.HTTP_200_OK,
            )

        name, sku = product.name, product.sku
        product.delete()
        log_activity(
            "product_deleted", user=request.user,
            details={"sku": sku, "name": name}, request=request,
        )
        return Response(
            {"archived": False, "detail": f"{name} was deleted — it had no history."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(summary="Restore an archived product")
    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        product = self.get_object()
        if product.is_active:
            return Response({"detail": "That product is not archived."},
                            status=status.HTTP_400_BAD_REQUEST)
        product.is_active = True
        product.save(update_fields=["is_active", "updated_at"])
        return Response(ProductSerializer(product, context={"request": request}).data)

    @extend_schema(
        summary="Whether this product can be deleted outright, or only archived",
        description="Lets the interface offer the right verb before anyone commits to it.",
    )
    @action(detail=True, methods=["get"], url_path="removal-check")
    def removal_check(self, request, pk=None):
        product = self.get_object()
        sales = SaleItem.objects.filter(product=product).count()
        movements = StockMovement.objects.filter(product=product).count()
        stock = getattr(getattr(product, "inventory", None), "stock_qty", 0) or 0
        blockers = []
        if sales:
            blockers.append(f"sold on {sales} bill{'s' if sales != 1 else ''}")
        if movements:
            blockers.append(f"{movements} stock movement{'s' if movements != 1 else ''}")
        if stock:
            blockers.append(f"{stock} in stock")
        return Response({
            "can_delete": not blockers,
            "reasons": blockers,
            "is_active": product.is_active,
        })

    @extend_schema(
        summary="Bulk import products from CSV",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {"file": {"type": "string", "format": "binary"}},
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "imported": {"type": "integer"},
                    "updated": {"type": "integer"},
                    "skipped": {"type": "integer"},
                },
            }
        },
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
            return Response(
                {"detail": f"Could not parse file: {exc}"}, status=status.HTTP_400_BAD_REQUEST
            )

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
        return Response(
            {
                "imported": result.totals.get("new", 0),
                "updated": result.totals.get("update", 0),
                "skipped": result.totals.get("skip", 0),
            }
        )

    @extend_schema(summary="Look up an active product by barcode (used by checkout scanner)")
    @action(detail=False, methods=["get"], url_path=r"barcode/(?P<barcode>[^/.]+)")
    def by_barcode(self, request, barcode=None):
        # Scanning at the till must never surface an archived product — that is
        # the whole point of archiving one.
        qs = self.get_queryset().filter(is_active=True)
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
    permission_classes = [IsOwnerOrManagerOrReadOnly]
    queryset = Inventory.objects.select_related("product", "product__category").order_by(
        "product__name"
    )
    serializer_class = InventorySerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["product__sku", "product__name"]
    ordering_fields = ["stock_qty", "updated_at"]

    @extend_schema(
        summary="Record stock-in for a product",
        request=StockInSerializer,
        responses={201: StockMovementSerializer},
    )
    @action(
        detail=False, methods=["post"], url_path="stock-in",
        permission_classes=[IsOwnerOrManager],
    )
    def stock_in(self, request):
        serializer = StockInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        movement = apply_stock_movement(
            product=d["product"],
            movement_type=StockMovement.MovementType.STOCK_IN,
            qty_change=d["qty"],
            cost_price_paise=d.get("cost_price_paise"),
            supplier=d.get("supplier"),
            reference=d.get("reference", ""),
            notes=d.get("notes", ""),
            created_by=request.user,
        )
        # Stock appearing from nowhere is where shrinkage hides, so record who
        # did it and why. Action.STOCK_IN was defined and never written until now.
        log_activity(
            "stock_in",
            user=request.user,
            details={
                "product": d["product"].sku,
                "qty": str(d["qty"]),
                "supplier": (d.get("supplier").name if d.get("supplier") else ""),
                "reference": d.get("reference", ""),
                "notes": d.get("notes", ""),
            },
            request=request,
        )
        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)


class StockMovementViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsOwnerOrManagerOrReadOnly]
    queryset = StockMovement.objects.select_related(
        "product", "supplier", "created_by"
    ).order_by("-created_at")
    serializer_class = StockMovementSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    # A supplier's purchase history is this same list, filtered:
    # GET /api/movements/?supplier=<id>&movement_type=stock_in
    filterset_fields = ["product", "supplier", "movement_type"]
    search_fields = ["product__sku", "product__name", "reference"]
    ordering_fields = ["created_at"]
