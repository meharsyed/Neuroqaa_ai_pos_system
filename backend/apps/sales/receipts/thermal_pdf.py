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
        totals_data.append([f"Tax ({ctx.tax_pct:.0f}%):", format_money(ctx.tax_paise, include_symbol=False)])

    totals_data.append(["TOTAL:", f"Rs {format_money(ctx.total_paise, include_symbol=False)}"])

    if ctx.tendered_paise:
        totals_data.append([f"Paid ({(ctx.payment_method or 'CASH').upper()}):", format_money(ctx.tendered_paise, include_symbol=False)])

    if ctx.change_paise:
        totals_data.append(["Change:", format_money(ctx.change_paise, include_symbol=False)])

    total_idx = next(i for i, r in enumerate(totals_data) if r[0] == "TOTAL:")
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
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 3 * mm_unit))

    # 9. Return policy / payment method (small text)
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
    """Try to load logo image, return None if missing"""
    try:
        from django.conf import settings
        import os
        logo_path = os.path.join(settings.BASE_DIR, "apps", "sales", "receipts", "assets", "logo-thermal.png")
        if os.path.exists(logo_path):
            return Image(logo_path, width=width, height=width, kind="proportional")
    except:
        pass
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