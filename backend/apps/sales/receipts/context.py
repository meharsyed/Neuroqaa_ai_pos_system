"""
Unified receipt context builder - prepares all data once for any renderer
Guarantees thermal, PDF, and HTML views show identical figures
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any
from zoneinfo import ZoneInfo
from django.core.exceptions import ObjectDoesNotExist

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

    # Payment
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

    # Get payment info safely (payment may not exist)
    payment = None
    try:
        payment = sale.payment
    except ObjectDoesNotExist:
        pass

    # Verify item sum matches stored subtotal
    items_sum = sum(item.line_total_paise for item in items)
    if items_sum != (sale.subtotal_paise or 0):
        logger.warning(
            f"Sale {sale.id}: item sum {items_sum} != subtotal {sale.subtotal_paise}"
        )

    # Get tax percentage from settings
    tax_pct = float(shop_settings.get("tax_pct", "0")) or 0.0

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
        tendered_paise=payment.amount_tendered_paise if payment else 0,
        change_paise=payment.change_paise if payment else 0,
        payment_method=payment.method if payment else "cash",
        receipt_header=shop_settings.get("receipt_header", "A name of Trust, Reliability and Quality!"),
        receipt_footer=shop_settings.get("receipt_footer", "Thank you for your business!"),
        tax_pct=tax_pct,
        is_return=sale.sale_type == "return",
        show_serial_numbers=show_serial_numbers,
    )