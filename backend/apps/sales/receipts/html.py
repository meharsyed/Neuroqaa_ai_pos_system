"""
HTML Receipt Renderer for Browser Printing

Renders ReceiptContext to self-contained HTML with embedded CSS.
Suitable for A4 invoices, thermal receipts, or browser preview.
All assets embedded as data URIs.
"""

from .context import ReceiptContext
from .utils import format_money


def render(ctx: ReceiptContext, format_name: str = "a4") -> str:
    """
    Render ReceiptContext as HTML for browser printing.

    Args:
        ctx: ReceiptContext with all receipt data
        format_name: "a4" or "thermal"

    Returns:
        Self-contained HTML string
    """
    if format_name == "thermal":
        return _render_thermal_html(ctx)
    else:
        return _render_a4_html(ctx)


def _render_a4_html(ctx: ReceiptContext) -> str:
    """Render A4 invoice layout"""

    items_html = ""
    for idx, item in enumerate(ctx.items, 1):
        disc_display = "—" if item.discount_paise == 0 else f"-{format_money(item.discount_paise, include_symbol=False)}"
        items_html += f"""
        <tr>
            <td class="col-num">{idx}</td>
            <td class="col-desc">
                <div class="item-name">{item.product_name}</div>
                <div class="item-sku">{item.product_sku}</div>
            </td>
            <td class="col-qty">{item.quantity}</td>
            <td class="col-price text-right">{format_money(item.unit_price_paise, include_symbol=False)}</td>
            <td class="col-disc text-right">{disc_display}</td>
            <td class="col-amt text-right">{format_money(item.line_total_paise, include_symbol=False)}</td>
        </tr>
        """

    # Build totals rows
    totals_rows = f"""
        <tr>
            <td colspan="5" class="label">Subtotal</td>
            <td class="text-right">{format_money(ctx.subtotal_paise, include_symbol=False)}</td>
        </tr>
    """

    if ctx.bill_discount_paise:
        totals_rows += f"""
        <tr>
            <td colspan="5" class="label">Bill Discount</td>
            <td class="text-right">-{format_money(ctx.bill_discount_paise, include_symbol=False)}</td>
        </tr>
        """

    if ctx.tax_paise:
        totals_rows += f"""
        <tr>
            <td colspan="5" class="label">Tax ({ctx.tax_pct:.0f}%)</td>
            <td class="text-right">{format_money(ctx.tax_paise, include_symbol=False)}</td>
        </tr>
        """

    totals_rows += f"""
        <tr class="total-row">
            <td colspan="5" class="label">TOTAL</td>
            <td class="text-right">Rs {format_money(ctx.total_paise, include_symbol=False)}</td>
        </tr>
    """

    if ctx.tendered_paise:
        totals_rows += f"""
        <tr>
            <td colspan="5" class="label">Paid ({(ctx.payment_method or 'CASH').upper()})</td>
            <td class="text-right">{format_money(ctx.tendered_paise, include_symbol=False)}</td>
        </tr>
        """

    if ctx.change_paise:
        totals_rows += f"""
        <tr>
            <td colspan="5" class="label">Change</td>
            <td class="text-right">{format_money(ctx.change_paise, include_symbol=False)}</td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invoice {ctx.sale_number}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 210mm;
            height: 297mm;
            margin: 0 auto;
            background: white;
            padding: 14mm;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}

        @page {{
            size: A4;
            margin: 12mm;
        }}

        @media print {{
            body {{ padding: 0; background: white; }}
            .container {{ max-width: 100%; height: auto; margin: 0; padding: 12mm; box-shadow: none; }}
            .no-print {{ display: none; }}
        }}

        /* Header */
        .header {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 0.8px solid #e5e7eb;
        }}

        .logo {{
            width: 22mm;
            height: 22mm;
            background: #e5e7eb;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #6b7280;
            font-size: 0.75rem;
            font-weight: bold;
        }}

        .shop-info {{
            flex: 1;
        }}

        .shop-name {{
            font-size: 8.5pt;
            font-weight: bold;
            color: #065f46;
            margin-bottom: 0.25rem;
        }}

        .shop-address {{
            font-size: 7.5pt;
            color: #6b7280;
            line-height: 1.3;
            margin-bottom: 0.25rem;
        }}

        .invoice-header {{
            text-align: right;
            flex: 1;
        }}

        .invoice-title {{
            font-size: 9pt;
            font-weight: bold;
            color: #0d9488;
            margin-bottom: 0.25rem;
        }}

        .invoice-details {{
            font-size: 8pt;
            color: #1f2937;
            line-height: 1.3;
        }}

        /* Rule */
        hr {{
            border: none;
            border-top: 0.8px solid #e5e7eb;
            margin: 0.4rem 0;
        }}

        /* Bill-to and Payment */
        .info-section {{
            display: flex;
            gap: 1rem;
            margin: 0.5rem 0 1rem 0;
            font-size: 8pt;
        }}

        .info-block {{
            flex: 1;
        }}

        .info-label {{
            font-weight: bold;
            color: #0d9488;
            margin-bottom: 0.2rem;
        }}

        .info-value {{
            color: #1f2937;
        }}

        .info-muted {{
            color: #6b7280;
        }}

        /* Items table */
        .items-section {{
            margin: 1rem 0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8pt;
        }}

        table thead {{
            background-color: #047857;
            color: white;
            font-weight: bold;
        }}

        table thead th {{
            padding: 0.3rem;
            text-align: left;
            border-bottom: 0.5px solid #d1d5db;
        }}

        table tbody td {{
            padding: 0.3rem;
            color: #1f2937;
            vertical-align: top;
        }}

        table tbody tr:nth-child(even) {{
            background-color: #f0fdfa;
        }}

        .col-num {{ width: 4%; text-align: center; }}
        .col-desc {{ width: 40%; }}
        .col-qty {{ width: 7.5%; text-align: center; }}
        .col-price {{ width: 15%; }}
        .col-disc {{ width: 13%; }}
        .col-amt {{ width: 20%; }}

        .item-name {{
            font-weight: bold;
            color: #1f2937;
        }}

        .item-sku {{
            font-size: 6pt;
            color: #9ca3af;
        }}

        .text-right {{
            text-align: right;
        }}

        /* Totals section */
        .totals-section {{
            display: flex;
            gap: 1rem;
            margin: 1rem 0;
        }}

        .notes {{
            flex: 1;
            font-size: 8pt;
            color: #6b7280;
            line-height: 1.4;
        }}

        .totals-table {{
            flex: 1;
        }}

        .totals-table table {{
            width: 100%;
        }}

        .totals-table tr {{
            font-size: 8.5pt;
        }}

        .totals-table .label {{
            text-align: left;
            color: #1f2937;
        }}

        .total-row {{
            background-color: #047857;
            color: white;
            font-weight: bold;
            font-size: 10pt;
        }}

        .total-row td {{
            padding: 0.4rem !important;
            color: white;
        }}

        /* Signature block */
        .signature-section {{
            margin-top: 2rem;
            display: flex;
            gap: 2rem;
        }}

        .qr {{
            width: 18mm;
            height: 18mm;
            background: #f3f4f6;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #9ca3af;
            font-size: 6pt;
        }}

        .sig-lines {{
            flex: 1;
            display: flex;
            gap: 2rem;
        }}

        .sig-block {{
            flex: 1;
        }}

        .sig-line {{
            border-top: 1px solid #1f2937;
            margin: 3rem 0 0.2rem 0;
            height: 0;
        }}

        .sig-label {{
            font-size: 7pt;
            color: #6b7280;
            text-align: center;
        }}

        /* Footer */
        .footer {{
            background-color: #f0fdfa;
            color: #0d9488;
            text-align: center;
            font-size: 7.5pt;
            padding: 0.3rem;
            margin-top: 1rem;
            border-top: 0.8px solid #e5e7eb;
        }}

        .print-button {{
            display: block;
            margin: 1rem auto;
            padding: 0.5rem 1rem;
            background: #047857;
            color: white;
            border: none;
            border-radius: 0.25rem;
            cursor: pointer;
            font-size: 0.875rem;
        }}

        .print-button:hover {{
            background: #065f46;
        }}
    </style>
</head>
<body>
    <button class="print-button no-print" onclick="window.print()">Print Receipt</button>

    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="logo">LOGO</div>
            <div class="shop-info">
                <div class="shop-name">{ctx.shop_name}</div>
                <div class="shop-address">
                    {ctx.shop_address}<br>
                    {ctx.shop_phone}
                </div>
            </div>
            <div class="invoice-header">
                <div class="invoice-title">TAX INVOICE</div>
                <div class="invoice-details">
                    No.&nbsp;&nbsp;{ctx.sale_number}<br>
                    Date&nbsp;&nbsp;{ctx.created_at_formatted}<br>
                    Time&nbsp;&nbsp;{ctx.created_at_time}<br>
                    Cashier&nbsp;&nbsp;{ctx.cashier_name}
                </div>
            </div>
        </div>

        <hr>

        <!-- Bill-to and Payment Info -->
        <div class="info-section">
            <div class="info-block">
                <div class="info-label">BILL TO</div>
                <div class="info-value">{ctx.customer_name or 'Walk-in Customer'}</div>
                <div class="info-muted">{ctx.customer_phone or '—'}</div>
            </div>
            <div class="info-block">
                <div class="info-label">PAYMENT</div>
                <div class="info-value">{(ctx.payment_method or 'CASH').upper()}</div>
                <div class="info-muted">{(ctx.status or 'COMPLETED').upper()}</div>
            </div>
        </div>

        <!-- Items -->
        <div class="items-section">
            <table>
                <thead>
                    <tr>
                        <th class="col-num">#</th>
                        <th class="col-desc">DESCRIPTION</th>
                        <th class="col-qty">QTY</th>
                        <th class="col-price">RATE</th>
                        <th class="col-disc">DISC</th>
                        <th class="col-amt">AMOUNT</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>
        </div>

        <!-- Totals and Notes -->
        <div class="totals-section">
            <div class="notes">
                {ctx.receipt_footer or 'Thank you for your business!'}
            </div>
            <div class="totals-table">
                <table>
                    <tbody>
                        {totals_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Signature -->
        <div class="signature-section">
            <div class="qr">QR</div>
            <div class="sig-lines">
                <div class="sig-block">
                    <div class="sig-line"></div>
                    <div class="sig-label">Customer Signature</div>
                </div>
                <div class="sig-block">
                    <div class="sig-line"></div>
                    <div class="sig-label">For {ctx.shop_name}</div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            {ctx.receipt_header or 'A name of Trust, Reliability and Quality!'}
            <br>
            Powered by Neuroqaa.ai
        </div>
    </div>
</body>
</html>
"""


def _render_thermal_html(ctx: ReceiptContext) -> str:
    """Render thermal (80mm) receipt layout"""

    items_html = ""
    for item in ctx.items:
        items_html += f"""
        <tr>
            <td class="col-item">
                <div class="item-name">{item.product_name}</div>
                <div class="item-sku">{item.product_sku}</div>
            </td>
            <td class="col-qty">{item.quantity}</td>
            <td class="col-amt">{format_money(item.line_total_paise, include_symbol=False)}</td>
        </tr>
        """

    totals_html = f"""
        <tr><td colspan="3"><div class="sep-line"></div></td></tr>
        <tr>
            <td class="label">Subtotal:</td>
            <td colspan="2" class="amount">{format_money(ctx.subtotal_paise, include_symbol=False)}</td>
        </tr>
    """

    if ctx.bill_discount_paise:
        totals_html += f"""
        <tr>
            <td class="label">Bill Disc:</td>
            <td colspan="2" class="amount">-{format_money(ctx.bill_discount_paise, include_symbol=False)}</td>
        </tr>
        """

    if ctx.tax_paise:
        totals_html += f"""
        <tr>
            <td class="label">Tax ({ctx.tax_pct:.0f}%):</td>
            <td colspan="2" class="amount">{format_money(ctx.tax_paise, include_symbol=False)}</td>
        </tr>
        """

    totals_html += f"""
        <tr class="total-row">
            <td class="label">TOTAL:</td>
            <td colspan="2" class="amount">Rs {format_money(ctx.total_paise, include_symbol=False)}</td>
        </tr>
    """

    if ctx.tendered_paise:
        totals_html += f"""
        <tr>
            <td class="label">Paid:</td>
            <td colspan="2" class="amount">{format_money(ctx.tendered_paise, include_symbol=False)}</td>
        </tr>
        """

    if ctx.change_paise:
        totals_html += f"""
        <tr>
            <td class="label">Change:</td>
            <td colspan="2" class="amount">{format_money(ctx.change_paise, include_symbol=False)}</td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Receipt {ctx.sale_number}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Courier New', monospace;
            background: #f5f5f5;
            padding: 20px;
        }}

        .receipt {{
            width: 80mm;
            margin: 0 auto;
            background: white;
            padding: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            font-size: 11px;
            line-height: 1.3;
        }}

        @page {{
            size: 80mm auto;
            margin: 0;
        }}

        @media print {{
            body {{ padding: 0; background: white; }}
            .receipt {{ width: 100%; margin: 0; box-shadow: none; padding: 4mm; }}
        }}

        .header {{
            text-align: center;
            margin-bottom: 1rem;
        }}

        .shop-name {{
            font-weight: bold;
            font-size: 11px;
            margin-bottom: 0.25rem;
        }}

        .shop-addr {{
            font-size: 7px;
            color: #666;
            margin-bottom: 0.5rem;
        }}

        .receipt-title {{
            font-weight: bold;
            font-size: 9px;
            margin-bottom: 0.25rem;
        }}

        .meta {{
            font-size: 7px;
            color: #666;
            margin-bottom: 0.5rem;
        }}

        .sep-line {{
            border-top: 1px solid #000;
            margin: 0.3rem 0;
        }}

        table {{
            width: 100%;
            font-size: 8px;
            margin-bottom: 0.5rem;
        }}

        table td {{
            padding: 0.2rem 0;
        }}

        .col-item {{ width: 55%; }}
        .col-qty {{ width: 15%; text-align: center; }}
        .col-amt {{ width: 30%; text-align: right; }}

        .item-name {{
            font-weight: bold;
        }}

        .item-sku {{
            font-size: 6px;
            color: #999;
        }}

        .label {{
            text-align: left;
        }}

        .amount {{
            text-align: right;
            font-family: 'Courier New', monospace;
        }}

        .total-row {{
            font-weight: bold;
            border-top: 1px solid #000;
            border-bottom: 1px solid #000;
        }}

        .total-row .label {{
            font-size: 10px;
        }}

        .total-row .amount {{
            font-size: 10px;
        }}

        .footer {{
            text-align: center;
            font-size: 6px;
            color: #666;
            margin-top: 0.5rem;
        }}

        .print-button {{
            display: block;
            margin: 1rem auto;
            padding: 0.5rem 1rem;
            background: #047857;
            color: white;
            border: none;
            border-radius: 0.25rem;
            cursor: pointer;
        }}

        .no-print {{
            display: block;
        }}

        @media print {{
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <button class="print-button no-print" onclick="window.print()">Print Receipt</button>

    <div class="receipt">
        <!-- Header -->
        <div class="header">
            <div class="shop-name">{ctx.shop_name}</div>
            <div class="shop-addr">
                {ctx.shop_address}<br>
                {ctx.shop_phone}
            </div>
            <div class="receipt-title">INVOICE #{ctx.sale_number}</div>
            <div class="meta">
                {ctx.created_at_formatted} {ctx.created_at_time}
            </div>
        </div>

        <!-- Items -->
        <table>
            <tbody>
                <tr><td colspan="3"><div class="sep-line"></div></td></tr>
                {items_html}
                {totals_html}
            </tbody>
        </table>

        <!-- Footer -->
        <div class="footer">
            {ctx.receipt_footer or 'Thank you!'}<br>
            Powered by Neuroqaa.ai
        </div>
    </div>
</body>
</html>
"""