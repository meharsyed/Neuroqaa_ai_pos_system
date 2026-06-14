"""
Receipt rendering: plain-text (ESC/POS-ready) and PDF (ReportLab 80 mm).
Thermal network printing is done via python-escpos when available.
"""

import io

from apps.catalog.money import Money
from apps.config.utils import get_setting

# ── Formatting helpers ─────────────────────────────────────────────────────────


def _fmt_qty(qty) -> str:
    """Remove trailing zeros from a Decimal qty: 3.000 → '3', 1.500 → '1.5'"""
    return f"{qty:.3f}".rstrip("0").rstrip(".")


def _money_cell(paise: int) -> str:
    """Compact money for table cells — drops .00 for whole-rupee amounts."""
    rupees = paise / 100
    if paise % 100 == 0:
        return f"Rs.{int(rupees):,}"
    return f"Rs.{rupees:,.2f}"


def _money_full(paise: int) -> str:
    """Full money string always showing two decimal places."""
    return f"Rs. {paise / 100:,.2f}"


# ── Text receipt ───────────────────────────────────────────────────────────────


def render_text_receipt(sale) -> str:
    """
    Returns a plain-text receipt string formatted for a thermal printer.
    Width is read from the `receipt_width` setting (default 48 chars).
    """
    width = int(get_setting("receipt_width", "48"))
    shop_name = get_setting("shop_name", "POS")
    shop_address = get_setting("shop_address", "")
    shop_phone = get_setting("shop_phone", "")
    header_text = get_setting("receipt_header", "")
    footer_text = get_setting("receipt_footer", "Thank you for your business!")

    lines: list[str] = []

    def centre(text: str) -> str:
        return text.center(width)

    def rule() -> str:
        return "-" * width

    def lr(left: str, right: str) -> str:
        gap = width - len(left) - len(right)
        if gap < 1:
            gap = 1
        return left + " " * gap + right

    lines.append(centre(shop_name))
    if shop_address:
        lines.append(centre(shop_address))
    if shop_phone:
        lines.append(centre(shop_phone))
    if header_text:
        lines.append(centre(header_text))
    lines.append(rule())
    lines.append(lr("Receipt:", sale.sale_number))
    lines.append(lr("Date:", sale.created_at.strftime("%Y-%m-%d %H:%M")))
    lines.append(lr("Cashier:", sale.cashier.get_full_name() or sale.cashier.email))
    lines.append(rule())

    for item in sale.items.select_related("product"):
        name = f"{item.product.sku} {item.product.name}"
        if len(name) > width - 1:
            name = name[: width - 1]
        lines.append(name)
        qty_price = f"  {_fmt_qty(item.qty)} x {str(Money(item.unit_price_paise))}"
        lines.append(lr(qty_price, str(Money(item.subtotal_paise))))
        if item.discount_paise:
            lines.append(lr("  Discount", f"- {str(Money(item.discount_paise))}"))

    lines.append(rule())
    lines.append(lr("Subtotal", str(Money(sale.subtotal_paise))))
    if sale.discount_paise:
        lines.append(lr("Discount", f"- {str(Money(sale.discount_paise))}"))
    if sale.tax_paise:
        lines.append(lr("Tax", str(Money(sale.tax_paise))))
    lines.append(rule())
    lines.append(lr("TOTAL", str(Money(sale.total_paise))))
    lines.append(rule())

    if hasattr(sale, "payment"):
        p = sale.payment
        lines.append(lr(f"Paid ({p.method.upper()})", str(Money(p.amount_tendered_paise))))
        if p.change_paise:
            lines.append(lr("Change", str(Money(p.change_paise))))

    lines.append(rule())
    if footer_text:
        lines.append(centre(footer_text))
    lines.append("")
    lines.append("")

    return "\n".join(lines)


# ── PDF receipt ────────────────────────────────────────────────────────────────


def render_pdf_receipt(sale) -> bytes:
    """
    Returns raw PDF bytes for an 80 mm thermal receipt.
    Requires reportlab.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm as mm_unit
        from reportlab.platypus import (
            HRFlowable,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise RuntimeError("reportlab is not installed. Run: pip install reportlab") from exc

    shop_name = get_setting("shop_name", "POS")
    shop_address = get_setting("shop_address", "")
    shop_phone = get_setting("shop_phone", "")
    header_text = get_setting("receipt_header", "")
    footer_text = get_setting("receipt_footer", "Thank you for your purchase!")

    page_w = 80 * mm_unit
    margin = 6 * mm_unit
    cw = page_w - 2 * margin  # usable content width ≈ 68 mm

    gray = colors.HexColor("#555555")
    lgray = colors.HexColor("#999999")
    amber = colors.HexColor("#B45309")
    black = colors.black

    def ps(name, **kw):
        defaults = {"fontName": "Helvetica", "fontSize": 8, "leading": 11, "alignment": TA_LEFT}
        defaults.update(kw)
        return ParagraphStyle(name, **defaults)

    s_shop = ps("sh", fontName="Helvetica-Bold", fontSize=13, leading=16, alignment=TA_CENTER)
    s_sub = ps("su", fontSize=8, leading=11, alignment=TA_CENTER)
    s_tagline = ps(
        "tg",
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        alignment=TA_CENTER,
        textColor=gray,
    )
    s_mlbl = ps("ml", fontName="Helvetica-Bold", fontSize=8, leading=11)
    s_mval = ps("mv", fontSize=8, leading=11)
    s_chdr = ps("ch", fontName="Helvetica-Bold", fontSize=7.5, leading=10)
    s_chdr_r = ps("cr", fontName="Helvetica-Bold", fontSize=7.5, leading=10, alignment=TA_RIGHT)
    s_iname = ps("in", fontName="Helvetica-Bold", fontSize=8, leading=10)
    s_isku = ps("is", fontSize=7, leading=9, textColor=gray)
    s_idisc = ps("id", fontName="Helvetica-Oblique", fontSize=7, leading=9, textColor=amber)
    s_num = ps("nm", fontSize=7.5, leading=10, alignment=TA_RIGHT)
    s_tlbl = ps("tl", fontSize=8, leading=11)
    s_tval = ps("tv", fontSize=8, leading=11, alignment=TA_RIGHT)
    s_grand_l = ps("gl", fontName="Helvetica-Bold", fontSize=10, leading=13)
    s_grand_v = ps("gv", fontName="Helvetica-Bold", fontSize=10, leading=13, alignment=TA_RIGHT)
    s_pay_l = ps("pl", fontName="Helvetica-Bold", fontSize=8.5, leading=12)
    s_pay_v = ps("pv", fontName="Helvetica-Bold", fontSize=8.5, leading=12, alignment=TA_RIGHT)
    s_change = ps("cg", fontName="Helvetica-Bold", fontSize=10, leading=13)
    s_change_v = ps("cv", fontName="Helvetica-Bold", fontSize=10, leading=13, alignment=TA_RIGHT)
    s_footer = ps("ft", fontSize=8, leading=12, alignment=TA_CENTER)
    s_dev = ps(
        "dv",
        fontName="Helvetica-Oblique",
        fontSize=7,
        leading=10,
        alignment=TA_CENTER,
        textColor=lgray,
    )
    s_devbold = ps(
        "db",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        alignment=TA_CENTER,
        textColor=gray,
    )

    def hr(thickness=0.5, color=black, before=3, after=3):
        return HRFlowable(
            width="100%", thickness=thickness, color=color, spaceBefore=before, spaceAfter=after
        )

    story = []

    # ── Shop header ────────────────────────────────────────────────────────
    story.append(Paragraph(shop_name, s_shop))
    if shop_address:
        story.append(Paragraph(shop_address, s_sub))
    if shop_phone:
        story.append(Paragraph(shop_phone, s_sub))
    if header_text:
        story.append(Spacer(1, 2))
        story.append(Paragraph(header_text, s_tagline))
    story.append(hr(thickness=1, before=5, after=4))

    # ── Sale meta ─────────────────────────────────────────────────────────
    cashier_name = sale.cashier.get_full_name() or sale.cashier.email
    meta_data = [
        [Paragraph("Receipt No:", s_mlbl), Paragraph(sale.sale_number, s_mval)],
        [
            Paragraph("Date:", s_mlbl),
            Paragraph(sale.created_at.strftime("%d %b %Y  %H:%M"), s_mval),
        ],
        [Paragraph("Cashier:", s_mlbl), Paragraph(cashier_name, s_mval)],
    ]
    meta_tbl = Table(meta_data, colWidths=[cw * 0.33, cw * 0.67])
    meta_tbl.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(meta_tbl)
    story.append(hr(before=4, after=4))

    # ── Items table ───────────────────────────────────────────────────────
    # Columns: Item name+sku | Qty | Rate | Amount
    # Widths:    42%          | 11% | 23%  | 24%
    col_w = [cw * 0.42, cw * 0.11, cw * 0.23, cw * 0.24]

    rows = [
        [
            Paragraph("ITEM", s_chdr),
            Paragraph("QTY", s_chdr_r),
            Paragraph("RATE", s_chdr_r),
            Paragraph("AMOUNT", s_chdr_r),
        ]
    ]

    items = list(sale.items.select_related("product"))
    for item in items:
        cell_flows = [
            Paragraph(item.product.name, s_iname),
            Paragraph(item.product.sku, s_isku),
        ]
        if item.discount_paise and item.discount_paise > 0:
            gross = int(item.qty * item.unit_price_paise) or 1
            disc_pct = round(item.discount_paise * 100 / gross)
            cell_flows.append(Paragraph(f"{disc_pct}% disc applied", s_idisc))

        rows.append(
            [
                cell_flows,
                Paragraph(_fmt_qty(item.qty), s_num),
                Paragraph(_money_cell(item.unit_price_paise), s_num),
                Paragraph(_money_cell(item.subtotal_paise), s_num),
            ]
        )

    items_tbl = Table(rows, colWidths=col_w)
    items_tbl.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, black),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(items_tbl)
    story.append(hr(before=4, after=3))

    # ── Totals ────────────────────────────────────────────────────────────
    # Show item-level discount summary if any items have discounts
    items_disc_total = sum(i.discount_paise for i in items if i.discount_paise)

    totals_rows = []
    gross_subtotal = sale.subtotal_paise + items_disc_total
    if items_disc_total:
        totals_rows.append(
            [
                Paragraph(
                    f"Gross subtotal ({len(items)} item{'s' if len(items) != 1 else ''})", s_tlbl
                ),
                Paragraph(_money_full(gross_subtotal), s_tval),
            ]
        )
        totals_rows.append(
            [
                Paragraph("Item discounts", s_tlbl),
                Paragraph(f"- {_money_full(items_disc_total)}", s_tval),
            ]
        )
    else:
        totals_rows.append(
            [
                Paragraph(f"Subtotal ({len(items)} item{'s' if len(items) != 1 else ''})", s_tlbl),
                Paragraph(_money_full(sale.subtotal_paise), s_tval),
            ]
        )
    if sale.discount_paise:
        totals_rows.append(
            [
                Paragraph("Bill discount", s_tlbl),
                Paragraph(f"- {_money_full(sale.discount_paise)}", s_tval),
            ]
        )
    if sale.tax_paise:
        totals_rows.append(
            [
                Paragraph("Tax", s_tlbl),
                Paragraph(_money_full(sale.tax_paise), s_tval),
            ]
        )

    # TOTAL row index
    total_row_idx = len(totals_rows)
    totals_rows.append(
        [
            Paragraph("TOTAL", s_grand_l),
            Paragraph(_money_full(sale.total_paise), s_grand_v),
        ]
    )

    # Payment rows
    pay_row_idx = len(totals_rows)
    if hasattr(sale, "payment"):
        p = sale.payment
        totals_rows.append(
            [
                Paragraph(f"Paid ({p.method.upper()})", s_pay_l),
                Paragraph(_money_full(p.amount_tendered_paise), s_pay_v),
            ]
        )
        if p.change_paise:
            totals_rows.append(
                [
                    Paragraph("Change", s_change),
                    Paragraph(_money_full(p.change_paise), s_change_v),
                ]
            )

    totals_tbl = Table(totals_rows, colWidths=[cw * 0.58, cw * 0.42])
    style_cmds = [
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Thick line above TOTAL row
        ("LINEABOVE", (0, total_row_idx), (-1, total_row_idx), 1.0, black),
        ("LINEBELOW", (0, total_row_idx), (-1, total_row_idx), 0.5, black),
        ("TOPPADDING", (0, total_row_idx), (-1, total_row_idx), 3),
        ("BOTTOMPADDING", (0, total_row_idx), (-1, total_row_idx), 4),
    ]
    if pay_row_idx < len(totals_rows):
        style_cmds.append(("LINEABOVE", (0, pay_row_idx), (-1, pay_row_idx), 0.3, lgray))
    totals_tbl.setStyle(TableStyle(style_cmds))
    story.append(totals_tbl)

    # ── Footer message ────────────────────────────────────────────────────
    story.append(Spacer(1, 10))
    if footer_text:
        story.append(Paragraph(footer_text, s_footer))
        story.append(Spacer(1, 10))

    # ── Developer / system branding ───────────────────────────────────────
    story.append(hr(thickness=0.3, color=lgray, before=4, after=6))
    story.append(Paragraph("Powered by Neuroqaa.ai POS", s_devbold))
    story.append(Paragraph("Neuroqaa.ai Pvt. Ltd. &mdash; Modern POS for Modern Businesses", s_dev))
    story.append(Paragraph("Sales &amp; Support: 0333-1445252", s_dev))
    story.append(Paragraph("www.neuroqaa.ai", s_dev))
    story.append(Spacer(1, 8))

    # ── Build with estimated dynamic height ───────────────────────────────
    buf = io.BytesIO()
    estimated_h = (140 + len(items) * 14) * mm_unit
    doc = SimpleDocTemplate(
        buf,
        pagesize=(page_w, estimated_h),
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )
    doc.build(story)
    return buf.getvalue()


# ── Thermal network printing ───────────────────────────────────────────────────


def print_receipt_network(sale, ip: str | None = None, port: int | None = None) -> None:
    """
    Send a text receipt to a network ESC/POS printer.
    Requires python-escpos (pip install python-escpos).
    Falls back to get_setting for ip/port when not supplied.
    """
    try:
        from escpos.printer import Network as EscNetwork
    except ImportError as exc:
        raise RuntimeError(
            "python-escpos is not installed. Run: pip install python-escpos"
        ) from exc

    printer_ip = ip or get_setting("thermal_printer_ip", "")
    printer_port = port or int(get_setting("thermal_printer_port", "9100"))

    if not printer_ip:
        raise ValueError(
            "Thermal printer IP not configured. Set it in Settings → thermal_printer_ip."
        )

    text = render_text_receipt(sale)
    printer = EscNetwork(printer_ip, printer_port)
    try:
        printer.text(text)
        printer.cut()
    finally:
        printer.close()
