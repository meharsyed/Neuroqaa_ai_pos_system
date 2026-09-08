"""
Khata statement — a printable account summary for one customer.

Same layout discipline as the invoice: every table width derived from
doc.width, every table hAlign'd explicitly, so nothing can bleed off the page.
"""

import io
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from apps.config.utils import get_all_settings
from apps.sales.receipts.theme import THEME
from apps.sales.receipts.utils import format_money_simple, num_to_words_pkr

from .models import CreditLedgerEntry
from .services import customer_credit_summary


def _s(name, **kw):
    return ParagraphStyle(name, **kw)


def _logo(width):
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(
        here, "..", "sales", "receipts", "assets", "logo-invoice.png"
    )
    if os.path.exists(path):
        try:
            img = Image(path, width=width, height=width, kind="proportional")
            img.hAlign = "LEFT"
            return img
        except Exception:
            return None
    return None


def render_khata_statement(customer) -> bytes:
    shop = get_all_settings()
    summary = customer_credit_summary(customer)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=12 * mm, bottomMargin=25 * mm,
        title=f"Khata statement — {customer.display_name}",
    )
    W = doc.width
    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    logo_w = 18 * mm
    logo = _logo(logo_w)
    rest = W - (logo_w + 4 * mm if logo else 0)

    shop_block = [
        Paragraph(shop.get("shop_name", "Speed Tech Solutions").upper(),
                  _s("n", fontName="Helvetica-Bold", fontSize=12.5,
                     textColor=THEME.GREEN_800, leading=15)),
        Paragraph(shop.get("shop_address", ""),
                  _s("a", fontSize=7, textColor=THEME.NEUTRAL_500, leading=9.5)),
        Paragraph(shop.get("shop_phone", ""),
                  _s("p", fontSize=7, textColor=THEME.NEUTRAL_500, leading=9.5)),
    ]
    grey = THEME.NEUTRAL_500.hexval()[2:]
    right = _s("r", fontSize=7, textColor=THEME.NEUTRAL_800,
               alignment=TA_RIGHT, leading=11)
    meta = [
        Paragraph("KHATA STATEMENT",
                  _s("t", fontName="Helvetica-Bold", fontSize=10,
                     textColor=THEME.TEAL_600, alignment=TA_RIGHT)),
        Spacer(1, 1.5 * mm),
        Paragraph(f'<font color="#{grey}">Customer</font>&nbsp;&nbsp;'
                  f"<b>{customer.name or '-'}</b>", right),
        Paragraph(f'<font color="#{grey}">Phone</font>&nbsp;&nbsp;'
                  f"<b>{customer.phone or '-'}</b>", right),
        Paragraph(f'<font color="#{grey}">Issued</font>&nbsp;&nbsp;'
                  f"<b>{_today(shop)}</b>", right),
    ]

    row = ([logo, "", shop_block, meta] if logo else [shop_block, meta])
    widths = ([logo_w, 4 * mm, rest * 0.55, rest * 0.45] if logo
              else [rest * 0.55, rest * 0.45])
    head = Table([row], colWidths=widths, hAlign="LEFT")
    head.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story += [head, Spacer(1, 3 * mm),
              HRFlowable(width="100%", thickness=0.9, color=THEME.ACCENT_RULE),
              Spacer(1, 4 * mm)]

    # ── Summary tiles ───────────────────────────────────────────────────────
    lbl = _s("l", fontSize=7, textColor=THEME.NEUTRAL_500, alignment=TA_CENTER, leading=9)
    val = _s("v", fontName="Helvetica-Bold", fontSize=12,
             textColor=THEME.NEUTRAL_800, alignment=TA_CENTER, leading=15)
    due = _s("d", parent=val, textColor=THEME.GREEN_800, fontSize=14)

    tiles = [
        [Paragraph("Total charged", lbl), Paragraph("Paid", lbl),
         Paragraph("Returned / voided", lbl), Paragraph("Balance due", lbl)],
        [Paragraph(format_money_simple(summary["total_charged_paise"]), val),
         Paragraph(format_money_simple(summary["total_paid_paise"]), val),
         Paragraph(format_money_simple(summary["total_reversed_paise"]), val),
         Paragraph("Rs " + format_money_simple(summary["outstanding_paise"]), due)],
    ]
    t = Table(tiles, colWidths=[W / 4.0] * 4, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), THEME.TEAL_50),
        ("BOX", (0, 0), (-1, -1), 0.4, THEME.NEUTRAL_200),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
        ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("TOPPADDING", (0, 1), (-1, 1), 0), ("BOTTOMPADDING", (0, 1), (-1, 1), 7),
    ]))
    story += [t, Spacer(1, 5 * mm)]

    # ── Ledger ──────────────────────────────────────────────────────────────
    th = _s("th", fontName="Helvetica-Bold", fontSize=7.5,
            textColor=colors.white, leading=9)
    thr = _s("thr", parent=th, alignment=TA_RIGHT)
    cell = _s("c", fontSize=8, textColor=THEME.NEUTRAL_800, leading=10)
    cell_r = _s("cr", parent=cell, alignment=TA_RIGHT)
    muted = _s("m", fontSize=6.5, textColor=THEME.NEUTRAL_500, leading=8)

    ratios = [0.16, 0.17, 0.31, 0.18, 0.18]
    widths = [W * r for r in ratios]
    widths[-1] = W - sum(widths[:-1])

    data = [[Paragraph("DATE", th), Paragraph("TYPE", th), Paragraph("REFERENCE", th),
             Paragraph("AMOUNT", thr), Paragraph("BALANCE", thr)]]

    entries = list(
        CreditLedgerEntry.objects.filter(customer=customer)
        .select_related("sale")
        .order_by("created_at", "id")
    )
    for e in entries:
        ref = e.sale.sale_number if e.sale else (e.note or "-")
        block = [Paragraph(ref, cell)]
        if e.sale and e.note:
            block.append(Paragraph(e.note, muted))
        sign = "+" if e.delta_paise > 0 else "-"
        data.append([
            Paragraph(e.created_at.strftime("%d %b %Y"), cell),
            Paragraph(e.get_kind_display(), cell),
            block,
            Paragraph(f"{sign} {format_money_simple(abs(e.delta_paise))}", cell_r),
            Paragraph(format_money_simple(e.balance_after_paise), cell_r),
        ])

    if len(data) == 1:
        data.append([Paragraph("No credit activity recorded.", cell), "", "", "", ""])

    ledger = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    ledger.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), THEME.GREEN_800),
        ("TOPPADDING", (0, 0), (-1, 0), 4), ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, THEME.TEAL_50]),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, THEME.NEUTRAL_200),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 1), (-1, -1), 4), ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [ledger, Spacer(1, 5 * mm)]

    # ── Closing ─────────────────────────────────────────────────────────────
    close = Table(
        [[Paragraph("BALANCE DUE",
                    _s("bl", fontName="Helvetica-Bold", fontSize=11,
                       textColor=colors.white, leading=14)),
          Paragraph("Rs " + format_money_simple(summary["outstanding_paise"]),
                    _s("bv", fontName="Helvetica-Bold", fontSize=13,
                       textColor=colors.white, alignment=TA_RIGHT, leading=16))]],
        colWidths=[W * 0.55, W * 0.45], hAlign="LEFT",
    )
    close.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), THEME.GREEN_800),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [close, Spacer(1, 3 * mm),
              Paragraph("In words: " + num_to_words_pkr(summary["outstanding_paise"]),
                        _s("w", fontSize=8, textColor=THEME.NEUTRAL_500))]

    if not summary["is_reconciled"]:
        story += [Spacer(1, 3 * mm), Paragraph(
            "Note: this statement was generated while the ledger and the stored "
            "balance disagreed. Please contact the shop.",
            _s("warn", fontSize=7.5, textColor=THEME.DANGER))]

    def _page(canvas, doc_):
        canvas.saveState()
        pw, ph = doc_.pagesize
        canvas.setFillColor(THEME.GREEN_800)
        canvas.rect(0, ph - 4 * mm, pw, 4 * mm, stroke=0, fill=1)
        canvas.setFillColor(THEME.TEAL_50)
        canvas.rect(0, 0, pw, 13 * mm, stroke=0, fill=1)
        canvas.setStrokeColor(THEME.TEAL_600)
        canvas.setLineWidth(1.1)
        canvas.line(0, 13 * mm, pw, 13 * mm)
        canvas.setFillColor(THEME.TEAL_800)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.drawString(14 * mm, 5.5 * mm,
                          shop.get("receipt_header", "") or shop.get("shop_name", ""))
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(THEME.NEUTRAL_500)
        canvas.drawRightString(pw - 14 * mm, 5.5 * mm, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_page, onLaterPages=_page)
    return buf.getvalue()


def _today(shop) -> str:
    from django.utils import timezone
    from zoneinfo import ZoneInfo

    return timezone.now().astimezone(ZoneInfo("Asia/Karachi")).strftime("%d %b %Y, %H:%M")
