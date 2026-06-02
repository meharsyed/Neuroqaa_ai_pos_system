from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Inventory, StockMovement
from apps.catalog.services import apply_stock_movement

from .models import Payment, Sale, SaleItem, Shift


def _generate_sale_number(sale: Sale) -> str:
    """
    Readable, sortable sale number: SALE-YYYYMMDD-NNNNN
    Uses localdate() so the date reflects the shop's timezone (set TIME_ZONE in settings).
    The PK guarantees global uniqueness.
    """
    today = timezone.localdate()
    return f"SALE-{today:%Y%m%d}-{sale.pk:05d}"


def get_shift_reconciliation(*, shift) -> dict:
    """
    Pre-close cash summary for an open shift — does NOT close it.
    Returns expected cash = opening_float + all cash sales this shift.
    """
    from django.db.models import Count, Sum
    from django.db.models.functions import Coalesce

    completed = shift.sales.filter(status=Sale.Status.COMPLETED)
    agg = completed.aggregate(
        total_revenue=Coalesce(Sum("total_paise"), 0),
        total_count=Count("id"),
    )
    cash_sales_total = completed.filter(payment__method="cash").aggregate(
        total=Coalesce(Sum("total_paise"), 0)
    )["total"]

    return {
        "opening_float_paise": shift.opening_float_paise,
        "cash_sales_total_paise": cash_sales_total,
        "expected_cash_paise": shift.opening_float_paise + cash_sales_total,
        "total_sales": agg["total_count"],
        "total_revenue_paise": agg["total_revenue"],
    }


def create_sale(
    *,
    cashier,
    items: list[dict],
    payment_method: str = "cash",
    amount_tendered_paise: int,
    discount_paise: int = 0,
    notes: str = "",
    customer_id: int | None = None,
) -> Sale:
    """
    Atomically create a completed sale. All steps are inside one transaction —
    any failure (validation, DB error, crash) rolls back everything.

    items: list of dicts with keys:
        product_id (int), qty (str/Decimal), unit_price_paise (int),
        discount_paise (int, optional — item-level discount)

    Steps:
      1. Lock all inventory rows in deterministic order (sorted by product_id)
         to prevent deadlocks on concurrent sales.
      2. Aggregate qty per product and guard against overselling.
      3. Create Sale, set the readable sale_number from the PK.
      4. Create SaleItem rows.
      5. Apply negative StockMovements via apply_stock_movement().
      6. Create Payment.
    """
    with transaction.atomic():
        # Sort product_ids to ensure consistent lock ordering across concurrent transactions,
        # which prevents the AB/BA deadlock pattern.
        product_ids = sorted({item["product_id"] for item in items})

        inventories = {
            inv.product_id: inv
            for inv in Inventory.objects.select_for_update()
            .select_related("product")
            .filter(product_id__in=product_ids)
        }

        missing = set(product_ids) - set(inventories)
        if missing:
            raise ValueError(f"Products {missing} have no inventory records.")

        # Aggregate total qty required per product (handles same product on multiple lines)
        qty_required: dict[int, Decimal] = {}
        for item in items:
            pid = item["product_id"]
            qty = Decimal(str(item["qty"]))
            qty_required[pid] = qty_required.get(pid, Decimal("0")) + qty

        # Oversell guard — checked AFTER acquiring locks so the qty we read is authoritative
        for pid, required in qty_required.items():
            available = inventories[pid].stock_qty
            if available < required:
                product = inventories[pid].product
                raise ValueError(
                    f"Insufficient stock for {product.sku}: " f"need {required}, have {available}."
                )

        # Compute line totals and overall subtotal
        subtotal_paise = 0
        for item in items:
            qty = Decimal(str(item["qty"]))
            line_total = int(qty * item["unit_price_paise"]) - item.get("discount_paise", 0)
            subtotal_paise += line_total

        total_paise = subtotal_paise - discount_paise
        change_paise = max(0, amount_tendered_paise - total_paise)

        # Auto-link this sale to the cashier's current open shift (if any).
        # Shift must be queried INSIDE the atomic block so the lock is held consistently.
        open_shift = (
            Shift.objects.filter(cashier=cashier, closed_at__isnull=True)
            .order_by("-opened_at")
            .first()
        )

        # Create Sale — sale_number starts as a UUID placeholder
        sale = Sale.objects.create(
            cashier=cashier,
            shift=open_shift,
            customer_id=customer_id,
            status=Sale.Status.COMPLETED,
            subtotal_paise=subtotal_paise,
            discount_paise=discount_paise,
            tax_paise=0,
            total_paise=total_paise,
            notes=notes,
        )

        # Replace UUID placeholder with readable sale number derived from PK
        sale.sale_number = _generate_sale_number(sale)
        sale.save(update_fields=["sale_number"])

        # Create SaleItems and apply stock deductions
        for item in items:
            qty = Decimal(str(item["qty"]))
            unit_price = item["unit_price_paise"]
            item_discount = item.get("discount_paise", 0)
            item_subtotal = int(qty * unit_price) - item_discount

            SaleItem.objects.create(
                sale=sale,
                product_id=item["product_id"],
                qty=qty,
                unit_price_paise=unit_price,
                discount_paise=item_discount,
                subtotal_paise=item_subtotal,
            )

            apply_stock_movement(
                product=inventories[item["product_id"]].product,
                movement_type=StockMovement.MovementType.SALE,
                qty_change=-qty,
                reference=sale.sale_number,
                created_by=cashier,
            )

        # Create Payment record
        Payment.objects.create(
            sale=sale,
            method=payment_method,
            amount_tendered_paise=amount_tendered_paise,
            change_paise=change_paise,
        )

    return sale


# ── Shift services ─────────────────────────────────────────────────────────────


def open_shift(*, cashier, opening_float_paise: int = 0, notes: str = "") -> Shift:
    """Open a new shift for the cashier. No validation on concurrent open shifts."""
    return Shift.objects.create(
        cashier=cashier,
        opening_float_paise=opening_float_paise,
        notes=notes,
    )


def close_shift(*, shift: Shift, closing_cash_paise: int, closing_notes: str = "") -> dict:
    """
    Close an open shift. Returns a variance summary dict.
    expected_cash = opening_float + sum of all cash sale totals in this shift.
    """
    from django.db.models import Count, Sum
    from django.db.models.functions import Coalesce

    if shift.closed_at is not None:
        raise ValueError("Shift is already closed.")

    completed = shift.sales.filter(status=Sale.Status.COMPLETED)
    agg = completed.aggregate(
        total_revenue=Coalesce(Sum("total_paise"), 0),
        total_count=Count("id"),
    )
    cash_sales_total = completed.filter(payment__method="cash").aggregate(
        total=Coalesce(Sum("total_paise"), 0)
    )["total"]

    expected_cash_paise = shift.opening_float_paise + cash_sales_total
    variance_paise = closing_cash_paise - expected_cash_paise

    shift.closed_at = timezone.now()
    shift.closing_cash_paise = closing_cash_paise
    shift.closing_notes = closing_notes
    shift.save(update_fields=["closed_at", "closing_cash_paise", "closing_notes"])

    return {
        "opening_float_paise": shift.opening_float_paise,
        "cash_sales_total_paise": cash_sales_total,
        "expected_cash_paise": expected_cash_paise,
        "actual_cash_paise": closing_cash_paise,
        "variance_paise": variance_paise,
        "total_sales": agg["total_count"],
        "total_revenue_paise": agg["total_revenue"],
    }


def void_sale(*, sale: Sale, voided_by) -> Sale:
    """
    Void a completed sale. Caller must verify the user has owner/manager role.
    Writes a RETURN StockMovement for every item — restores stock levels.
    """
    if sale.status == Sale.Status.VOIDED:
        raise ValueError("Sale is already voided.")

    with transaction.atomic():
        for item in sale.items.select_related("product"):
            apply_stock_movement(
                product=item.product,
                movement_type=StockMovement.MovementType.RETURN,
                qty_change=item.qty,
                reference=f"VOID-{sale.sale_number}",
                created_by=voided_by,
            )

        sale.status = Sale.Status.VOIDED
        sale.voided_by = voided_by
        sale.voided_at = timezone.now()
        sale.save(update_fields=["status", "voided_by", "voided_at", "updated_at"])

    return sale
