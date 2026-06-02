from decimal import Decimal

from django.contrib import admin

from apps.catalog.money import Money

from .models import Payment, Sale, SaleItem, Shift


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ["product", "qty", "display_unit_price", "display_item_discount", "display_subtotal"]
    fields = readonly_fields
    can_delete = False

    def display_unit_price(self, obj):
        return str(Money(obj.unit_price_paise))
    display_unit_price.short_description = "Unit Price"

    def display_item_discount(self, obj):
        return str(Money(obj.discount_paise)) if obj.discount_paise else "—"
    display_item_discount.short_description = "Discount"

    def display_subtotal(self, obj):
        return str(Money(obj.subtotal_paise))
    display_subtotal.short_description = "Subtotal"

    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    readonly_fields = ["method", "amount_tendered_paise", "change_paise"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        "sale_number", "cashier", "status",
        "display_subtotal", "display_discount", "display_total",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["sale_number", "cashier__email"]
    readonly_fields = [
        "sale_number", "cashier", "status",
        "display_subtotal", "display_discount", "display_total",
        "voided_by", "voided_at", "created_at", "updated_at",
    ]
    fieldsets = [
        (None, {"fields": ["sale_number", "cashier", "status"]}),
        ("Amounts", {"fields": ["display_subtotal", "display_discount", "display_total"]}),
        ("Void", {"fields": ["voided_by", "voided_at"], "classes": ["collapse"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"], "classes": ["collapse"]}),
    ]
    inlines = [SaleItemInline, PaymentInline]

    def display_subtotal(self, obj):
        return str(Money(obj.subtotal_paise))
    display_subtotal.short_description = "Subtotal"

    def display_discount(self, obj):
        return str(Money(obj.discount_paise)) if obj.discount_paise else "—"
    display_discount.short_description = "Discount"

    def display_total(self, obj):
        return str(Money(obj.total_paise))
    display_total.short_description = "Total"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ["pk", "cashier", "opened_at", "closed_at"]
    list_filter = ["cashier"]
    readonly_fields = ["opened_at"]