"""
80mm / 58mm Thermal Receipt Renderer
ESC/POS text-based output for point-of-sale thermal printers
"""

from typing import Optional
from .context import ReceiptContext
from .utils import format_money, num_to_words_pkr


def _wrap(text: str, width: int) -> list[str]:
    """Break a clause onto roll-width lines without splitting words."""
    import textwrap

    return textwrap.wrap(text, width=max(16, width)) or [""]


def _pad_center(text: str, width: int) -> str:
    """Center text within given width, truncating if needed"""
    text = str(text)[:width]
    padding = max(0, (width - len(text)) // 2)
    return " " * padding + text


def _pad_right(text: str, width: int) -> str:
    """Right-align text within width"""
    text = str(text)[:width]
    padding = max(0, width - len(text))
    return " " * padding + text


def _pad_left(text: str, width: int) -> str:
    """Left-align text within width"""
    return str(text)[:width].ljust(width)


def render_thermal_text(ctx: ReceiptContext, width_mm: int = 80) -> str:
    """
    Render thermal receipt as plaintext (ESC/POS format).

    Args:
        ctx: ReceiptContext with receipt data
        width_mm: 80 or 58mm

    Returns:
        Plain text string formatted for thermal printer (32 or 24 chars per line)
    """

    # Font A: 80mm = 32 chars, 58mm = 24 chars
    char_width = 32 if width_mm == 80 else 24
    sep = "=" * char_width
    sep_dash = "-" * char_width

    lines = []

    # Header (shop name, address, phone, tagline)
    lines.append(_pad_center(ctx.shop_name, char_width))
    if ctx.shop_address:
        lines.append(_pad_center(ctx.shop_address, char_width))
    if ctx.shop_phone:
        lines.append(_pad_center(ctx.shop_phone, char_width))
    if ctx.receipt_header:
        lines.append(_pad_center(ctx.receipt_header, char_width))
    lines.append(sep)

    # Sale info
    lines.append(_pad_left(ctx.sale_number, char_width))
    lines.append(f"{ctx.created_at_formatted}  {ctx.created_at_time}  {ctx.cashier_name}")
    if ctx.customer_name or ctx.customer_phone:
        cust = ctx.customer_name or ctx.customer_phone
        lines.append(f"Customer: {cust}")
    lines.append(sep_dash)

    # Items
    for item in ctx.items:
        # Product name (may wrap)
        lines.append(_pad_left(item.product_name[:char_width], char_width))

        # SKU on same line as qty/amount if space allows
        sku_text = f"  {item.product_sku}"
        if len(sku_text) <= char_width:
            lines.append(_pad_left(sku_text, char_width))

        # Qty x Rate = Amount
        qty_str = f"  {item.quantity} x"
        rate_str = format_money(item.unit_price_paise, include_symbol=False)
        amount_str = format_money(item.line_total_paise, include_symbol=False)

        # Try to fit on one line: "  2 x 22,000.00" + right-aligned amount
        # If not enough space, put on separate line
        qty_rate = f"{qty_str} {rate_str}"
        if len(qty_rate) + len(amount_str) + 2 <= char_width:
            # Single line
            line = qty_rate + _pad_right(amount_str, char_width - len(qty_rate))
            lines.append(line)
        else:
            # Two lines
            lines.append(qty_rate)
            lines.append(_pad_right(amount_str, char_width))

        # Discount line if applicable
        if item.discount_paise > 0:
            disc_str = format_money(item.discount_paise, include_symbol=False)
            lines.append(_pad_left(f"  Discount: -{disc_str}", char_width))

        # Serial numbers if applicable
        if ctx.show_serial_numbers and item.serials:
            for serial in item.serials:
                serial_str = f"  SN: {serial.serial}"
                if serial.warranty_months:
                    serial_str += f" ({serial.warranty_months}m)"
                lines.append(_pad_left(serial_str, char_width))

    lines.append(sep_dash)

    # Totals
    subtotal_str = format_money(ctx.subtotal_paise, include_symbol=False)
    lines.append(f"Subtotal{_pad_right(subtotal_str, char_width - len('Subtotal'))}")

    if ctx.bill_discount_paise > 0:
        disc_str = format_money(ctx.bill_discount_paise, include_symbol=False)
        disc_display = "-" + disc_str
        lines.append(f"Bill discount{_pad_right(disc_display, char_width - len('Bill discount'))}")

    if ctx.tax_paise > 0:
        tax_str = format_money(ctx.tax_paise, include_symbol=False)
        lines.append(f"Tax{_pad_right(tax_str, char_width - len('Tax'))}")

    lines.append(sep)

    # Installation, then the emphasised line the customer pays.
    if ctx.has_installation:
        goods = format_money(ctx.total_paise, include_symbol=False)
        lines.append(f"Goods total{_pad_right(goods, char_width - len('Goods total'))}")
        inst = format_money(ctx.installation_paise, include_symbol=False)
        lines.append(f"Installation{_pad_right(inst, char_width - len('Installation'))}")
        if ctx.installation_note:
            lines.append(f"  ({ctx.installation_note[:char_width - 4]})")

    label = "AMOUNT DUE" if ctx.has_installation else "TOTAL"
    total_str = format_money(ctx.amount_due_paise)
    lines.append(_pad_center(f"{label}  {total_str}", char_width))

    lines.append(sep)

    # Payment — one line per tender, and the khata remainder if any. This
    # used to say "Cash" whatever was actually used.
    for t in ctx.cash_tenders:
        amt = format_money(t.amount_paise, include_symbol=False)
        lines.append(f"{t.label}{_pad_right(amt, char_width - len(t.label))}")

    change = sum(t.change_paise for t in ctx.cash_tenders)
    if change > 0:
        change_str = format_money(change, include_symbol=False)
        lines.append(f"Change{_pad_right(change_str, char_width - len('Change'))}")

    if ctx.credit_paise > 0:
        due = format_money(ctx.credit_paise, include_symbol=False)
        label = "BALANCE DUE (Khata)"
        lines.append(f"{label}{_pad_right(due, char_width - len(label))}")

    lines.append(sep_dash)

    # Warranty conditions. English only — the printer has no Urdu characters —
    # and only when something on the bill actually carries a serial.
    if ctx.warranty_en and ctx.has_serials:
        lines.append(_pad_center("WARRANTY", char_width))
        for chunk in _wrap(ctx.warranty_en, char_width):
            lines.append(chunk)
        lines.append(sep_dash)

    # Footer
    lines.append(_pad_center("Thank you for your business!", char_width))
    lines.append(_pad_center("Goods once sold are", char_width))
    lines.append(_pad_center("returnable within 7 days", char_width))
    lines.append(_pad_center("with this receipt", char_width))
    lines.append("")
    lines.append(_pad_center(f"[QR: {ctx.sale_number}]", char_width))
    lines.append(_pad_center("Powered by Neuroqaa.ai", char_width))
    lines.append("")

    return "\n".join(lines)


def render_thermal_escpos(ctx: ReceiptContext, width_mm: int = 80) -> bytes:
    """
    Generate ESC/POS commands for thermal printer.

    Args:
        ctx: ReceiptContext
        width_mm: 80 or 58mm printer

    Returns:
        Bytes of ESC/POS commands ready to send to printer

    Note:
        This is a simplified version. In production, integrate with python-escpos.
    """
    # For now, return UTF-8 encoded text + feed and cut commands
    text = render_thermal_text(ctx, width_mm)
    commands = text.encode('utf-8')

    # ESC/POS: feed 4 lines and cut
    commands += b"\n\n\n\n"
    commands += b"\x1d\x56\x42\x00"  # GS V m n (cut)

    return commands