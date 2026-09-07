"""Quotation API. Separate module so it does not tangle with the sales views."""

from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsOwnerOrManagerOrReadOnly

from .quotation_services import (
    create_quotation,
    mark_converted,
    quotation_to_cart,
    revise_quotation,
)
from .quotations import BusinessProfile, Quotation, QuotationItem


# ── Serializers ────────────────────────────────────────────────────────────


class BusinessProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = [
            "id", "name", "address", "phone", "email", "tax_number",
            "footer", "is_default", "is_active",
        ]


class QuotationItemSerializer(serializers.ModelSerializer):
    line_total_paise = serializers.IntegerField(read_only=True)
    is_off_catalogue = serializers.BooleanField(read_only=True)

    class Meta:
        model = QuotationItem
        fields = [
            "id", "product", "name", "sku", "description", "qty", "unit",
            "unit_price_paise", "discount_paise", "position",
            "line_total_paise", "is_off_catalogue",
        ]


class QuotationSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True, read_only=True)
    profile_name = serializers.CharField(source="profile.name", read_only=True, default=None)
    created_by_name = serializers.SerializerMethodField()
    display_number = serializers.CharField(read_only=True)
    valid_until = serializers.DateField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Quotation
        fields = [
            "id", "number", "display_number", "revision", "status",
            "profile", "profile_name",
            "customer", "customer_name", "customer_phone", "customer_address",
            "valid_days", "valid_until", "is_expired",
            "subtotal_paise", "discount_paise", "tax_paise", "tax_pct",
            "installation_paise", "installation_note", "total_paise",
            "notes", "terms", "items",
            "created_by", "created_by_name",
            "converted_sale", "converted_at", "created_at", "updated_at",
        ]

    def get_created_by_name(self, obj) -> str:
        return obj.created_by.get_full_name() or obj.created_by.email


class QuotationItemInputSerializer(serializers.Serializer):
    """
    A line. `product_id` is optional — a quotation routinely lists work the
    shop does not stock, and refusing that is what sends people back to Word.
    """

    product_id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    qty = serializers.DecimalField(max_digits=10, decimal_places=3, required=False)
    unit = serializers.CharField(max_length=20, required=False, allow_blank=True)
    unit_price_paise = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    discount_paise = serializers.IntegerField(min_value=0, required=False, default=0)

    def validate(self, attrs):
        if not attrs.get("product_id") and not (attrs.get("name") or "").strip():
            raise serializers.ValidationError(
                "A line needs either a product or a description of its own."
            )
        return attrs


class CreateQuotationSerializer(serializers.Serializer):
    items = QuotationItemInputSerializer(many=True)
    profile_id = serializers.IntegerField(required=False, allow_null=True)
    customer_id = serializers.IntegerField(required=False, allow_null=True)
    customer_name = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    customer_phone = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    customer_address = serializers.CharField(required=False, allow_blank=True, default="")
    discount_paise = serializers.IntegerField(min_value=0, required=False, default=0)
    tax_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    installation_paise = serializers.IntegerField(min_value=0, required=False, default=0)
    installation_note = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    valid_days = serializers.IntegerField(min_value=1, max_value=365, required=False, default=15)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    terms = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("A quotation needs at least one line.")
        return value


# ── Views ──────────────────────────────────────────────────────────────────


class BusinessProfileViewSet(viewsets.ModelViewSet):
    """Letterheads to quote under. Owner/manager may change them."""

    queryset = BusinessProfile.objects.all()
    serializer_class = BusinessProfileSerializer
    permission_classes = [IsOwnerOrManagerOrReadOnly]
    pagination_class = None


class QuotationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        Quotation.objects.select_related("profile", "customer", "created_by", "converted_sale")
        .prefetch_related("items__product")
        .order_by("-created_at")
    )
    serializer_class = QuotationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "customer"]
    search_fields = ["number", "customer_name", "customer_phone", "items__name"]
    ordering_fields = ["created_at", "total_paise"]

    def create(self, request, *args, **kwargs):
        serializer = CreateQuotationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            quotation = create_quotation(
                created_by=request.user,
                items=[dict(i) for i in d["items"]],
                profile_id=d.get("profile_id"),
                customer_id=d.get("customer_id"),
                customer_name=d.get("customer_name", ""),
                customer_phone=d.get("customer_phone", ""),
                customer_address=d.get("customer_address", ""),
                discount_paise=d.get("discount_paise", 0),
                tax_pct=d.get("tax_pct"),
                installation_paise=d.get("installation_paise", 0),
                installation_note=d.get("installation_note", ""),
                valid_days=d.get("valid_days", 15),
                notes=d.get("notes", ""),
                terms=d.get("terms", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            self.get_serializer(quotation).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(summary="Revise a quotation in place — bumps the revision")
    @action(detail=True, methods=["post"], url_path="revise")
    def revise(self, request, pk=None):
        quotation = self.get_object()
        serializer = CreateQuotationSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        d = dict(serializer.validated_data)
        if "items" in d:
            d["items"] = [dict(i) for i in d["items"]]
        try:
            quotation = revise_quotation(
                quotation=quotation, created_by=request.user, **d
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(quotation).data)

    @extend_schema(summary="Change a quotation's status")
    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request, pk=None):
        quotation = self.get_object()
        new = request.data.get("status")
        if new not in Quotation.Status.values:
            return Response({"detail": f"Unknown status: {new!r}."},
                            status=status.HTTP_400_BAD_REQUEST)
        if quotation.converted_sale_id and new != Quotation.Status.ACCEPTED:
            return Response(
                {"detail": "This quotation has already become a sale."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        quotation.status = new
        quotation.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(quotation).data)

    @extend_schema(summary="Everything the till needs to turn this into a sale")
    @action(detail=True, methods=["get"], url_path="to-cart")
    def to_cart(self, request, pk=None):
        return Response(quotation_to_cart(self.get_object()))

    @extend_schema(summary="Record that this quotation became a sale")
    @action(detail=True, methods=["post"], url_path="mark-converted")
    def mark_converted_action(self, request, pk=None):
        from .models import Sale

        quotation = self.get_object()
        try:
            sale = Sale.objects.get(pk=request.data.get("sale_id"))
        except (Sale.DoesNotExist, TypeError, ValueError):
            return Response({"detail": "That sale does not exist."},
                            status=status.HTTP_400_BAD_REQUEST)
        mark_converted(quotation=quotation, sale=sale, user=request.user)
        return Response(self.get_serializer(quotation).data)

    @extend_schema(summary="The printed quotation")
    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf(self, request, pk=None):
        from .receipts.quotation_pdf import render_quotation_pdf

        quotation = self.get_object()
        pdf = render_quotation_pdf(quotation)
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = (
            f'inline; filename="quotation-{quotation.number}.pdf"'
        )
        return resp
