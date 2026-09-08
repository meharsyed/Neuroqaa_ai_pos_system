"""
Unified receipt context builder - prepares all data once for any renderer
Guarantees thermal, PDF, and HTML views show identical figures
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any
from zoneinfo import ZoneInfo

from .utils import format_qty

logger = logging.getLogger(__name__)


@dataclass
class Serial:
    """Serial number for a product"""
    serial: str
    warranty_months: int | None = None


@dataclass
class LineItem:
    """Receipt line item"""
    product_name: str
    product_sku: str
    quantity: str  # Decimal, rendered as-is
    unit_price_paise: int
    line_total_paise: int  # qty * unit_price - discount
    discount_paise: int
    serials: List[Serial] | None = None  # Optional serial numbers


@dataclass
class Tender:
    """One way a bill was settled. A bill may have several."""
    method: str  # 'cash', 'card', 'credit', ...
    amount_paise: int
    tendered_paise: int = 0
    change_paise: int = 0

    @property
    def label(self) -> str:
        return {
            "cash": "Cash",
            "card": "Card",
            "bank_transfer": "Bank transfer",
            "cheque": "Cheque",
            "credit": "Khata",
        }.get(self.method, self.method.replace("_", " ").title())


@dataclass
class ReceiptContext:
    """
    Complete receipt data - single source of truth.
    All monetary values are in paise (integer).
    """

    # Identifiers
    sale_id: str
    sale_number: str
    status: str  # 'completed' or 'voided'

    # Dates & times (in Asia/Karachi timezone)
    created_at: datetime
    created_at_formatted: str  # "02 Sep 2026"
    created_at_time: str  # "15:02"

    # Parties
    shop_name: str
    shop_address: str
    shop_phone: str
    shop_email: str
    cashier_name: str
    customer_name: str
    customer_phone: str

    # Items
    items: List[LineItem]

    # Monetary - from stored sale values, never recomputed
    subtotal_paise: int
    item_discounts_paise: int  # sum of all line item discounts
    bill_discount_paise: int  # sale-level discount
    tax_paise: int
    total_paise: int

    # Payment — the primary (largest non-credit) tender, kept for renderers
    # and callers that only ever showed one method.
    tendered_paise: int
    change_paise: int
    payment_method: str  # 'cash', 'card', etc.

    # Settings & customization
    receipt_header: str  # e.g. "A name of Trust, Reliability and Quality!"
    receipt_footer: str  # e.g. "Thank you for your business!"

    # Additional fields for rendering
    tax_pct: float = 0.0  # Tax percentage (e.g. 17.0 for 17%)
    is_return: bool = False  # True if this is a return / credit note
    show_serial_numbers: bool = True  # Whether to display serial numbers on receipt

    # Split settlement. `tenders` lists every way this bill was paid, in the
    # order they were taken; `credit_paise` is whatever went on khata.
    tenders: List["Tender"] = field(default_factory=list)
    amount_paid_paise: int = 0
    credit_paise: int = 0

    # Installation / labour billed on this receipt. The customer pays it, so it
    # sits between the goods total and the amount due — but it is not revenue,
    # and the shop hands it on to the technician.
    installation_paise: int = 0
    installation_note: str = ""

    # The warranty clause, from Settings. Urdu is rendered on the A4/A5
    # invoice and the web bill only — an 80mm thermal printer has no Urdu in
    # its character ROM, so the till slip is always English.
    warranty_en: str = ""
    warranty_ur: str = ""
    warranty_language: str = "en"     # en | ur | both

    @property
    def has_serials(self) -> bool:
        """Whether any line on this bill carries a serial number."""
        return any(i.serials for i in self.items)

    @property
    def has_installation(self) -> bool:
        return self.installation_paise > 0

    @property
    def amount_due_paise(self) -> int:
        """Goods total plus installation — the figure the customer pays."""
        return self.total_paise + self.installation_paise

    @property
    def is_split(self) -> bool:
        """More than one tender — the receipt has to show the breakdown."""
        return len(self.tenders) > 1

    @property
    def is_credit(self) -> bool:
        return self.credit_paise > 0

    @property
    def cash_tenders(self) -> List["Tender"]:
        return [t for t in self.tenders if t.method != "credit"]


def build_receipt_context(sale: Any, shop_settings: Dict[str, str]) -> ReceiptContext:
    """
    Build unified receipt context from a Sale instance and settings.

    Args:
        sale: Sale model instance (has all required fields)
        shop_settings: Dict of shop settings (as from get_setting)

    Returns:
        ReceiptContext with all data needed for any renderer

    Note:
        - All times are converted to Asia/Karachi timezone
        - All monetary fields come from the stored sale, never recomputed
        - Status is checked for 'completed' vs 'voided'
    """

    # Convert created_at to Karachi timezone
    karachi_tz = ZoneInfo("Asia/Karachi")
    if sale.created_at.tzinfo is None:
        # Assume UTC if naive
        created_at_khi = sale.created_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(karachi_tz)
    else:
        created_at_khi = sale.created_at.astimezone(karachi_tz)

    created_at_formatted = created_at_khi.strftime("%d %b %Y")
    created_at_time = created_at_khi.strftime("%H:%M")

    # Build line items from sale.items
    items = []
    for item in sale.items.all():
        # Collect serials if available
        serials = None
        if hasattr(item, 'serials') and item.serials.exists():
            serials = [
                Serial(serial=s.serial, warranty_months=s.warranty_months)
                for s in item.serials.all()
            ]

        line_item = LineItem(
            product_name=item.product.name,
            product_sku=item.product.sku,
            quantity=format_qty(item.qty),  # Remove trailing zeros
            unit_price_paise=item.unit_price_paise,
            line_total_paise=item.subtotal_paise,  # Use stored value, never recompute
            discount_paise=item.discount_paise,
            serials=serials,
        )
        items.append(line_item)

    # Get customer info safely (can be null)
    customer_name = ""
    customer_phone = ""
    if sale.customer:
        customer_name = sale.customer.name or ""
        customer_phone = sale.customer.phone or ""

    # Every tender that settled this bill, in the order they were taken.
    # A sale may have none (nothing recorded), one, or several.
    tenders = [
        Tender(
            method=p.method,
            amount_paise=p.amount_paise,
            tendered_paise=p.amount_tendered_paise,
            change_paise=p.change_paise,
        )
        for p in sale.payments.all()
    ]
    # The primary tender is what a single-method receipt used to show: the
    # largest non-credit one, or the credit line if that is all there is.
    payment = None
    non_credit = [t for t in tenders if t.method != "credit"]
    if non_credit or tenders:
        payment = max(non_credit or tenders, key=lambda t: t.amount_paise)

    credit_paise = sum(t.amount_paise for t in tenders if t.method == "credit")
    amount_paid_paise = sum(t.amount_paise for t in non_credit)

    # Verify item sum matches stored subtotal
    items_sum = sum(item.line_total_paise for item in items)
    if items_sum != (sale.subtotal_paise or 0):
        logger.warning(
            f"Sale {sale.id}: item sum {items_sum} != subtotal {sale.subtotal_paise}"
        )

    # Get tax percentage from settings
    # The rate this bill was charged at, and nothing else. Reading the live
    # shop setting here meant raising the rate silently rewrote the percentage
    # on every past invoice the next time it was printed. Older bills had their
    # own rate derived from their own numbers in migration 0012; where even
    # that was impossible, and where tax was typed as a flat amount, tax_pct is
    # null and no percentage is printed — better nothing than a wrong one.
    tax_pct = float(sale.tax_pct) if getattr(sale, "tax_pct", None) is not None else 0.0

    # Get serial numbers display setting
    show_serial_numbers = shop_settings.get("show_serial_numbers_on_receipt", "true").lower() == "true"

    # Build context
    return ReceiptContext(
        sale_id=str(sale.id),
        sale_number=sale.sale_number,
        status=sale.status or "completed",
        created_at=created_at_khi,
        created_at_formatted=created_at_formatted,
        created_at_time=created_at_time,
        shop_name=shop_settings.get("shop_name", "SPEED TECH SOLUTIONS"),
        shop_address=shop_settings.get("shop_address", "Agha Siraj Complex, Circular Road, Quetta"),
        shop_phone=shop_settings.get("shop_phone", "+92 321 8131109"),
        shop_email=shop_settings.get("shop_email", ""),
        cashier_name=sale.cashier.get_full_name() or sale.cashier.email or "Admin",
        customer_name=customer_name,
        customer_phone=customer_phone,
        items=items,
        subtotal_paise=sale.subtotal_paise or 0,
        item_discounts_paise=sum(item.discount_paise for item in items),
        bill_discount_paise=sale.discount_paise or 0,
        tax_paise=sale.tax_paise or 0,
        total_paise=sale.total_paise or 0,
        tendered_paise=payment.tendered_paise if payment else 0,
        change_paise=payment.change_paise if payment else 0,
        payment_method=payment.method if payment else "cash",
        receipt_header=shop_settings.get("receipt_header", "A name of Trust, Reliability and Quality!"),
        receipt_footer=shop_settings.get("receipt_footer", "Thank you for your business!"),
        tax_pct=tax_pct,
        is_return=sale.sale_type == "return",
        show_serial_numbers=show_serial_numbers,
        tenders=tenders,
        amount_paid_paise=amount_paid_paise,
        credit_paise=credit_paise,
        warranty_en=(
            shop_settings.get("warranty_note_en", "")
            if shop_settings.get("warranty_note_enabled", "true").lower() == "true"
            else ""
        ),
        warranty_ur=(
            shop_settings.get("warranty_note_ur", "")
            if shop_settings.get("warranty_note_enabled", "true").lower() == "true"
            else ""
        ),
        warranty_language=(shop_settings.get("warranty_note_language", "en") or "en").lower(),
        installation_paise=getattr(sale, "installation_paise", 0) or 0,
        installation_note=getattr(sale, "installation_note", "") or "",
    )