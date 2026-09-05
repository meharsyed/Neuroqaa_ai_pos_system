"""
A4 / A5 invoice renderer — Speed Tech Solutions.

Layout rules that must never be broken:
  * Every Table gets hAlign="LEFT" and colWidths that sum to EXACTLY the
    available width. ReportLab centres a table that is wider than its frame,
    so an over-wide table bleeds off BOTH page edges and is clipped.
  * Every row in a table has exactly len(colWidths) cells. A ragged row makes
    ReportLab invent an extra column and the table silently grows.
  * Only two filled blocks per page: the items header and the TOTAL bar.
    Everything else is ink on white — this is printed on paper.
"""

import io
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, Table, TableStyle, SimpleDocTemplate, Spacer, HRFlowable, Image,
)
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing

from .context import ReceiptContext
from .theme import THEME
from .utils import format_money_simple, num_to_words_pkr

# ── Density ────────────────────────────────────────────────────────────────
DENSITY = {
    "a4": dict(base=8.5, small=7, header=7.5, name=13, row_pad=4.0,
               logo=20, margin_x=14, margin_y=12, footer_h=13, qr=20, show_qr=True),
    "a5": dict(base=7.0, small=6, header=6.5, name=11, row_pad=2.6,
               logo=15, margin_x=10, margin_y=9, footer_h=10, qr=15, show_qr=False),
}


def _s(name, **kw):
    return ParagraphStyle(name, **kw)


def _get_logo(width):
    """Logo if present, else None. A missing logo must never break the invoice."""
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in ("assets/logo-invoice.png", "assets/logo-mark.png"):
        path = os.path.join(here, candidate)
        if os.path.exists(path):
            try:
                img = Image(path, width=width, height=width, kind="proportional")
                img.hAlign = "LEFT"
                return img
            except Exception:
                return None
    return None


def render(ctx: ReceiptContext, pagesize: str = "a4") -> bytes:
    d = DENSITY.get(pagesize, DENSITY["a4"])
    psize = A4 if pagesize == "a4" else A5

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=psize,
        leftMargin=d["margin_x"] * mm, rightMargin=d["margin_x"] * mm,
        topMargin=d["margin_y"] * mm,
        bottomMargin=(d["footer_h"] + d["margin_y"]) * mm,
        title=f"Invoice {ctx.sale_number}",
        author=ctx.shop_name,
    )
    W = doc.width

    story = [
        _header(ctx, W, d),
        Spacer(1, 3 * mm),
        HRFlowable(width="100%", thickness=0.9, color=THEME.ACCENT_RULE,
                   spaceBefore=0, spaceAfter=0),
        Spacer(1, 3.5 * mm),
        _bill_and_payment(ctx, W, d),
        Spacer(1, 4 * mm),
        _items(ctx, W, d),
        Spacer(1, 4.5 * mm),
        _notes_and_totals(ctx, W, d),
    ]

    if d["show_qr"]:
        story += [Spacer(1, 7 * mm), _qr_block(ctx, W, d)]

    def _page(canvas, doc_):
        _draw_page_furniture(canvas, doc_, ctx, d)

    doc.build(story, onFirstPage=_page, onLaterPages=_page)
    return buf.getvalue()


# ── Blocks ─────────────────────────────────────────────────────────────────

def _header(ctx, W, d):
    """logo | company | invoice meta — widths sum to exactly W."""
    logo_w = d["logo"] * mm
    logo = _get_logo(logo_w)
    rest = W - (logo_w + 4 * mm if logo else 0)

    company = [
        Paragraph(ctx.shop_name.upper(), _s("n", fontName="Helvetica-Bold",
                  fontSize=d["name"], textColor=THEME.GREEN_800, leading=d["name"] + 2)),
        Spacer(1, 1.2 * mm),
        Paragraph(ctx.shop_address or "", _s("a", fontSize=d["small"],
                  textColor=THEME.NEUTRAL_500, leading=d["small"] + 2.5)),
        Paragraph(" · ".join(x for x in (ctx.shop_phone, ctx.shop_email) if x),
                  _s("p", fontSize=d["small"], textColor=THEME.NEUTRAL_500,
                     leading=d["small"] + 2.5)),
    ]

    # Label and value on ONE right-aligned line — a two-column meta table leaves
    # a wide dead gap between label and value, which is what the client flagged.
    line = _s("mv", fontSize=d["small"], textColor=THEME.NEUTRAL_800,
              alignment=TA_RIGHT, leading=d["small"] + 4)
    grey = THEME.NEUTRAL_500.hexval()[2:]

    def meta_line(label, value):
        return Paragraph(
            f'<font color="#{grey}">{label}</font>&nbsp;&nbsp;<b>{value}</b>', line)

    title = "CREDIT NOTE" if ctx.is_return else "TAX INVOICE"
    meta = [
        Paragraph(title, _s("t", fontName="Helvetica-Bold", fontSize=d["base"] + 1.5,
                            textColor=THEME.TEAL_600, alignment=TA_RIGHT)),
        Spacer(1, 1.8 * mm),
        meta_line("No.", ctx.sale_number),
        meta_line("Date", f"{ctx.created_at_formatted}, {ctx.created_at_time}"),
        meta_line("Cashier", ctx.cashier_name),
    ]
    meta_w = rest * 0.44

    if logo:
        widths = [logo_w, 4 * mm, rest - meta_w - logo_w - 4 * mm, meta_w]
        row = [logo, "", company, meta]
    else:
        widths = [rest - meta_w, meta_w]
        row = [company, meta]

    t = Table([row], colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _bill_and_payment(ctx, W, d):
    lbl = _s("l", fontName="Helvetica-Bold", fontSize=d["small"],
             textColor=THEME.TEAL_600, leading=d["small"] + 3)
    val = _s("v", fontSize=d["base"], textColor=THEME.NEUTRAL_800,
             leading=d["base"] + 2.5)
    mut = _s("m", fontSize=d["small"], textColor=THEME.NEUTRAL_500,
             leading=d["small"] + 2.5)

    bill = [Paragraph("BILL TO", lbl), Spacer(1, 1 * mm),
            Paragraph(ctx.customer_name or "Walk-in Customer", val)]
    if ctx.customer_phone:
        bill.append(Paragraph(ctx.customer_phone, mut))

    method = (ctx.payment_method or "cash").replace("_", " ").title()
    pay = [Paragraph("PAYMENT", lbl), Spacer(1, 1 * mm),
           Paragraph(method, val),
           Paragraph("VOIDED" if ctx.status == "voided" else "Completed",
                     _s("st", fontSize=d["small"],
                        textColor=THEME.DANGER if ctx.status == "voided" else THEME.NEUTRAL_500))]

    t = Table([[bill, pay]], colWidths=[W * 0.62, W * 0.38], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _items(ctx, W, d):
    """Items table. DISC column appears only when a line actually has a discount."""
    show_disc = any(i.discount_paise > 0 for i in ctx.items)

    if show_disc:
        ratios = [0.05, 0.395, 0.075, 0.155, 0.135, 0.19]
        heads = ["#", "DESCRIPTION", "QTY", "RATE", "DISC", "AMOUNT"]
    else:
        ratios = [0.05, 0.475, 0.085, 0.19, 0.20]
        heads = ["#", "DESCRIPTION", "QTY", "RATE", "AMOUNT"]
    ncols = len(ratios)
    widths = [W * r for r in ratios]
    widths[-1] = W - sum(widths[:-1])          # absorb float error — must total W

    th = _s("th", fontName="Helvetica-Bold", fontSize=d["header"],
            textColor=colors.white, leading=d["header"] + 2)
    th_r = _s("thr", parent=th, alignment=TA_RIGHT)
    th_c = _s("thc", parent=th, alignment=TA_CENTER)

    name_st = _s("nm", fontName="Helvetica-Bold", fontSize=d["base"],
                 textColor=THEME.NEUTRAL_800, leading=d["base"] + 2)
    sku_st = _s("sk", fontName="Helvetica", fontSize=d["small"] - 0.5,
                textColor=THEME.NEUTRAL_400, leading=d["small"] + 1.5)
    ser_st = _s("se", fontSize=d["small"] - 0.5, textColor=THEME.TEAL_700,
                leading=d["small"] + 1.5)
    num_st = _s("nu", fontSize=d["base"], textColor=THEME.NEUTRAL_800,
                alignment=TA_RIGHT, leading=d["base"] + 2)
    ctr_st = _s("ct", parent=num_st, alignment=TA_CENTER)
    idx_st = _s("ix", fontSize=d["small"], textColor=THEME.NEUTRAL_400,
                alignment=TA_CENTER, leading=d["base"] + 2)

    header = [Paragraph(heads[0], th_c), Paragraph(heads[1], th),
              Paragraph(heads[2], th_c)] + \
             [Paragraph(h, th_r) for h in heads[3:]]
    data = [header]

    for i, item in enumerate(ctx.items, 1):
        # Description cell holds name + SKU + serials, so a row can never go ragged.
        desc = [Paragraph(item.product_name, name_st),
                Paragraph(item.product_sku, sku_st)]
        if ctx.show_serial_numbers and item.serials:
            for s in item.serials:
                w = f" &nbsp;({s.warranty_months}m warranty)" if s.warranty_months else ""
                desc.append(Paragraph(f"S/N {s.serial}{w}", ser_st))

        row = [Paragraph(str(i), idx_st), desc,
               Paragraph(item.quantity, ctr_st),
               Paragraph(format_money_simple(item.unit_price_paise), num_st)]
        if show_disc:
            row.append(Paragraph(
                format_money_simple(item.discount_paise) if item.discount_paise else "-",
                num_st))
        row.append(Paragraph(format_money_simple(item.line_total_paise), num_st))
        assert len(row) == ncols
        data.append(row)

    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), THEME.GREEN_800),
        ("TOPPADDING", (0, 0), (-1, 0), 4), ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, THEME.TEAL_50]),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, THEME.NEUTRAL_200),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 1), (-1, -1), d["row_pad"]),
        ("BOTTOMPADDING", (0, 1), (-1, -1), d["row_pad"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (0, -1), 2), ("RIGHTPADDING", (-1, 0), (-1, -1), 5),
    ]))
    return t


def _notes_and_totals(ctx, W, d):
    lbl = _s("l", fontName="Helvetica-Bold", fontSize=d["small"],
             textColor=THEME.TEAL_600, leading=d["small"] + 3)
    body = _s("b", fontSize=d["small"], textColor=THEME.NEUTRAL_500,
              leading=d["small"] + 3)

    notes = []
    if ctx.receipt_footer:
        notes += [Paragraph("NOTES", lbl), Spacer(1, 1 * mm),
                  Paragraph(ctx.receipt_footer, body), Spacer(1, 3 * mm)]
    notes += [Paragraph("AMOUNT IN WORDS", lbl), Spacer(1, 1 * mm),
              Paragraph(num_to_words_pkr(ctx.total_paise), body)]

    # ── totals: build rows, remember which index is TOTAL ──
    tl = _s("tl", fontSize=d["base"], textColor=THEME.NEUTRAL_600,
            leading=d["base"] + 3)
    tv = _s("tv", fontSize=d["base"], textColor=THEME.NEUTRAL_800,
            alignment=TA_RIGHT, leading=d["base"] + 3)
    gl = _s("gl", fontName="Helvetica-Bold", fontSize=d["base"] + 2.5,
            textColor=colors.white, leading=d["base"] + 6)
    gv = _s("gv", parent=gl, alignment=TA_RIGHT)

    rows = [[Paragraph("Subtotal", tl),
             Paragraph(format_money_simple(ctx.subtotal_paise), tv)]]
    if ctx.item_discounts_paise:
        rows.append([Paragraph("Item discounts", tl),
                     Paragraph("-" + format_money_simple(ctx.item_discounts_paise), tv)])
    if ctx.bill_discount_paise:
        rows.append([Paragraph("Bill discount", tl),
                     Paragraph("-" + format_money_simple(ctx.bill_discount_paise), tv)])
    if ctx.tax_paise:
        pct = f" ({ctx.tax_pct:g}%)" if ctx.tax_pct else ""
        rows.append([Paragraph(f"Tax{pct}", tl),
                     Paragraph(format_money_simple(ctx.tax_paise), tv)])

    total_idx = len(rows)
    rows.append([Paragraph("TOTAL", gl),
                 Paragraph("Rs " + format_money_simple(ctx.total_paise), gv)])

    method = (ctx.payment_method or "cash").replace("_", " ").title()
    if (ctx.payment_method or "").lower() == "credit":
        # Nothing was tendered — say so, and state the amount now owed.
        due = _s("due", fontName="Helvetica-Bold", fontSize=d["base"],
                 textColor=THEME.WARNING, leading=d["base"] + 3)
        due_r = _s("dur", parent=due, alignment=TA_RIGHT)
        rows.append([Paragraph("Paid now", tl), Paragraph("0.00", tv)])
        rows.append([Paragraph("BALANCE DUE (Khata)", due),
                     Paragraph(format_money_simple(ctx.total_paise), due_r)])
    else:
        rows.append([Paragraph(f"Paid ({method})", tl),
                     Paragraph(format_money_simple(ctx.tendered_paise), tv)])
        if ctx.change_paise:
            rows.append([Paragraph("Change", tl),
                         Paragraph(format_money_simple(ctx.change_paise), tv)])

    tot_w = W * 0.42
    totals = Table(rows, colWidths=[tot_w * 0.52, tot_w * 0.48], hAlign="RIGHT")
    totals.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
        ("LINEBELOW", (0, 0), (-1, total_idx - 1), 0.4, THEME.NEUTRAL_200),
        # the ONLY filled row, targeted by computed index — never (0,-1)
        ("BACKGROUND", (0, total_idx), (-1, total_idx), THEME.GREEN_800),
        ("TOPPADDING", (0, total_idx), (-1, total_idx), 5),
        ("BOTTOMPADDING", (0, total_idx), (-1, total_idx), 5),
    ]))

    layout = Table([[notes, totals]],
                   colWidths=[W - tot_w - 10 * mm, tot_w + 10 * mm], hAlign="LEFT")
    layout.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return layout


def _qr_block(ctx, W, d):
    size = d["qr"] * mm
    code = qr.QrCodeWidget(
        f"{ctx.sale_number}|{ctx.total_paise}|{ctx.created_at_formatted}")
    b = code.getBounds()
    dr = Drawing(size, size, transform=[size / (b[2] - b[0]), 0, 0,
                                        size / (b[3] - b[1]), 0, 0])
    dr.add(code)
    cap = Paragraph("Scan to verify<br/>this bill",
                    _s("q", fontSize=d["small"] - 0.5, textColor=THEME.NEUTRAL_400,
                       leading=d["small"] + 1))
    t = Table([[dr, cap]], colWidths=[size + 3 * mm, W - size - 3 * mm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


# ── Page furniture ─────────────────────────────────────────────────────────

def _draw_page_furniture(canvas, doc, ctx, d):
    canvas.saveState()
    pw, ph = doc.pagesize

    # top accent bar
    canvas.setFillColor(THEME.GREEN_800)
    canvas.rect(0, ph - 4 * mm, pw, 4 * mm, stroke=0, fill=1)

    # footer band
    fh = d["footer_h"] * mm
    canvas.setFillColor(THEME.TEAL_50)
    canvas.rect(0, 0, pw, fh, stroke=0, fill=1)
    canvas.setStrokeColor(THEME.TEAL_600)
    canvas.setLineWidth(1.1)
    canvas.line(0, fh, pw, fh)

    mx = d["margin_x"] * mm
    canvas.setFillColor(THEME.TEAL_800)
    canvas.setFont("Helvetica-Bold", d["small"])
    canvas.drawString(mx, fh / 2 - 1, ctx.receipt_header or ctx.shop_name)
    canvas.setFont("Helvetica", d["small"] - 0.5)
    canvas.setFillColor(THEME.NEUTRAL_500)
    canvas.drawRightString(pw - mx, fh / 2 - 1, f"Page {doc.page}")

    if ctx.status == "voided":
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 96)
        canvas.setFillColor(colors.Color(0.71, 0.14, 0.09, alpha=0.11))
        canvas.translate(pw / 2, ph / 2)
        canvas.rotate(35)
        canvas.drawCentredString(0, 0, "VOID")
        canvas.restoreState()

    canvas.restoreState()
