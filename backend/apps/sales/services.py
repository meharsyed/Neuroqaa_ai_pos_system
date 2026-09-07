from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.catalog.models import Inventory, StockMovement
from apps.catalog.services import apply_stock_movement
from apps.customers.services import post_credit_entry

from apps.accounts.activity import log_activity

from .models import Payment, Sale, SaleItem, SaleItemSerial, Shift


def _credit_reversed_for(sale: Sale) -> int:
    """How much of this credit sale has already been given back (as a positive
    number), so a void after a partial return does not double-refund."""
    from apps.customers.models import CreditLedgerEntry

    total = CreditLedgerEntry.objects.filter(
        sale=sale,
        kind__in=[CreditLedgerEntry.Kind.VOID, CreditLedgerEntry.Kind.RETURN],
    ).aggregate(t=Coalesce(Sum("delta_paise"), 0))["t"]
    return -total


def _credit_charged_for(sale: Sale, kinds: list[str]) -> int:
    """How much of the given kinds this sale put on the khata."""
    from apps.customers.models import CreditLedgerEntry

    return CreditLedgerEntry.objects.filter(sale=sale, kind__in=kinds).aggregate(
        t=Coalesce(Sum("delta_paise"), 0)
    )["t"]


def _generate_sale_number(sale: Sale) -> str:
    """
    Readable, sortable sale number: SALE-YYYYMMDD-NNNNN
    Uses localdate() so the date reflects the shop's timezone (set TIME_ZONE in settings).
    The PK guarantees global uniqueness.
    """
    today = timezone.localdate()
    return f"SALE-{today:%Y%m%d}-{sale.pk:05d}"


def installation_summary(completed) -> dict:
    """
    Installation money across a queryset of sales — what the shop is holding on
    behalf of technicians, and what customers still owe for labour.

    This is not revenue and never appears in the P&L. It is a pass-through the
    owner collects and hands on, so what he needs is simply: how much has come
    in, and how much is still out.
    """
    from django.db.models import Sum
    from django.db.models.functions import Coalesce

    rows = completed.filter(installation_paise__gt=0)
    charged = rows.aggregate(t=Coalesce(Sum("installation_paise"), 0))["t"]

    # Money at the till settles installation first, so what has been collected
    # is min(installation, paid) per bill — summed here in Python because the
    # per-row minimum is not worth a database expression for these volumes.
    collected = sum(r.installation_collected_paise for r in rows)

    return {
        "bill_count": rows.count(),
        "charged_paise": charged,
        "collected_paise": collected,
        "outstanding_paise": charged - collected,
    }


def _cash_taken_paise(completed) -> int:
    """
    Cash that actually went into the drawer across a queryset of sales.

    A bill can be settled by more than one tender now, so this sums the cash
    *tenders* rather than the totals of sales whose method happened to be cash.
    `amount_paise` is what the tender settled — change already handed back is
    the difference between it and `amount_tendered_paise` — so this is the net
    cash in the till.
    """
    from django.db.models import Sum
    from django.db.models.functions import Coalesce

    return Payment.objects.filter(
        sale__in=completed, method=Payment.Method.CASH
    ).aggregate(total=Coalesce(Sum("amount_paise"), 0))["total"]


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
    cash_sales_total = _cash_taken_paise(completed)

    return {
        "opening_float_paise": shift.opening_float_paise,
        "cash_sales_total_paise": cash_sales_total,
        "expected_cash_paise": shift.opening_float_paise + cash_sales_total,
        "total_sales": agg["total_count"],
        "total_revenue_paise": agg["total_revenue"],
    }


def _resolve_tenders(
    *,
    tenders: list[dict] | None,
    payment_method: str,
    amount_tendered_paise: int,
    total_paise: int,
) -> list[dict]:
    """
    Normalise however the caller described payment into a list of tenders.

    Callers may pass a single `payment_method` (the original API, still used
    everywhere) or an explicit `tenders` list for a split payment. Either way
    the result describes only the NON-credit part of the bill — whatever is
    left unsettled becomes the khata remainder.

    Returns [{method, amount_paise, tendered_paise, change_paise}].
    """
    if tenders is None:
        if payment_method == Payment.Method.CREDIT:
            return []                       # the whole bill goes on khata
        return [{
            "method": payment_method,
            "amount_paise": total_paise,
            "tendered_paise": amount_tendered_paise,
            "change_paise": max(0, amount_tendered_paise - total_paise),
        }]

    resolved: list[dict] = []
    for raw in tenders:
        method = raw.get("method")
        if method == Payment.Method.CREDIT:
            raise ValueError(
                "Credit is not a tender — it is whatever the tenders leave unpaid."
            )
        if method not in Payment.Method.values:
            raise ValueError(f"Unknown payment method: {method!r}")

        amount = int(raw.get("amount_paise") or 0)
        if amount <= 0:
            raise ValueError(f"Each payment must be more than zero ({method}).")

        # The API calls it amount_tendered_paise; internal callers use the
        # shorter name. Accept either, and fall back to the amount itself.
        tendered = int(
            raw.get("tendered_paise")
            or raw.get("amount_tendered_paise")
            or amount
        )
        if tendered < amount:
            raise ValueError(
                f"Tendered amount is less than the {method} payment it settles."
            )
        resolved.append({
            "method": method,
            "amount_paise": amount,
            "tendered_paise": tendered,
            # Only cash gives change back; a card is charged for exactly its amount.
            "change_paise": (tendered - amount) if method == Payment.Method.CASH else 0,
        })

    settled = sum(t["amount_paise"] for t in resolved)
    if settled > total_paise:
        raise ValueError(
            f"Payments total Rs {settled / 100:,.2f}, more than the bill of "
            f"Rs {total_paise / 100:,.2f}."
        )
    return resolved


def _resolve_tax(
    *,
    taxable_paise: int,
    tax_pct: Decimal | float | str | None,
    tax_paise: int | None,
) -> tuple[int, Decimal | None]:
    """
    Work out the tax on a bill, and the rate behind it.

    Three ways in, in order of preference:

      tax_pct given      -> compute the amount from the rate. The normal path.
      tax_paise given    -> a flat figure the till typed in; no rate to print.
      neither            -> fall back to the shop's tax_pct setting.

    Returns (amount, rate-or-None). The rate is stored on the sale so a receipt
    prints the percentage that was actually charged rather than whatever the
    setting happens to say when the bill is reprinted years later.
    """
    if tax_pct is not None and str(tax_pct) != "":
        rate = Decimal(str(tax_pct))
        if rate < 0 or rate > 100:
            raise ValueError("A tax rate must be between 0 and 100 percent.")
        # ROUND_HALF_UP to match the JavaScript Math.round the till uses to
        # show the figure — otherwise a bill ending on a half paisa would be
        # quoted to the customer as one number and recorded as another.
        return int(
            (Decimal(taxable_paise) * rate / 100).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        ), rate

    if tax_paise is not None:
        if tax_paise < 0:
            raise ValueError("Tax cannot be negative.")
        if tax_paise > max(0, taxable_paise):
            raise ValueError(
                f"Tax of Rs {tax_paise / 100:,.2f} is more than the bill it is "
                f"charged on (Rs {max(0, taxable_paise) / 100:,.2f})."
            )
        return tax_paise, None

    from apps.config.utils import get_setting

    try:
        rate = Decimal(get_setting("tax_pct", "0") or "0")
    except Exception:
        rate = Decimal("0")
    if rate <= 0:
        return 0, None
    return int(
        (Decimal(taxable_paise) * rate / 100).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    ), rate


def create_sale(
    *,
    cashier,
    items: list[dict],
    payment_method: str = "cash",
    amount_tendered_paise: int = 0,
    discount_paise: int = 0,
    tax_paise: int | None = None,
    tax_pct: Decimal | float | str | None = None,
    installation_paise: int = 0,
    installation_note: str = "",
    notes: str = "",
    customer_id: int | None = None,
    tenders: list[dict] | None = None,
) -> Sale:
    """
    Atomically create a completed sale. All steps are inside one transaction —
    any failure (validation, DB error, crash) rolls back everything.

    items: list of dicts with keys:
        product_id (int), qty (str/Decimal), unit_price_paise (int),
        discount_paise (int, optional — item-level discount),
        serials (list, optional — [{"serial": str, "warranty_months": int | None}])

    Steps:
      1. Lock all inventory rows in deterministic order (sorted by product_id)
         to prevent deadlocks on concurrent sales.
      2. Aggregate qty per product and guard against overselling.
      3. Create Sale, set the readable sale_number from the PK.
      4. Create SaleItem rows and associated SaleItemSerial records.
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

        if installation_paise < 0:
            raise ValueError("An installation charge cannot be negative.")

        # Tax is worked out here, from a rate, against the taxable amount. It
        # used to be whatever number the browser sent, stored without a glance
        # — so tax was already editable by anyone who could craft a request,
        # and the interface was the only thing pretending otherwise.
        taxable_paise = subtotal_paise - discount_paise
        tax_paise, tax_rate = _resolve_tax(
            taxable_paise=taxable_paise,
            tax_pct=tax_pct,
            tax_paise=tax_paise,
        )

        # total_paise stays the GOODS total — it is the revenue figure every
        # report sums, so installation must never be folded into it. What the
        # customer pays is amount_due_paise, and that is what the tenders and
        # the khata work against. Installation is added after tax: labour is
        # not taxed as goods.
        total_paise = subtotal_paise - discount_paise + tax_paise
        amount_due_paise = total_paise + installation_paise
        change_paise = max(0, amount_tendered_paise - amount_due_paise)

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
            tax_paise=tax_paise,
            tax_pct=tax_rate,
            total_paise=total_paise,
            installation_paise=installation_paise,
            installation_note=installation_note,
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

            sale_item = SaleItem.objects.create(
                sale=sale,
                product_id=item["product_id"],
                qty=qty,
                unit_price_paise=unit_price,
                discount_paise=item_discount,
                subtotal_paise=item_subtotal,
            )

            # Create serial records if provided
            serials_data = item.get("serials", [])
            if serials_data:
                for serial_entry in serials_data:
                    SaleItemSerial.objects.create(
                        sale_item=sale_item,
                        serial=serial_entry.get("serial"),
                        warranty_months=serial_entry.get("warranty_months"),
                    )

            apply_stock_movement(
                product=inventories[item["product_id"]].product,
                movement_type=StockMovement.MovementType.SALE,
                qty_change=-qty,
                reference=sale.sale_number,
                created_by=cashier,
            )

        # ── Settle the bill ────────────────────────────────────────────────
        # One or more tenders; anything they leave unpaid goes on the khata.
        resolved = _resolve_tenders(
            tenders=tenders,
            payment_method=payment_method,
            amount_tendered_paise=amount_tendered_paise,
            total_paise=amount_due_paise,
        )
        paid_paise = sum(t["amount_paise"] for t in resolved)
        credit_paise = amount_due_paise - paid_paise

        if credit_paise > 0:
            if not sale.customer:
                raise ValueError(
                    "The unpaid balance would go on khata, which requires a customer."
                )
            # Money taken at the till settles the installation first, so the
            # technician can be paid without waiting for the customer to clear
            # the goods too. Whatever is left of each part goes on the khata as
            # its own entry, so goods debt and labour debt stay tellable apart.
            unpaid_installation = max(0, installation_paise - paid_paise)
            unpaid_goods = credit_paise - unpaid_installation

            # enforce_limit refuses the sale rather than letting the debt grow
            # unbounded. Checked under the customer row lock. Only the part that
            # actually goes on credit counts against the limit — and both parts
            # do, because the customer owes both.
            if unpaid_goods > 0:
                post_credit_entry(
                    customer=sale.customer,
                    kind="sale",
                    delta_paise=unpaid_goods,
                    sale=sale,
                    note=f"Credit sale {sale.sale_number}",
                    created_by=cashier,
                    enforce_limit=True,
                )
            if unpaid_installation > 0:
                post_credit_entry(
                    customer=sale.customer,
                    kind="installation",
                    delta_paise=unpaid_installation,
                    sale=sale,
                    note=(
                        f"Installation on {sale.sale_number}"
                        + (f" — {installation_note}" if installation_note else "")
                    ),
                    created_by=cashier,
                    enforce_limit=True,
                )
            resolved.append({
                "method": Payment.Method.CREDIT,
                "amount_paise": credit_paise,
                "tendered_paise": 0,
                "change_paise": 0,
            })

        for tender in resolved:
            Payment.objects.create(
                sale=sale,
                method=tender["method"],
                amount_paise=tender["amount_paise"],
                amount_tendered_paise=tender["tendered_paise"],
                change_paise=tender["change_paise"],
            )

        sale.amount_paid_paise = paid_paise
        sale.save(update_fields=["amount_paid_paise", "updated_at"])

    log_activity(
        "sale_created",
        user=cashier,
        details={
            "sale_number": sale.sale_number,
            "total_paise": total_paise,
            "installation_paise": installation_paise,
            "items_count": len(items),
            "payment_method": payment_method,
            "amount_paid_paise": sale.amount_paid_paise,
            "credit_paise": sale.credit_paise,
        },
    )
    return sale


# ── Shift services ─────────────────────────────────────────────────────────────


def open_shift(*, cashier, opening_float_paise: int = 0, notes: str = "") -> Shift:
    """Open a new shift for the cashier. No validation on concurrent open shifts."""
    shift = Shift.objects.create(
        cashier=cashier,
        opening_float_paise=opening_float_paise,
        notes=notes,
    )
    log_activity(
        "shift_opened",
        user=cashier,
        details={"shift_id": shift.pk, "opening_float_paise": opening_float_paise},
    )
    return shift


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
    cash_sales_total = _cash_taken_paise(completed)

    expected_cash_paise = shift.opening_float_paise + cash_sales_total
    variance_paise = closing_cash_paise - expected_cash_paise

    shift.closed_at = timezone.now()
    shift.closing_cash_paise = closing_cash_paise
    shift.closing_notes = closing_notes
    shift.save(update_fields=["closed_at", "closing_cash_paise", "closing_notes"])
    log_activity(
        "shift_closed",
        user=shift.cashier,
        details={
            "shift_id": shift.pk,
            "variance_paise": variance_paise,
            "total_sales": agg["total_count"],
            "total_revenue_paise": agg["total_revenue"],
        },
    )

    return {
        "opening_float_paise": shift.opening_float_paise,
        "cash_sales_total_paise": cash_sales_total,
        "expected_cash_paise": expected_cash_paise,
        "actual_cash_paise": closing_cash_paise,
        "variance_paise": variance_paise,
        "total_sales": agg["total_count"],
        "total_revenue_paise": agg["total_revenue"],
    }


def create_return(
    *,
    cashier,
    original_sale: Sale,
    items: list[dict],
    notes: str = "",
) -> Sale:
    """
    Process a partial or full return against an original sale.

    items: [{"product_id": int, "qty": str/Decimal}]
    - Each item must reference a product in the original sale.
    - qty must not exceed what was originally sold.
    - Stock is restored via RETURN StockMovements.
    - Returns a new Sale record with sale_type=RETURN and negative total.
    """
    if original_sale.status == Sale.Status.VOIDED:
        raise ValueError("Cannot return items from a voided sale.")
    if original_sale.sale_type == Sale.SaleType.RETURN:
        raise ValueError("Cannot return a return transaction.")

    original_items = {
        item.product_id: item for item in original_sale.items.select_related("product")
    }

    with transaction.atomic():
        return_subtotal = 0
        validated: list[tuple] = []

        for entry in items:
            pid = entry["product_id"]
            qty = Decimal(str(entry["qty"]))

            if pid not in original_items:
                raise ValueError(f"Product {pid} was not in original sale.")
            original_item = original_items[pid]
            if qty <= 0:
                raise ValueError(f"Return qty must be positive for product {pid}.")
            if qty > original_item.qty:
                raise ValueError(
                    f"Return qty {qty} exceeds original sold qty {original_item.qty} "
                    f"for {original_item.product.sku}."
                )

            line_total = int(qty * original_item.unit_price_paise)
            return_subtotal += line_total
            validated.append((original_item, qty, line_total))

        if not validated:
            raise ValueError("At least one item must be returned.")

        today = timezone.localdate()
        return_number_placeholder = f"TEMP-{timezone.now().timestamp()}"

        return_sale = Sale.objects.create(
            cashier=cashier,
            sale_type=Sale.SaleType.RETURN,
            return_of=original_sale,
            status=Sale.Status.COMPLETED,
            subtotal_paise=-return_subtotal,
            discount_paise=0,
            tax_paise=0,
            total_paise=-return_subtotal,
            notes=notes or f"Return of {original_sale.sale_number}",
        )

        seq = return_sale.pk
        return_sale.sale_number = f"RET-{today:%Y%m%d}-{seq:05d}"
        return_sale.save(update_fields=["sale_number"])

        for original_item, qty, line_total in validated:
            SaleItem.objects.create(
                sale=return_sale,
                product_id=original_item.product_id,
                qty=qty,
                unit_price_paise=original_item.unit_price_paise,
                discount_paise=0,
                subtotal_paise=-line_total,
            )

            apply_stock_movement(
                product=original_item.product,
                movement_type=StockMovement.MovementType.RETURN,
                qty_change=qty,
                reference=return_sale.sale_number,
                created_by=cashier,
            )

        # Returning goods bought on khata reduces what is owed, capped at what
        # is still outstanding against that sale.
        if original_sale.customer and _is_credit_sale(original_sale):
            # Only the part that went on khata can be taken off it. On a split
            # bill — Rs 2,000 cash, Rs 8,000 khata — a return knocks down the
            # khata first, and never by more than the Rs 8,000 that was owed.
            #
            # Goods only: returning a camera does not undo the installation
            # that was already carried out, so labour debt survives a return.
            # A void is different — see void_sale.
            refundable = _credit_charged_for(
                original_sale, ["sale"]
            ) - _credit_reversed_for(original_sale)
            reverse = min(return_subtotal, max(0, refundable))
            if reverse > 0:
                post_credit_entry(
                    customer=original_sale.customer,
                    kind="return",
                    delta_paise=-reverse,
                    sale=original_sale,
                    note=f"Return {return_sale.sale_number} against {original_sale.sale_number}",
                    created_by=cashier,
                )

    log_activity(
        "return_created",
        user=cashier,
        details={
            "return_number": return_sale.sale_number,
            "original_sale": original_sale.sale_number,
            "return_total_paise": -return_sale.total_paise,
            "items_returned": len(validated),
        },
    )
    return return_sale


def _is_credit_sale(sale: Sale) -> bool:
    """True when any part of the sale was put on the customer's khata."""
    return sale.payments.filter(method=Payment.Method.CREDIT).exists()


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

        # Reverse the khata charge. Without this, voiding a credit sale left
        # the customer owing the full amount forever, with no sale to point at.
        if sale.customer and _is_credit_sale(sale):
            # Only the khata portion was ever owed; the cash part of a split
            # bill is refunded at the till, not written off the ledger. A void
            # cancels the whole bill, so unlike a return it clears installation
            # debt as well as goods debt.
            already = sale.credit_paise - _credit_reversed_for(sale)
            if already > 0:
                post_credit_entry(
                    customer=sale.customer,
                    kind="void",
                    delta_paise=-already,
                    sale=sale,
                    note=f"Voided credit sale {sale.sale_number}",
                    created_by=voided_by,
                )

        sale.status = Sale.Status.VOIDED
        sale.voided_by = voided_by
        sale.voided_at = timezone.now()
        sale.save(update_fields=["status", "voided_by", "voided_at", "updated_at"])

    log_activity(
        "sale_voided",
        user=voided_by,
        details={"sale_number": sale.sale_number, "total_paise": sale.total_paise},
    )
    return sale
