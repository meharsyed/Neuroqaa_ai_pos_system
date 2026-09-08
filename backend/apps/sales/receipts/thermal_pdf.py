"""
80mm / 58mm Thermal Receipt PDF Renderer

Renders ReceiptContext to a continuous thermal roll PDF (no page breaks).
Single column, monochrome, ESC/POS-style layout.
"""

import io
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm as mm_unit
from reportlab.platypus import (
    Paragraph, Table, TableStyle, SimpleDocTemplate, Spacer,
    HRFlowable, Image
)
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing

from .context import ReceiptContext
from .theme import THEME
from .utils import format_money


ROLL_WIDTHS = {80: 72 * mm_unit, 58: 50 * mm_unit}


def render(ctx: ReceiptContext, width_mm: int = 80) -> bytes:
    """
    Render ReceiptContext to a thermal receipt PDF.

    Args:
        ctx: ReceiptContext with all receipt data
        width_mm: 80 or 58 (mm width)

    Returns:
        PDF bytes ready to send to printer or client
    """
    page_w = ROLL_WIDTHS.get(width_mm, ROLL_WIDTHS[80])
    margin = 4 * mm_unit

    buf = io.BytesIO()

    # Measure content height
    story = _build_story(ctx, page_w - 2 * margin)
    content_h = _measure_story_height(story, page_w - 2 * margin)
    page_h = content_h + 2 * margin + 8 * mm_unit

    # Create doc with dynamic page height
    doc = SimpleDocTemplate(
        buf,
        pagesize=(page_w, page_h),
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    doc.build(story)
    return buf.getvalue()


def _build_story(ctx: ReceiptContext, page_width: float):
    """Build the complete thermal receipt story"""
    story = []

    # 1. Logo
    # Logo ONLY. The shop name is printed once, by the block below.
    logo = _get_logo_image(16 * mm_unit)
    if logo:
        story.append(logo)
        story.append(Spacer(1, 2 * mm_unit))

    # 2. Shop info (centered, small)
    story.append(Paragraph(
        ctx.shop_name,
        ParagraphStyle("", fontName="Helvetica-Bold", fontSize=11, textColor=colors.black, alignment=TA_CENTER)
    ))
    story.append(Paragraph(
        ctx.shop_address or "",
        ParagraphStyle("", fontSize=7, textColor=colors.black, alignment=TA_CENTER)
    ))
    story.append(Paragraph(
        ctx.shop_phone or "",
        ParagraphStyle("", fontSize=7, textColor=colors.black, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 2 * mm_unit))

    # 3. Header text (italic)
    story.append(Paragraph(
        ctx.receipt_header or "A name of Trust, Reliability and Quality!",
        ParagraphStyle("", fontSize=7, textColor=colors.black, alignment=TA_CENTER, fontName="Helvetica-Oblique")
    ))

    # 4. Separator rule
    story.append(Spacer(1, 1.5 * mm_unit))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceBefore=0, spaceAfter=1.5*mm_unit))

    # 5. Invoice header
    story.append(Paragraph(
        f"Invoice #{ctx.sale_number}",
        ParagraphStyle("", fontSize=8, textColor=colors.black, alignment=TA_CENTER, fontName="Helvetica-Bold")
    ))
    story.append(Paragraph(
        f"{ctx.created_at_formatted} {ctx.created_at_time}",
        ParagraphStyle("", fontSize=7, textColor=colors.black, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 1.5 * mm_unit))

    # 6. Bill to
    story.append(Paragraph(
        "BILL TO:",
        ParagraphStyle("", fontSize=8, textColor=colors.black, fontName="Helvetica-Bold")
    ))
    customer_name = ctx.customer_name or "Walk-in Customer"
    story.append(Paragraph(
        customer_name,
        ParagraphStyle("", fontSize=8, textColor=colors.black)
    ))
    if ctx.customer_phone:
        story.append(Paragraph(
            ctx.customer_phone,
            ParagraphStyle("", fontSize=7, textColor=colors.black)
        ))
    story.append(Spacer(1, 2 * mm_unit))

    # 7. Items — 2 columns. 72mm cannot hold name + qty + rate + amount on one
    # line, so qty x rate sits under the name and only the amount is columnar.
    nm = ParagraphStyle("", fontSize=8, textColor=colors.black, fontName="Helvetica-Bold", leading=9.5)
    sk = ParagraphStyle("", fontSize=6, textColor=colors.grey, leading=7.5)
    qr_st = ParagraphStyle("", fontSize=7, textColor=colors.black, leading=9)
    se = ParagraphStyle("", fontSize=6, textColor=colors.black, leading=7.5)
    amt = ParagraphStyle("", fontSize=8, textColor=colors.black, alignment=TA_RIGHT, leading=9.5)
    hd = ParagraphStyle("", fontSize=6.5, textColor=colors.black, fontName="Helvetica-Bold")
    hdr = ParagraphStyle("", parent=hd, alignment=TA_RIGHT)

    items_data = [[Paragraph("ITEM", hd), Paragraph("AMOUNT", hdr)]]
    for item in ctx.items:
        cell = [Paragraph(item.product_name, nm), Paragraph(item.product_sku, sk),
                Paragraph(f"{item.quantity} x {format_money(item.unit_price_paise, include_symbol=False)}", qr_st)]
        if getattr(ctx, "show_serial_numbers", True) and item.serials:
            for sn in item.serials:
                w = f" ({sn.warranty_months}m)" if sn.warranty_months else ""
                cell.append(Paragraph(f"S/N {sn.serial}{w}", se))
        items_data.append([cell, Paragraph(format_money(item.line_total_paise, include_symbol=False), amt)])

    items_table = Table(items_data, colWidths=[page_width * 0.68, page_width * 0.32])
    items_table.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, colors.Color(.8, .8, .8)),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 2 * mm_unit))

    # 8. Totals (simple right-aligned list)
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceBefore=0, spaceAfter=1.5*mm_unit))

    totals_data = [
        ["Subtotal:", format_money(ctx.subtotal_paise, include_symbol=False)],
    ]

    if ctx.bill_discount_paise:
        totals_data.append(["Bill Discount:", f"-{format_money(ctx.bill_discount_paise, include_symbol=False)}"])

    if ctx.tax_paise:
        # :g, not :.0f — a bill taxed at 21.5% printed "Tax (22%)" here while
        # the A4 invoice for the same sale said 21.5%. Two documents, one sale,
        # two different rates.
        pct = f" ({ctx.tax_pct:g}%)" if ctx.tax_pct else ""
        totals_data.append([f"Tax{pct}:", format_money(ctx.tax_paise, include_symbol=False)])

    # Installation pushes the emphasised line down to AMOUNT DUE; the goods
    # total becomes an ordinary row above it.
    if ctx.has_installation:
        totals_data.append(["Goods total:", format_money(ctx.total_paise, include_symbol=False)])
        inst_idx = len(totals_data)
        totals_data.append([
            "+ Installation / labour:",
            format_money(ctx.installation_paise, include_symbol=False),
        ])
    else:
        inst_idx = None

    _emph = "AMOUNT DUE:" if ctx.has_installation else "TOTAL:"
    totals_data.append([_emph, f"Rs {format_money(ctx.amount_due_paise, include_symbol=False)}"])

    # One line per tender, so a part-paid bill shows the cash taken AND the
    # khata remainder rather than only one of them.
    cash_tenders = ctx.cash_tenders
    if cash_tenders:
        for t in cash_tenders:
            totals_data.append([
                f"Paid ({t.label.upper()}):",
                format_money(t.amount_paise, include_symbol=False),
            ])
        change = sum(t.change_paise for t in cash_tenders)
        if change:
            totals_data.append(["Change:", format_money(change, include_symbol=False)])
    else:
        totals_data.append(["Paid now:", "0.00"])

    if ctx.credit_paise:
        totals_data.append([
            "BALANCE DUE (Khata):",
            format_money(ctx.credit_paise, include_symbol=False),
        ])

    total_idx = next(i for i, r in enumerate(totals_data) if r[0] == _emph)
    totals_table = Table(totals_data, colWidths=[page_width * 0.46, page_width * 0.54])
    totals_table.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, total_idx), (-1, total_idx), 0.8, colors.black),
        ("LINEBELOW", (0, total_idx), (-1, total_idx), 0.8, colors.black),
        ("FONTNAME", (0, total_idx), (-1, total_idx), "Helvetica-Bold"),
        ("FONTSIZE", (0, total_idx), (-1, total_idx), 10.5),
        ("TOPPADDING", (0, total_idx), (-1, total_idx), 3.5),
        ("BOTTOMPADDING", (0, total_idx), (-1, total_idx), 3.5),
    ] + ([
        ("FONTNAME", (0, len(totals_data) - 1), (-1, len(totals_data) - 1), "Helvetica-Bold"),
        ("LINEBELOW", (0, len(totals_data) - 1), (-1, len(totals_data) - 1), 0.8, colors.black),
    ] if ctx.credit_paise else []) + ([
        # Labour is a different kind of charge from a discount or a tax — it is
        # money passing through to the technician — so it is set apart rather
        # than dropped into the run of adjustment rows.
        ("FONTNAME", (0, inst_idx), (-1, inst_idx), "Helvetica-Bold"),
        ("LINEABOVE", (0, inst_idx), (-1, inst_idx), 0.4, colors.grey),
    ] if inst_idx is not None else [])))
    story.append(totals_table)
    story.append(Spacer(1, 3 * mm_unit))

    # 9. Warranty conditions — English only. A thermal printer's character ROM
    # has no Urdu, so the Urdu clause lives on the A4 invoice and the web bill.
    # Printed only when the bill carries serial numbers: without a serial there
    # is no warranty to void, and roll is not free.
    if ctx.warranty_en and ctx.has_serials:
        story.append(Paragraph(
            f"<b>Warranty:</b> {ctx.warranty_en}",
            ParagraphStyle("warr", fontSize=5.8, textColor=colors.black,
                           alignment=TA_CENTER, leading=7)
        ))
        story.append(Spacer(1, 2 * mm_unit))

    # 10. Return policy / payment method (small text)
    story.append(Paragraph(
        "Goods returnable within 7 days with this receipt.",
        ParagraphStyle("", fontSize=6, textColor=colors.grey, alignment=TA_CENTER, leading=7.5)
    ))
    story.append(Spacer(1, 2 * mm_unit))

    # 10. QR code (small)
    qr_image = _build_qr_code(ctx, 14 * mm_unit)
    qr_tbl = Table([[qr_image]], colWidths=[page_width])
    qr_tbl.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(qr_tbl)
    story.append(Spacer(1, 2 * mm_unit))

    # 11. Footer text and vendor credit
    story.append(Paragraph(
        ctx.receipt_footer or "Thank you for your business!",
        ParagraphStyle("", fontSize=6, textColor=colors.black, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 1 * mm_unit))
    story.append(Paragraph(
        "Powered by Neuroqaa.ai",
        ParagraphStyle("", fontSize=5, textColor=colors.grey, alignment=TA_CENTER)
    ))

    return story


def _measure_story_height(story, page_width: float) -> float:
    """Measure total height of story elements"""
    height = 0
    for element in story:
        if hasattr(element, "height"):
            height += element.height
        elif hasattr(element, "wrap"):
            # For elements that can wrap (Paragraph, etc.)
            w, h = element.wrap(page_width, 10000)
            height += h
        elif element.__class__.__name__ == "Spacer":
            height += element.height
    return height


def _get_logo_image(width: float):
    """Load the thermal logo if present. Resolved relative to this file, not
    settings.BASE_DIR, so the renderer stays usable outside a Django context."""
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("logo-thermal.png", "logo-invoice.png"):
        path = os.path.join(here, "assets", name)
        if os.path.exists(path):
            try:
                img = Image(path, width=width, height=width, kind="proportional")
                img.hAlign = "CENTER"
                return img
            except Exception:
                return None
    return None


def _build_qr_code(ctx: ReceiptContext, size: float):
    """Build QR code for sale number | total | date"""
    try:
        qr_data = f"{ctx.sale_number}|{ctx.total_paise}|{ctx.created_at:%Y-%m-%d}"
        code = qr.QrCodeWidget(qr_data, barBorder=0)
        bounds = code.getBounds()
        d = Drawing(size, size, transform=[size/(bounds[2]-bounds[0]), 0, 0, size/(bounds[3]-bounds[1]), 0, 0])
        d.add(code)
        return d
    except:
        return Paragraph("QR", ParagraphStyle("", fontSize=6, textColor=colors.grey))