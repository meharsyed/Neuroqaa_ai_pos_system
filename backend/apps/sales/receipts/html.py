"""
HTML receipt.

This is what a customer opens on their phone from a WhatsApp link, so it is
mobile-first rather than an A4 page shrunk down: the item table reflows to
stacked rows on a narrow screen, and everything is legible without zooming.

It also prints correctly (`@media print`), which gives any office printer a
path that does not involve ReportLab.

Same layout discipline as the PDF: the only two filled blocks are the items
header and the total, and every colour comes from the shared theme.
"""

import base64
import html as _html
import os

from .context import ReceiptContext
from .theme import THEME
from .utils import format_money_simple, num_to_words_pkr

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def _hex(color) -> str:
    """ReportLab Color -> '#rrggbb'."""
    return "#" + color.hexval()[2:]


def _esc(value) -> str:
    return _html.escape(str(value if value is not None else ""))


def _logo_data_uri() -> str | None:
    """Inline the logo so the page works with no network and no extra request."""
    path = os.path.join(_ASSETS, "logo-invoice.png")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as fh:
            return "data:image/png;base64," + base64.b64encode(fh.read()).decode("ascii")
    except OSError:
        return None


def _qr_svg(data: str, size: int = 96) -> str:
    """Compact inline SVG QR. renderSVG would emit ~26KB for the same thing."""
    try:
        from reportlab.graphics.barcode import qr

        widget = qr.QrCodeWidget(data, barBorder=0)
        widget.draw()                      # builds the module matrix
        matrix = widget.qr.modules
        n = len(matrix)
    except Exception:
        return ""

    rects = []
    for y, row in enumerate(matrix):
        x = 0
        while x < n:
            if row[x]:
                run = 1
                while x + run < n and row[x + run]:
                    run += 1
                rects.append(f'<rect x="{x}" y="{y}" width="{run}" height="1"/>')
                x += run
            else:
                x += 1
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" '
        f'width="{size}" height="{size}" shape-rendering="crispEdges" '
        f'role="img" aria-label="Bill code">'
        f'<rect width="{n}" height="{n}" fill="#fff"/>'
        f'<g fill="#000">{"".join(rects)}</g></svg>'
    )


def _css(fmt: str) -> str:
    green, green_dark = _hex(THEME.GREEN_800), _hex(THEME.GREEN_900)
    teal, teal_soft = _hex(THEME.TEAL_600), _hex(THEME.TEAL_50)
    ink, muted = _hex(THEME.NEUTRAL_800), _hex(THEME.NEUTRAL_500)
    rule, faint = _hex(THEME.NEUTRAL_200), _hex(THEME.NEUTRAL_100)
    danger = _hex(THEME.DANGER)
    sheet_max = "460px" if fmt == "thermal" else "780px"

    return f"""
*,*::before,*::after{{box-sizing:border-box}}
body{{margin:0;padding:16px 12px 40px;background:{faint};color:{ink};
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,system-ui,sans-serif;
  -webkit-text-size-adjust:100%}}
.sheet{{max-width:{sheet_max};margin:0 auto;background:#fff;border:1px solid {rule};
  border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(20,40,30,.06)}}
.bar{{height:6px;background:{green}}}
.pad{{padding:20px 18px}}

.top{{display:flex;gap:14px;align-items:flex-start;flex-wrap:wrap}}
.logo{{width:56px;flex:0 0 auto}} .logo img{{width:100%;height:auto;display:block}}
.who{{flex:1 1 190px;min-width:0}}
.shop{{margin:0;font-size:17px;font-weight:700;color:{green};letter-spacing:.01em}}
.shop-meta{{margin:4px 0 0;font-size:12.5px;color:{muted};line-height:1.45}}
.meta{{flex:1 1 170px;text-align:right;font-size:13px}}
.meta .kind{{font-weight:700;color:{teal};letter-spacing:.06em;font-size:12.5px;
  text-transform:uppercase;margin-bottom:6px}}
.meta div{{color:{muted};margin-bottom:2px}}
.meta b{{color:{ink};font-weight:600;margin-left:6px;
  font-variant-numeric:tabular-nums;word-break:break-word}}
hr.rule{{border:0;border-top:1.5px solid {teal};margin:16px 0}}

.parties{{display:flex;gap:20px;flex-wrap:wrap;margin-bottom:16px}}
.party{{flex:1 1 150px;min-width:0}}
.label{{font-size:11px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
  color:{teal};margin-bottom:3px}}
.voided{{color:{danger};font-weight:700}}

table{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}}
thead th{{background:{green};color:#fff;font-size:11px;font-weight:700;
  letter-spacing:.06em;text-transform:uppercase;padding:9px 8px;text-align:right}}
thead th:first-child,thead th.desc{{text-align:left}}
tbody td{{padding:10px 8px;border-bottom:1px solid {rule};text-align:right;
  font-size:14px;vertical-align:top}}
tbody td:first-child,tbody td.desc{{text-align:left}}
tbody tr:nth-child(even) td{{background:{teal_soft}}}
.name{{font-weight:600}}
.sku,.serial{{display:block;font-size:11.5px;color:{muted};margin-top:2px}}
.serial{{color:{teal}}}

.totals{{margin-top:18px;margin-left:auto;max-width:340px;font-variant-numeric:tabular-nums}}
.totals .row{{display:flex;justify-content:space-between;gap:16px;padding:6px 10px;
  border-bottom:1px solid {rule};font-size:14px}}
.totals .row span:first-child{{color:{muted}}}
.grand{{display:flex;justify-content:space-between;gap:16px;align-items:center;
  background:{green};color:#fff;padding:12px;border-radius:6px;margin:8px 0}}
.grand .lbl{{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  opacity:.9}}
.grand .amt{{font-size:20px;font-weight:700}}
.due{{color:{danger};font-weight:700}}

.notes{{margin-top:18px;font-size:13px;color:{muted}}}
.notes .label{{color:{teal}}}
.foot{{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-top:20px;
  padding-top:16px;border-top:1px solid {rule}}}
.foot .qr{{flex:0 0 auto;line-height:0}}
.foot .qr svg{{border:1px solid {rule};border-radius:4px}}
.band{{background:{teal_soft};color:{green_dark};text-align:center;
  padding:12px;font-size:12.5px}}
.band .vendor{{display:block;margin-top:3px;font-size:11px;color:{muted}}}

.actions{{max-width:{sheet_max};margin:0 auto 14px;text-align:center}}
.btn{{display:inline-block;border:0;border-radius:8px;background:{green};color:#fff;
  font:600 15px/1 inherit;padding:13px 22px;cursor:pointer}}
.btn:focus-visible{{outline:3px solid {teal};outline-offset:2px}}

@media (max-width:520px){{
  body{{padding:10px 8px 28px}}
  .pad{{padding:16px 13px}}
  .meta{{text-align:left;flex-basis:100%}}
  thead{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}
  tbody td{{display:block;border:0;padding:2px 0;text-align:left}}
  tbody tr{{display:block;padding:12px 2px;border-bottom:1px solid {rule}}}
  tbody tr:nth-child(even) td{{background:transparent}}
  tbody tr:nth-child(even){{background:{teal_soft}}}
  td.num::before{{content:attr(data-label);color:{muted};font-size:12px;
    display:inline-block;min-width:92px}}
  td.idx{{display:none}}
  .totals{{max-width:none}}
}}
@media print{{
  body{{background:#fff;padding:0}}
  .actions{{display:none}}
  .sheet{{border:0;border-radius:0;box-shadow:none;max-width:none}}
  @page{{size:A4;margin:12mm}}
}}
"""


def render(ctx: ReceiptContext, format_name: str = "a4") -> str:
    fmt = "thermal" if format_name == "thermal" else "a4"
    voided = ctx.status == "voided"
    # The thermal PDF prints "Invoice #…" too, so the wording stays consistent.
    kind = "Credit note" if ctx.is_return else ("Tax invoice" if fmt == "a4" else "Invoice")

    logo = _logo_data_uri()
    logo_html = (
        f'<div class="logo"><img src="{logo}" alt=""></div>' if logo else ""
    )

    show_disc = any(i.discount_paise > 0 for i in ctx.items)

    head_cells = ['<th>#</th>', '<th class="desc">Description</th>', "<th>Qty</th>", "<th>Rate</th>"]
    if show_disc:
        head_cells.append("<th>Disc</th>")
    head_cells.append("<th>Amount</th>")

    rows = []
    for i, item in enumerate(ctx.items, 1):
        serials = ""
        if ctx.show_serial_numbers and item.serials:
            serials = "".join(
                f'<span class="serial">S/N {_esc(s.serial)}'
                + (f" ({s.warranty_months}m warranty)" if s.warranty_months else "")
                + "</span>"
                for s in item.serials
            )
        cells = [
            f'<td class="idx">{i}</td>',
            f'<td class="desc"><span class="name">{_esc(item.product_name)}</span>'
            f'<span class="sku">{_esc(item.product_sku)}</span>{serials}</td>',
            f'<td class="num" data-label="Qty">{_esc(item.quantity)}</td>',
            f'<td class="num" data-label="Rate">{format_money_simple(item.unit_price_paise)}</td>',
        ]
        if show_disc:
            disc = format_money_simple(item.discount_paise) if item.discount_paise else "—"
            cells.append(f'<td class="num" data-label="Discount">{disc}</td>')
        cells.append(
            f'<td class="num" data-label="Amount">'
            f"<b>{format_money_simple(item.line_total_paise)}</b></td>"
        )
        rows.append("<tr>" + "".join(cells) + "</tr>")

    total_rows = [
        f'<div class="row"><span>Subtotal</span>'
        f"<span>{format_money_simple(ctx.subtotal_paise)}</span></div>"
    ]
    if ctx.item_discounts_paise:
        total_rows.append(
            f'<div class="row"><span>Item discounts</span>'
            f"<span>-{format_money_simple(ctx.item_discounts_paise)}</span></div>"
        )
    if ctx.bill_discount_paise:
        total_rows.append(
            f'<div class="row"><span>Bill discount</span>'
            f"<span>-{format_money_simple(ctx.bill_discount_paise)}</span></div>"
        )
    if ctx.tax_paise:
        pct = f" ({ctx.tax_pct:g}%)" if ctx.tax_pct else ""
        total_rows.append(
            f'<div class="row"><span>Tax{pct}</span>'
            f"<span>{format_money_simple(ctx.tax_paise)}</span></div>"
        )

    grand = (
        '<div class="grand"><span class="lbl">Total</span>'
        f'<span class="amt">Rs {format_money_simple(ctx.total_paise)}</span></div>'
    )

    after = []
    method = (ctx.payment_method or "cash").replace("_", " ").title()
    if (ctx.payment_method or "").lower() == "credit":
        after.append('<div class="row"><span>Paid now</span><span>0.00</span></div>')
        after.append(
            '<div class="row"><span class="due">Balance due (Khata)</span>'
            f'<span class="due">{format_money_simple(ctx.total_paise)}</span></div>'
        )
    else:
        after.append(
            f'<div class="row"><span>Paid ({_esc(method)})</span>'
            f"<span>{format_money_simple(ctx.tendered_paise)}</span></div>"
        )
        if ctx.change_paise:
            after.append(
                f'<div class="row"><span>Change</span>'
                f"<span>{format_money_simple(ctx.change_paise)}</span></div>"
            )

    qr = _qr_svg(f"{ctx.sale_number}|{ctx.total_paise}|{ctx.created_at_formatted}")
    customer = _esc(ctx.customer_name or "Walk-in Customer")
    phone = f'<div>{_esc(ctx.customer_phone)}</div>' if ctx.customer_phone else ""
    status_html = (
        '<div class="voided">VOIDED</div>' if voided else "<div>Completed</div>"
    )
    contact = " · ".join(x for x in (ctx.shop_phone, ctx.shop_email) if x)

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="{_hex(THEME.GREEN_800)}">
<title>{_esc(ctx.sale_number)} — {_esc(ctx.shop_name)}</title>
<style>{_css(fmt)}</style>
</head><body>

<div class="actions">
  <button class="btn" type="button" onclick="window.print()">Print this bill</button>
</div>

<div class="sheet">
  <div class="bar"></div>
  <div class="pad">

    <div class="top">
      {logo_html}
      <div class="who">
        <h1 class="shop">{_esc(ctx.shop_name)}</h1>
        <p class="shop-meta">{_esc(ctx.shop_address)}<br>{_esc(contact)}</p>
      </div>
      <div class="meta">
        <div class="kind">{_esc(kind)}</div>
        <div>No.<b>{_esc(ctx.sale_number)}</b></div>
        <div>Date<b>{_esc(ctx.created_at_formatted)}, {_esc(ctx.created_at_time)}</b></div>
        <div>Served by<b>{_esc(ctx.cashier_name)}</b></div>
      </div>
    </div>

    <hr class="rule">

    <div class="parties">
      <div class="party">
        <div class="label">Bill to</div>
        <div>{customer}</div>
        {phone}
      </div>
      <div class="party">
        <div class="label">Payment</div>
        <div>{_esc(method)}</div>
        {status_html}
      </div>
    </div>

    <table>
      <thead><tr>{"".join(head_cells)}</tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>

    <div class="totals">
      {"".join(total_rows)}
      {grand}
      {"".join(after)}
    </div>

    <div class="notes">
      <div class="label">Amount in words</div>
      {_esc(num_to_words_pkr(ctx.total_paise))}
      {f'<p>{_esc(ctx.receipt_footer)}</p>' if ctx.receipt_footer else ""}
    </div>

    <div class="foot">
      <div class="qr">{qr}</div>
      <div class="notes" style="margin:0">
        Keep this bill for warranty and returns.<br>
        Scan the code to identify this sale.
      </div>
    </div>

  </div>
  <div class="band">
    {_esc(ctx.receipt_header)}
    <span class="vendor">Powered by Neuroqaa.ai</span>
  </div>
</div>

</body></html>"""
