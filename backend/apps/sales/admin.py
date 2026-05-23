from django.contrib import admin

from .models import Payment, Sale, SaleItem, Shift


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ["product", "qty", "unit_price_paise", "discount_paise", "subtotal_paise"]
    can_delete = False

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
    list_display = ["sale_number", "cashier", "status", "total_paise", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["sale_number", "cashier__email"]
    readonly_fields = [
        "sale_number", "cashier", "status",
        "subtotal_paise", "discount_paise", "tax_paise", "total_paise",
        "voided_by", "voided_at", "created_at", "updated_at",
    ]
    inlines = [SaleItemInline, PaymentInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ["pk", "cashier", "opened_at", "closed_at"]
    list_filter = ["cashier"]
    readonly_fields = ["opened_at"]