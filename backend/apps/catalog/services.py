from decimal import Decimal

from django.db import transaction

from .models import Inventory, Product, StockMovement


def apply_stock_movement(
    *,
    product: Product,
    movement_type: str,
    qty_change: Decimal,
    cost_price_paise: int | None = None,
    reference: str = "",
    notes: str = "",
    created_by=None,
) -> StockMovement:
    """
    Atomically update Inventory.stock_qty and append a StockMovement row.

    This is the ONLY correct way to change stock levels. Never set
    inventory.stock_qty directly — that skips the audit trail.

    Uses SELECT FOR UPDATE so concurrent requests don't race each other.
    Both writes are inside one transaction, so a crash mid-way leaves no
    inconsistency between Inventory and StockMovement.
    """
    if not isinstance(qty_change, Decimal):
        qty_change = Decimal(str(qty_change))

    with transaction.atomic():
        inventory = Inventory.objects.select_for_update().get(product=product)
        new_qty = inventory.stock_qty + qty_change
        inventory.stock_qty = new_qty
        inventory.save(update_fields=["stock_qty", "updated_at"])

        movement = StockMovement(
            tenant_id=product.tenant_id,
            product=product,
            movement_type=movement_type,
            qty_change=qty_change,
            qty_after=new_qty,
            cost_price_paise=cost_price_paise,
            reference=reference,
            notes=notes,
            created_by=created_by,
        )
        movement.save()

    return movement


def set_opening_stock(
    *,
    product: Product,
    qty: Decimal,
    cost_price_paise: int | None = None,
    created_by=None,
) -> StockMovement:
    """
    Set the initial stock level for a newly created product.
    Raises ValueError if the product already has stock — use apply_stock_movement instead.
    """
    if not isinstance(qty, Decimal):
        qty = Decimal(str(qty))

    inventory = Inventory.objects.get(product=product)
    if inventory.stock_qty != Decimal("0"):
        raise ValueError(
            f"Product {product.sku} already has stock ({inventory.stock_qty}). "
            "Use apply_stock_movement for subsequent adjustments."
        )

    return apply_stock_movement(
        product=product,
        movement_type=StockMovement.MovementType.OPENING,
        qty_change=qty,
        cost_price_paise=cost_price_paise,
        created_by=created_by,
    )
