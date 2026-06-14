"""
Business-intelligence report functions — pure data, no HTTP.
Each function returns a plain dict/list suitable for JSON serialisation
or CSV export.
"""

import csv
import io
from datetime import date

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce


def daily_summary(report_date: date) -> dict:
    from .models import Sale, SaleItem

    completed = Sale.objects.filter(
        status=Sale.Status.COMPLETED,
        created_at__date=report_date,
    )

    agg = completed.aggregate(
        total_revenue=Coalesce(Sum("total_paise"), 0),
        total_discount=Coalesce(Sum("discount_paise"), 0),
        transaction_count=Count("id"),
    )

    payment_rows = (
        completed.values("payment__method")
        .annotate(
            total_paise=Coalesce(Sum("total_paise"), 0),
            count=Count("id"),
        )
        .order_by("payment__method")
    )
    payment_breakdown = {
        row["payment__method"]: {
            "total_paise": row["total_paise"],
            "count": row["count"],
        }
        for row in payment_rows
    }

    top_products = list(
        SaleItem.objects.filter(sale__in=completed)
        .values("product__sku", "product__name")
        .annotate(
            qty_sold=Sum("qty"),
            revenue_paise=Coalesce(Sum("subtotal_paise"), 0),
        )
        .order_by("-revenue_paise")[:10]
    )

    return {
        "date": report_date.isoformat(),
        "transaction_count": agg["transaction_count"],
        "total_revenue_paise": agg["total_revenue"],
        "total_discount_paise": agg["total_discount"],
        "payment_breakdown": payment_breakdown,
        "top_products": top_products,
    }


def date_range_summary(start: date, end: date) -> dict:
    from .models import Sale

    completed = Sale.objects.filter(
        status=Sale.Status.COMPLETED,
        created_at__date__gte=start,
        created_at__date__lte=end,
    )

    agg = completed.aggregate(
        total_revenue=Coalesce(Sum("total_paise"), 0),
        total_discount=Coalesce(Sum("discount_paise"), 0),
        transaction_count=Count("id"),
    )

    daily_rows = list(
        completed.values("created_at__date")
        .annotate(
            revenue_paise=Coalesce(Sum("total_paise"), 0),
            count=Count("id"),
        )
        .order_by("created_at__date")
    )

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "transaction_count": agg["transaction_count"],
        "total_revenue_paise": agg["total_revenue"],
        "total_discount_paise": agg["total_discount"],
        "daily_breakdown": [
            {
                "date": str(row["created_at__date"]),
                "revenue_paise": row["revenue_paise"],
                "count": row["count"],
            }
            for row in daily_rows
        ],
    }


def inventory_valuation() -> dict:
    from apps.catalog.models import Inventory

    rows = list(
        Inventory.objects.select_related("product")
        .filter(product__is_active=True)
        .order_by("product__sku")
    )

    products = []
    total_cost = 0
    total_sell = 0

    for inv in rows:
        p = inv.product
        cost_val = int(inv.stock_qty * p.cost_price_paise)
        sell_val = int(inv.stock_qty * p.sell_price_paise)
        total_cost += cost_val
        total_sell += sell_val
        products.append(
            {
                "sku": p.sku,
                "name": p.name,
                "stock_qty": str(inv.stock_qty),
                "cost_price_paise": p.cost_price_paise,
                "sell_price_paise": p.sell_price_paise,
                "cost_value_paise": cost_val,
                "sell_value_paise": sell_val,
            }
        )

    return {
        "products": products,
        "total_cost_value_paise": total_cost,
        "total_sell_value_paise": total_sell,
        "potential_profit_paise": total_sell - total_cost,
    }


# ── Audit / closing report ────────────────────────────────────────────────────


def audit_report(start: date, end: date) -> dict:
    """
    Comprehensive profit & loss audit for a date range.
    COGS is computed using each product's current cost_price_paise — an approximation
    when cost prices change over time (weighted-average costing not implemented).
    """
    from decimal import Decimal

    from django.db.models import DecimalField, ExpressionWrapper, F
    from django.utils import timezone

    from .models import Sale, SaleItem

    # Only completed, non-return sales
    completed = Sale.objects.filter(
        status=Sale.Status.COMPLETED,
        sale_type=Sale.SaleType.SALE,
        created_at__date__gte=start,
        created_at__date__lte=end,
    )

    agg = completed.aggregate(
        transaction_count=Count("id"),
        total_revenue=Coalesce(Sum("total_paise"), 0),
        total_subtotal=Coalesce(Sum("subtotal_paise"), 0),
        total_discount=Coalesce(Sum("discount_paise"), 0),
        total_tax=Coalesce(Sum("tax_paise"), 0),
    )

    # COGS: qty × product.cost_price_paise for each sold item
    cogs_result = (
        SaleItem.objects.filter(sale__in=completed)
        .annotate(
            line_cogs=ExpressionWrapper(
                F("qty") * F("product__cost_price_paise"),
                output_field=DecimalField(max_digits=20, decimal_places=3),
            )
        )
        .aggregate(total=Coalesce(Sum("line_cogs"), Decimal("0")))
    )
    total_cogs = int(cogs_result["total"])

    revenue = agg["total_revenue"]
    gross_profit = revenue - total_cogs
    gross_margin_pct = round(gross_profit / revenue * 100, 1) if revenue > 0 else 0.0

    # Payment breakdown
    payment_rows = (
        completed.values("payment__method")
        .annotate(count=Count("id"), total_paise=Coalesce(Sum("total_paise"), 0))
        .order_by("payment__method")
    )
    payment_breakdown = {
        row["payment__method"]: {"count": row["count"], "total_paise": row["total_paise"]}
        for row in payment_rows
    }

    # Daily breakdown
    daily_rows = list(
        completed.values("created_at__date")
        .annotate(
            count=Count("id"),
            revenue_paise=Coalesce(Sum("total_paise"), 0),
            discount_paise=Coalesce(Sum("discount_paise"), 0),
        )
        .order_by("created_at__date")
    )
    daily_breakdown = [
        {
            "date": str(row["created_at__date"]),
            "count": row["count"],
            "revenue_paise": row["revenue_paise"],
            "discount_paise": row["discount_paise"],
        }
        for row in daily_rows
    ]

    # Top 10 products with per-product profit
    item_agg = list(
        SaleItem.objects.filter(sale__in=completed)
        .values("product__sku", "product__name", "product__cost_price_paise")
        .annotate(
            qty_sold=Sum("qty"),
            revenue_paise=Coalesce(Sum("subtotal_paise"), 0),
        )
        .order_by("-revenue_paise")[:10]
    )
    top_products = []
    for row in item_agg:
        rev = row["revenue_paise"] or 0
        qty = float(row["qty_sold"] or 0)
        cost = row["product__cost_price_paise"] or 0
        cogs = int(qty * cost)
        profit = rev - cogs
        margin = round(profit / rev * 100, 1) if rev > 0 else 0.0
        top_products.append(
            {
                "sku": row["product__sku"],
                "name": row["product__name"],
                "qty_sold": str(row["qty_sold"]),
                "revenue_paise": rev,
                "cogs_paise": cogs,
                "gross_profit_paise": profit,
                "gross_margin_pct": margin,
            }
        )

    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "generated_at": timezone.now().isoformat(),
        "transaction_count": agg["transaction_count"],
        "total_revenue_paise": revenue,
        "total_subtotal_paise": agg["total_subtotal"],
        "total_discount_paise": agg["total_discount"],
        "total_tax_paise": agg["total_tax"],
        "total_cogs_paise": total_cogs,
        "gross_profit_paise": gross_profit,
        "gross_margin_pct": gross_margin_pct,
        "payment_breakdown": payment_breakdown,
        "daily_breakdown": daily_breakdown,
        "top_products": top_products,
    }


def audit_report_pdf(data: dict, shop_name: str = "POS", shop_address: str = "", shop_phone: str = "") -> bytes:
    """
    Generate an A4 PDF audit/closing report from audit_report() data.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )
    except ImportError as exc:
        raise RuntimeError("reportlab is not installed.") from exc

    import io as _io

    buf = _io.BytesIO()
    page_w, page_h = A4
    margin = 18 * mm

    def rs(paise: int) -> str:
        r = paise / 100
        return f"Rs. {r:,.2f}"

    def ps(name: str, **kw):
        d = {"fontName": "Helvetica", "fontSize": 10, "leading": 14, "alignment": TA_LEFT}
        d.update(kw)
        return ParagraphStyle(name, **d)

    PRIMARY = colors.HexColor("#1E3A5F")
    LIGHT   = colors.HexColor("#EEF2F7")
    GRAY    = colors.HexColor("#666666")
    GREEN   = colors.HexColor("#16A34A")
    RED     = colors.HexColor("#DC2626")

    cw = page_w - 2 * margin

    story = []

    # ── Header ─────────────────────────────────────────────────────────────
    story.append(Paragraph(shop_name, ps("sn", fontName="Helvetica-Bold", fontSize=18, alignment=TA_CENTER, textColor=PRIMARY, spaceBefore=0, spaceAfter=2*mm)))
    if shop_address:
        story.append(Paragraph(shop_address, ps("sa", fontSize=9, alignment=TA_CENTER, textColor=GRAY, spaceBefore=0, spaceAfter=1*mm)))
    if shop_phone:
        story.append(Paragraph(shop_phone, ps("sp", fontSize=9, alignment=TA_CENTER, textColor=GRAY, spaceBefore=0, spaceAfter=5*mm)))
    else:
        story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=2 * mm))
    story.append(Paragraph(
        "AUDIT / CLOSING REPORT",
        ps("title", fontName="Helvetica-Bold", fontSize=14, alignment=TA_CENTER, textColor=PRIMARY),
    ))
    story.append(Paragraph(
        f"Period: {data['period_start']}  →  {data['period_end']}",
        ps("period", fontSize=10, alignment=TA_CENTER, textColor=GRAY),
    ))
    from datetime import datetime
    gen_dt = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
    story.append(Paragraph(
        f"Generated: {gen_dt.strftime('%d %b %Y  %H:%M')}",
        ps("gen", fontSize=8, alignment=TA_CENTER, textColor=GRAY),
    ))
    story.append(Spacer(1, 5 * mm))

    # ── Summary boxes ───────────────────────────────────────────────────────
    margin_color = GREEN if data["gross_margin_pct"] >= 0 else RED

    def summary_cell(label: str, value: str, color=PRIMARY) -> list:
        return [
            Paragraph(value, ps("sv", fontName="Helvetica-Bold", fontSize=13, alignment=TA_CENTER, textColor=color)),
            Paragraph(label,  ps("sl", fontSize=8, alignment=TA_CENTER, textColor=GRAY)),
        ]

    box_w = cw / 5 - 2 * mm
    summary_tbl = Table(
        [[
            summary_cell("Transactions", str(data["transaction_count"])),
            summary_cell("Revenue", rs(data["total_revenue_paise"])),
            summary_cell("COGS", rs(data["total_cogs_paise"]), GRAY),
            summary_cell("Gross Profit", rs(data["gross_profit_paise"]), GREEN if data["gross_profit_paise"] >= 0 else RED),
            summary_cell("Margin", f"{data['gross_margin_pct']}%", margin_color),
        ]],
        colWidths=[box_w] * 5,
    )
    summary_tbl.setStyle(TableStyle([
        ("BOX",            (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID",      (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND",     (0, 0), (-1, -1), LIGHT),
        ("TOPPADDING",     (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(summary_tbl)
    story.append(Spacer(1, 5 * mm))

    # ── Revenue breakdown ───────────────────────────────────────────────────
    story.append(Paragraph("REVENUE & PROFIT BREAKDOWN", ps("h2", fontName="Helvetica-Bold", fontSize=10, textColor=PRIMARY)))
    story.append(HRFlowable(width="100%", thickness=0.5, color=PRIMARY, spaceAfter=2 * mm))

    def rev_row(label, value, bold=False, color=colors.black):
        fn = "Helvetica-Bold" if bold else "Helvetica"
        fs = 10 if bold else 9
        return [
            Paragraph(label, ps(f"rl{label}", fontName=fn, fontSize=fs, textColor=color)),
            Paragraph(value, ps(f"rv{label}", fontName=fn, fontSize=fs, alignment=TA_RIGHT, textColor=color)),
        ]

    rev_data = [
        rev_row("Gross Sales (before discounts)", rs(data["total_subtotal_paise"])),
        rev_row("Discounts Given", f"− {rs(data['total_discount_paise'])}", color=colors.HexColor("#B45309")),
        rev_row("Tax Collected", f"+ {rs(data['total_tax_paise'])}", color=colors.HexColor("#1D4ED8")),
        rev_row("Net Revenue", rs(data["total_revenue_paise"]), bold=True),
        rev_row("Cost of Goods Sold (COGS)", f"− {rs(data['total_cogs_paise'])}", color=GRAY),
        rev_row("Gross Profit", rs(data["gross_profit_paise"]), bold=True,
                color=GREEN if data["gross_profit_paise"] >= 0 else RED),
        rev_row(f"Gross Margin", f"{data['gross_margin_pct']}%", bold=True,
                color=GREEN if data["gross_margin_pct"] >= 0 else RED),
    ]
    rev_tbl = Table(rev_data, colWidths=[cw * 0.65, cw * 0.35])
    rev_tbl.setStyle(TableStyle([
        ("LINEBELOW",      (0, 3), (-1, 3), 0.5, colors.HexColor("#CBD5E1")),
        ("LINEBELOW",      (0, 4), (-1, 4), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND",     (0, 3), (-1, 3), LIGHT),
        ("BACKGROUND",     (0, 5), (-1, 6), LIGHT),
        ("TOPPADDING",     (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
    ]))
    story.append(rev_tbl)
    story.append(Spacer(1, 5 * mm))

    # ── Payment methods ─────────────────────────────────────────────────────
    if data["payment_breakdown"]:
        story.append(Paragraph("PAYMENT METHODS", ps("h2", fontName="Helvetica-Bold", fontSize=10, textColor=PRIMARY)))
        story.append(HRFlowable(width="100%", thickness=0.5, color=PRIMARY, spaceAfter=2 * mm))
        pay_header = [
            Paragraph('<font color="white"><b>Method</b></font>', ps("ph", fontName="Helvetica", fontSize=9)),
            Paragraph('<font color="white"><b>Transactions</b></font>', ps("ph2", fontName="Helvetica", fontSize=9, alignment=TA_RIGHT)),
            Paragraph('<font color="white"><b>Total Revenue</b></font>', ps("ph3", fontName="Helvetica", fontSize=9, alignment=TA_RIGHT)),
        ]
        pay_rows = [pay_header]
        for method, v in data["payment_breakdown"].items():
            pay_rows.append([
                Paragraph(method.upper(), ps("pm", fontSize=9)),
                Paragraph(str(v["count"]), ps("pc", fontSize=9, alignment=TA_RIGHT)),
                Paragraph(rs(v["total_paise"]), ps("pv", fontSize=9, alignment=TA_RIGHT)),
            ])
        pay_tbl = Table(pay_rows, colWidths=[cw * 0.4, cw * 0.25, cw * 0.35])
        pay_tbl.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR",      (0, 0), (-1, 0), colors.white),
            ("INNERGRID",      (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
            ("BOX",            (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING",     (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ]))
        story.append(pay_tbl)
        story.append(Spacer(1, 5 * mm))

    # ── Top products ────────────────────────────────────────────────────────
    if data["top_products"]:
        story.append(Paragraph("TOP PRODUCTS BY REVENUE (with margin)", ps("h2", fontName="Helvetica-Bold", fontSize=10, textColor=PRIMARY)))
        story.append(HRFlowable(width="100%", thickness=0.5, color=PRIMARY, spaceAfter=2 * mm))
        prod_header = [
            Paragraph('<font color="white"><b>SKU / Product</b></font>', ps("th", fontName="Helvetica", fontSize=8)),
            Paragraph('<font color="white"><b>Qty</b></font>', ps("th2", fontName="Helvetica", fontSize=8, alignment=TA_RIGHT)),
            Paragraph('<font color="white"><b>Revenue</b></font>', ps("th3", fontName="Helvetica", fontSize=8, alignment=TA_RIGHT)),
            Paragraph('<font color="white"><b>COGS</b></font>', ps("th4", fontName="Helvetica", fontSize=8, alignment=TA_RIGHT)),
            Paragraph('<font color="white"><b>Profit</b></font>', ps("th5", fontName="Helvetica", fontSize=8, alignment=TA_RIGHT)),
            Paragraph('<font color="white"><b>Margin</b></font>', ps("th6", fontName="Helvetica", fontSize=8, alignment=TA_RIGHT)),
        ]
        prod_rows = [prod_header]
        for p in data["top_products"]:
            profit_color = GREEN if p["gross_profit_paise"] >= 0 else RED
            prod_rows.append([
                Paragraph(f"<b>{p['sku']}</b><br/><font size='7' color='#666'>{p['name']}</font>", ps("pn", fontSize=8, leading=11)),
                Paragraph(p["qty_sold"], ps("pq", fontSize=8, alignment=TA_RIGHT)),
                Paragraph(rs(p["revenue_paise"]), ps("pr", fontSize=8, alignment=TA_RIGHT)),
                Paragraph(rs(p["cogs_paise"]), ps("pc2", fontSize=8, alignment=TA_RIGHT, textColor=GRAY)),
                Paragraph(rs(p["gross_profit_paise"]), ps("pp", fontSize=8, alignment=TA_RIGHT, textColor=profit_color)),
                Paragraph(f"{p['gross_margin_pct']}%", ps("pm2", fontName="Helvetica-Bold", fontSize=8, alignment=TA_RIGHT, textColor=profit_color)),
            ])
        prod_tbl = Table(prod_rows, colWidths=[cw * 0.30, cw * 0.09, cw * 0.16, cw * 0.16, cw * 0.16, cw * 0.13])
        prod_tbl.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR",      (0, 0), (-1, 0), colors.white),
            ("INNERGRID",      (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
            ("BOX",            (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING",     (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
            ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(prod_tbl)
        story.append(Spacer(1, 5 * mm))

    # ── Daily breakdown ─────────────────────────────────────────────────────
    if data["daily_breakdown"]:
        story.append(Paragraph("DAILY BREAKDOWN", ps("h2", fontName="Helvetica-Bold", fontSize=10, textColor=PRIMARY)))
        story.append(HRFlowable(width="100%", thickness=0.5, color=PRIMARY, spaceAfter=2 * mm))
        day_header = [
            Paragraph('<font color="white"><b>Date</b></font>', ps("dh", fontName="Helvetica", fontSize=9)),
            Paragraph('<font color="white"><b>Transactions</b></font>', ps("dh2", fontName="Helvetica", fontSize=9, alignment=TA_RIGHT)),
            Paragraph('<font color="white"><b>Discounts</b></font>', ps("dh3", fontName="Helvetica", fontSize=9, alignment=TA_RIGHT)),
            Paragraph('<font color="white"><b>Revenue</b></font>', ps("dh4", fontName="Helvetica", fontSize=9, alignment=TA_RIGHT)),
        ]
        day_rows = [day_header]
        for row in data["daily_breakdown"]:
            day_rows.append([
                Paragraph(row["date"], ps("dd", fontSize=9)),
                Paragraph(str(row["count"]), ps("dc", fontSize=9, alignment=TA_RIGHT)),
                Paragraph(rs(row["discount_paise"]), ps("ddisc", fontSize=9, alignment=TA_RIGHT, textColor=colors.HexColor("#B45309"))),
                Paragraph(rs(row["revenue_paise"]), ps("dr", fontSize=9, alignment=TA_RIGHT)),
            ])
        day_tbl = Table(day_rows, colWidths=[cw * 0.28, cw * 0.22, cw * 0.22, cw * 0.28])
        day_tbl.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR",      (0, 0), (-1, 0), colors.white),
            ("INNERGRID",      (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
            ("BOX",            (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING",     (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ]))
        story.append(day_tbl)

    # ── Footer ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#CBD5E1"), spaceAfter=2 * mm))
    story.append(Paragraph(
        "COGS is based on current product cost prices (approximate). "
        "This report is confidential and intended for management use only.",
        ps("note", fontSize=7, textColor=GRAY, alignment=TA_CENTER),
    ))
    story.append(Paragraph(
        f"Powered by Neuroqaa POS  |  Neuroqaa.ai Pvt. Ltd.",
        ps("foot", fontSize=7, textColor=GRAY, alignment=TA_CENTER),
    ))

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )
    doc.build(story)
    return buf.getvalue()


# ── CSV helpers ────────────────────────────────────────────────────────────────


def daily_summary_csv(data: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", data["date"]])
    w.writerow(["Transactions", data["transaction_count"]])
    w.writerow(["Total Revenue (Rs.)", f"{data['total_revenue_paise'] / 100:.2f}"])
    w.writerow(["Total Discounts (Rs.)", f"{data['total_discount_paise'] / 100:.2f}"])
    w.writerow([])
    w.writerow(["Payment Method", "Amount (Rs.)", "Transactions"])
    for method, v in data["payment_breakdown"].items():
        w.writerow([method, f"{v['total_paise'] / 100:.2f}", v["count"]])
    w.writerow([])
    w.writerow(["SKU", "Product", "Qty Sold", "Revenue (Rs.)"])
    for p in data["top_products"]:
        w.writerow(
            [
                p["product__sku"],
                p["product__name"],
                p["qty_sold"],
                f"{p['revenue_paise'] / 100:.2f}",
            ]
        )
    return buf.getvalue()


def inventory_valuation_csv(data: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "SKU",
            "Name",
            "Stock Qty",
            "Cost Price (Rs.)",
            "Sell Price (Rs.)",
            "Cost Value (Rs.)",
            "Sell Value (Rs.)",
        ]
    )
    for p in data["products"]:
        w.writerow(
            [
                p["sku"],
                p["name"],
                p["stock_qty"],
                f"{p['cost_price_paise'] / 100:.2f}",
                f"{p['sell_price_paise'] / 100:.2f}",
                f"{p['cost_value_paise'] / 100:.2f}",
                f"{p['sell_value_paise'] / 100:.2f}",
            ]
        )
    w.writerow([])
    w.writerow(
        [
            "",
            "TOTAL",
            "",
            f"{data['total_cost_value_paise'] / 100:.2f}",
            f"{data['total_sell_value_paise'] / 100:.2f}",
        ]
    )
    return buf.getvalue()
