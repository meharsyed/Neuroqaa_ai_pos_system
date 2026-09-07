"""
The printed quotation.

Shares the invoice's typography and rule work so the two documents look like
they came from the same shop, but says QUOTATION at the top and carries no
invoice number — a quotation is not a tax document and must not be mistakable
for one.
"""

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .document import _get_logo, _s
from .theme import THEME
from .utils import format_money_simple, num_to_words_pkr


def _fmt_qty(q) -> str:
    s = f"{q:.3f}".rstrip("0").rstrip(".")
    return s or "0"


def render_quotation_pdf(quotation) -> bytes:
    from apps.config.utils import get_all_settings

    shop = get_all_settings()
    profile = quotation.profile

    # The letterhead: the chosen business profile, falling back to the shop's
    # own details when a quotation was raised without one.
    name = (profile.name if profile else "") or shop.get("shop_name", "Speed Tech Solutions")
    address = (profile.address if profile else "") or shop.get("shop_address", "")
    phone = (profile.phone if profile else "") or shop.get("shop_phone", "")
    email = (profile.email if profile else "") or shop.get("shop_email", "")
    tax_no = profile.tax_number if profile else ""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=13 * mm, bottomMargin=18 * mm,
        title=f"Quotation {quotation.display_number}", author=name,
    )
    W = doc.width
    base, small = 8.6, 7.4

    lbl = _s("qlbl", fontName="Helvetica-Bold", fontSize=small - 0.4,
             textColor=THEME.TEAL_600, leading=small + 2)
    val = _s("qval", fontSize=base, textColor=THEME.NEUTRAL_800, leading=base + 2.5)
    mut = _s("qmut", fontSize=small, textColor=THEME.NEUTRAL_500, leading=small + 2.5)
    shop_name = _s("qshop", fontName="Helvetica-Bold", fontSize=base + 5.5,
                   textColor=THEME.GREEN_800, leading=base + 8)
    kind = _s("qkind", fontName="Helvetica-Bold", fontSize=base + 3.5,
              textColor=THEME.TEAL_600, alignment=TA_RIGHT, leading=base + 6)
    meta = _s("qmeta", fontSize=small, textColor=THEME.NEUTRAL_500,
              alignment=TA_RIGHT, leading=small + 3)

    # ── Header ─────────────────────────────────────────────────────────────
    ident = [Paragraph(name, shop_name)]
    if address:
        ident.append(Paragraph(address.replace("\n", "<br/>"), mut))
    contact = " · ".join(x for x in (phone, email) if x)
    if contact:
        ident.append(Paragraph(contact, mut))
    if tax_no:
        ident.append(Paragraph(f"NTN / STRN: {tax_no}", mut))

    valid_until = quotation.valid_until
    right = [
        Paragraph("QUOTATION", kind),
        Spacer(1, 1.5 * mm),
        Paragraph(f"No. <b>{quotation.display_number}</b>", meta),
        Paragraph(f"Date <b>{quotation.created_at:%d %b %Y}</b>", meta),
    ]
    if valid_until:
        right.append(Paragraph(f"Valid until <b>{valid_until:%d %b %Y}</b>", meta))
    author = quotation.created_by.get_full_name() or quotation.created_by.email
    right.append(Paragraph(f"Prepared by <b>{author}</b>", meta))

    logo = _get_logo(20 * mm)
    head_cells = ([logo, ident, right] if logo else [ident, right])
    head_widths = ([22 * mm, W * 0.44 - 11 * mm, W * 0.56 - 11 * mm]
                   if logo else [W * 0.55, W * 0.45])
    header = Table([head_cells], colWidths=head_widths, hAlign="LEFT")
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    story = [
        header,
        Spacer(1, 3 * mm),
        HRFlowable(width="100%", thickness=0.9, color=THEME.TEAL_600, spaceAfter=0),
        Spacer(1, 3.5 * mm),
    ]

    # ── Who it is for ──────────────────────────────────────────────────────
    to_name = quotation.customer_name or (
        quotation.customer.display_name if quotation.customer else "—"
    )
    to = [Paragraph("QUOTATION FOR", lbl), Spacer(1, 1 * mm), Paragraph(to_name, val)]
    if quotation.customer_phone or (quotation.customer and quotation.customer.phone):
        to.append(Paragraph(
            quotation.customer_phone or quotation.customer.phone, mut))
    if quotation.customer_address:
        to.append(Paragraph(quotation.customer_address.replace("\n", "<br/>"), mut))

    story += [Table([[to]], colWidths=[W], hAlign="LEFT",
                    style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                                      ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                      ("TOPPADDING", (0, 0), (-1, -1), 0),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 0)])),
              Spacer(1, 4 * mm)]

    # ── Lines ──────────────────────────────────────────────────────────────
    th = _s("qth", fontName="Helvetica-Bold", fontSize=small - 0.3,
            textColor=colors.white, leading=small + 2)
    th_r = _s("qthr", parent=th, alignment=TA_RIGHT)
    cell = _s("qcell", fontName="Helvetica-Bold", fontSize=base,
              textColor=THEME.NEUTRAL_800, leading=base + 2)
    cell_r = _s("qcellr", fontSize=base, textColor=THEME.NEUTRAL_800,
                alignment=TA_RIGHT, leading=base + 2)
    sub = _s("qsub", fontSize=small - 0.4, textColor=THEME.NEUTRAL_500, leading=small + 1)

    ratios = [0.06, 0.46, 0.12, 0.18, 0.18]
    widths = [W * r for r in ratios]

    rows = [[Paragraph("#", th), Paragraph("DESCRIPTION", th),
             Paragraph("QTY", th_r), Paragraph("RATE", th_r), Paragraph("AMOUNT", th_r)]]
    for i, item in enumerate(quotation.items.all(), start=1):
        desc = [Paragraph(item.name, cell)]
        if item.sku:
            desc.append(Paragraph(item.sku, sub))
        if item.description:
            desc.append(Paragraph(item.description, sub))
        if item.is_off_catalogue:
            # Says plainly that this is supplied work rather than a shelf item.
            desc.append(Paragraph("Supplied / arranged to order", sub))
        qty = _fmt_qty(item.qty) + (f" {item.unit}" if item.unit else "")
        rows.append([
            Paragraph(str(i), sub), desc,
            Paragraph(qty, cell_r),
            Paragraph(format_money_simple(item.unit_price_paise), cell_r),
            Paragraph(format_money_simple(item.line_total_paise), cell_r),
        ])

    table = Table(rows, colWidths=widths, hAlign="LEFT", repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), THEME.GREEN_800),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, THEME.TEAL_50]),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, THEME.NEUTRAL_200),
    ]))
    story += [table, Spacer(1, 4.5 * mm)]

    # ── Totals ─────────────────────────────────────────────────────────────
    tl = _s("qtl", fontSize=base, textColor=THEME.NEUTRAL_600, leading=base + 3)
    tv = _s("qtv", fontSize=base, textColor=THEME.NEUTRAL_800,
            alignment=TA_RIGHT, leading=base + 3)
    gl = _s("qgl", fontName="Helvetica-Bold", fontSize=base + 2.5,
            textColor=colors.white, leading=base + 6)
    gv = _s("qgv", parent=gl, alignment=TA_RIGHT)

    trows = [[Paragraph("Subtotal", tl),
              Paragraph(format_money_simple(quotation.subtotal_paise), tv)]]
    if quotation.discount_paise:
        trows.append([Paragraph("Discount", tl),
                      Paragraph("-" + format_money_simple(quotation.discount_paise), tv)])
    if quotation.tax_paise:
        # float(), not the Decimal directly: "{Decimal('17.00'):g}" keeps the
        # trailing zeros and prints "17.00%".
        pct = f" ({float(quotation.tax_pct):g}%)" if quotation.tax_pct else ""
        trows.append([Paragraph(f"Tax{pct}", tl),
                      Paragraph(format_money_simple(quotation.tax_paise), tv)])

    inst_idx = None
    if quotation.installation_paise:
        inst_cell = [Paragraph("+ Installation / labour",
                               _s("qil", parent=tl, fontName="Helvetica-Bold",
                                  textColor=THEME.TEAL_600))]
        if quotation.installation_note:
            inst_cell.append(Paragraph(quotation.installation_note, sub))
        inst_idx = len(trows)
        trows.append([inst_cell,
                      Paragraph(format_money_simple(quotation.installation_paise),
                                _s("qiv", parent=tv, fontName="Helvetica-Bold",
                                   textColor=THEME.TEAL_600))])

    total_idx = len(trows)
    trows.append([Paragraph("TOTAL", gl),
                  Paragraph("Rs " + format_money_simple(quotation.total_paise), gv)])

    tot_w = W * 0.42
    totals = Table(trows, colWidths=[tot_w * 0.52, tot_w * 0.48], hAlign="RIGHT")
    totals.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
        ("LINEBELOW", (0, 0), (-1, total_idx - 1), 0.4, THEME.NEUTRAL_200),
        ("BACKGROUND", (0, total_idx), (-1, total_idx), THEME.GREEN_800),
        ("TOPPADDING", (0, total_idx), (-1, total_idx), 5),
        ("BOTTOMPADDING", (0, total_idx), (-1, total_idx), 5),
    ] + ([("BACKGROUND", (0, inst_idx), (-1, inst_idx), THEME.TEAL_50)]
         if inst_idx is not None else [])))

    left_col = [Paragraph("AMOUNT IN WORDS", lbl), Spacer(1, 1 * mm),
                Paragraph(num_to_words_pkr(quotation.total_paise), mut)]
    if quotation.notes:
        left_col += [Spacer(1, 3 * mm), Paragraph("NOTES", lbl), Spacer(1, 1 * mm),
                     Paragraph(quotation.notes.replace("\n", "<br/>"), mut)]

    layout = Table([[left_col, totals]],
                   colWidths=[W - tot_w - 10 * mm, tot_w + 10 * mm], hAlign="LEFT")
    layout.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story += [layout, Spacer(1, 6 * mm)]

    # ── Terms ──────────────────────────────────────────────────────────────
    terms = quotation.terms.strip() or (
        f"This quotation is valid for {quotation.valid_days} days from the date above. "
        "Prices are subject to stock availability at the time of order. "
        "Installation charges are for labour only unless stated otherwise."
    )
    box = Table([[[Paragraph("TERMS", lbl), Spacer(1, 1.2 * mm),
                   Paragraph(terms.replace("\n", "<br/>"), mut)]]],
                colWidths=[W], hAlign="LEFT")
    box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, THEME.NEUTRAL_200),
        ("BACKGROUND", (0, 0), (-1, -1), THEME.NEUTRAL_50),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(box)

    if profile and profile.footer:
        story += [Spacer(1, 3 * mm), Paragraph(profile.footer, mut)]

    def _page(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 6.6)
        canvas.setFillColor(THEME.NEUTRAL_400)
        # Never an invoice number, and it says so at the foot of every page.
        canvas.drawString(doc_.leftMargin, 10 * mm,
                          "Quotation — not a tax invoice")
        canvas.drawRightString(doc_.pagesize[0] - doc_.rightMargin, 10 * mm,
                               f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_page, onLaterPages=_page)
    return buf.getvalue()
