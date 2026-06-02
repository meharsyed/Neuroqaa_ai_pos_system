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
