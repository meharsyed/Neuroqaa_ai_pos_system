from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin

from .models import Category, Inventory, Product, StockMovement
from .money import Money
from .resources import ProductResource


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_classes = [ProductResource]
    list_display = [
        "sku", "name", "category", "unit",
        "display_cost", "display_sell", "display_margin",
        "is_active",
    ]
    list_filter = ["category", "unit", "is_active"]
    search_fields = ["name", "sku", "barcode"]
    list_select_related = ["category"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        (None, {"fields": ["name", "sku", "barcode", "category", "unit", "description", "is_active"]}),
        ("Pricing (paise = Rs × 100)", {"fields": ["cost_price_paise", "sell_price_paise"]}),
        ("Inventory", {"fields": ["low_stock_threshold"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"], "classes": ["collapse"]}),
    ]

    def display_cost(self, obj):
        return str(Money(obj.cost_price_paise))
    display_cost.short_description = "Cost"

    def display_sell(self, obj):
        return str(Money(obj.sell_price_paise))
    display_sell.short_description = "Sell Price"

    def display_margin(self, obj):
        margin = obj.margin_paise
        color = "green" if margin > 0 else "red"
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            str(Money(margin)),
        )
    display_margin.short_description = "Margin"


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ["product", "stock_qty", "display_level", "updated_at"]
    search_fields = ["product__sku", "product__name"]
    list_select_related = ["product"]
    readonly_fields = ["updated_at"]

    def display_level(self, obj):
        if obj.is_low_stock:
            return format_html('<span style="color:red;font-weight:bold;">⚠ Low Stock</span>')
        return format_html('<span style="color:green;">OK</span>')
    display_level.short_description = "Level"

    def has_add_permission(self, request):
        return False  # Inventory rows are created automatically with products

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        "product", "movement_type", "qty_change", "qty_after",
        "reference", "created_by", "created_at",
    ]
    list_filter = ["movement_type", "created_at"]
    search_fields = ["product__sku", "product__name", "reference"]
    list_select_related = ["product", "created_by"]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False  # Only created via services.apply_stock_movement

    def has_change_permission(self, request, obj=None):
        return False  # Append-only

    def has_delete_permission(self, request, obj=None):
        return False  # Append-only