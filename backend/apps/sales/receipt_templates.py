"""
Professional Receipt Template Generator
Supports 4 template designs: Classic, Modern, Itemized, Compact
"""

from io import BytesIO
from datetime import datetime
from decimal import Decimal

from reportlab.lib.pagesizes import letter, landscape, A4, A5
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, HRFlowable, Preformatted
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# Page format definitions
PAGE_FORMATS = {
    "thermal_80mm": {
        "name": "Thermal 80mm",
        "width_mm": 80,
        "height_inch": 11,
        "margin_mm": 3,
        "description": "80mm thermal printer (standard retail)",
    },
    "thermal_58mm": {
        "name": "Thermal 58mm",
        "width_mm": 58,
        "height_inch": 11,
        "margin_mm": 2,
        "description": "58mm thermal printer (compact)",
    },
    "a4": {
        "name": "A4",
        "pagesize": A4,  # 210 × 297 mm
        "margin_mm": 10,
        "description": "Standard A4 paper (professional)",
    },
    "a5": {
        "name": "A5",
        "pagesize": A5,  # 148 × 210 mm
        "margin_mm": 8,
        "description": "A5 paper (half-page, compact)",
    },
}


class BaseReceiptTemplate:
    """Base class for all receipt templates"""

    def __init__(self, sale, shop_settings, page_format="a4"):
        self.sale = sale
        self.shop = shop_settings
        self.page_format = page_format
        self.format_config = PAGE_FORMATS.get(page_format, PAGE_FORMATS["a4"])
        self.header_text = shop_settings.get("receipt_header", "")
        self.footer_text = shop_settings.get("receipt_footer", "Thank you for your business!")

        # Set up page dimensions based on format
        if "width_mm" in self.format_config:
            # Thermal printer format
            self.width_mm = self.format_config["width_mm"]
            self.height_inch = self.format_config.get("height_inch", 11)
            self.pagesize = (self.width_mm * mm, self.height_inch * inch)
        else:
            # Standard paper format (A4, A5)
            self.pagesize = self.format_config.get("pagesize", A4)
            self.width_mm = None

        self.margin_mm = self.format_config.get("margin_mm", 5)

    def _get_styles(self):
        """Get default styles"""
        styles = getSampleStyleSheet()
        return styles

    def _format_currency(self, paise):
        """Format paise to Rs. display"""
        return f"Rs. {paise / 100:,.2f}"

    def _get_page_width(self):
        """Calculate page width in points"""
        if self.width_mm:
            return self.width_mm * mm
        else:
            # For A4/A5 formats, use standard width
            if self.page_format == "a5":
                return 148 * mm
            return 210 * mm  # A4 default

    def _get_margin_mm(self):
        """Get margin size in mm"""
        return self.margin_mm

    def _get_customer_name(self):
        """Get customer name safely (handles NULL customer)"""
        return self.sale.customer.name if self.sale.customer else "Walk-in Customer"

    def _get_customer_phone(self):
        """Get customer phone safely (handles NULL customer)"""
        return self.sale.customer.phone if self.sale.customer else "N/A"

    def _get_payment_method(self):
        """Get payment method safely (handles missing payment)"""
        return self.sale.payment.method.upper() if self.sale.payment else "CASH"

    def generate_pdf(self):
        """Generate PDF - override in subclasses"""
        raise NotImplementedError


class ClassicTemplate(BaseReceiptTemplate):
    """Professional traditional invoice template"""

    def generate_pdf(self):
        """Generate classic professional receipt"""
        buffer = BytesIO()
        margin = self._get_margin_mm() * mm
        page_width = self._get_page_width()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.pagesize,
            rightMargin=margin,
            leftMargin=margin,
            topMargin=margin * 1.5,
            bottomMargin=margin,
        )

        elements = []
        styles = self._get_styles()

        # ─── HEADER: Shop Name ───
        shop_name_style = ParagraphStyle(
            'ShopName',
            parent=styles['Heading1'],
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=2 * mm,
            alignment=TA_CENTER,
        )
        elements.append(Paragraph(self.shop.get("shop_name", "SHOP NAME"), shop_name_style))

        # ─── Subtitle ───
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#4b5563'),
            spaceAfter=3 * mm,
            alignment=TA_CENTER,
        )
        elements.append(Paragraph("Sanitary & Tiles • Professional POS System", subtitle_style))

        # ─── Divider ───
        elements.append(Spacer(1, 1 * mm))

        # ─── Shop Contact Info ───
        info_style = ParagraphStyle(
            'ShopInfo',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#6b7280'),
            spaceAfter=3 * mm,
            alignment=TA_CENTER,
            leading=9,
        )
        shop_info = f"""{self.shop.get("shop_address", "Address")}<br/>
Phone: {self.shop.get("shop_phone", "N/A")} | Email: {self.shop.get("shop_email", "N/A")}"""
        elements.append(Paragraph(shop_info, info_style))

        # ─── Divider Line ───
        elements.append(Spacer(1, 2 * mm))
        hr_style = TableStyle([('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#d1d5db'))])
        hr_table = Table([["="*50]], colWidths=[page_width - 8*mm])
        hr_table.setStyle(hr_style)
        elements.append(hr_table)

        # ─── Invoice Header ───
        inv_style = ParagraphStyle(
            'InvLabel',
            parent=styles['Normal'],
            fontSize=8,
            fontName='Helvetica-Bold',
            textColor=colors.black,
        )
        inv_data = [
            [Paragraph("INVOICE #", inv_style), Paragraph(f"INV-{self.sale.id:06d}", inv_style)],
            [Paragraph("DATE", inv_style), Paragraph(datetime.now().strftime("%d %b %Y, %I:%M %p"), inv_style)],
        ]
        inv_table = Table(inv_data, colWidths=[page_width * 0.4, page_width * 0.6])
        inv_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(inv_table)
        elements.append(Spacer(1, 3 * mm))

        # ─── Customer Section ───
        bill_label = ParagraphStyle(
            'BillLabel',
            parent=styles['Normal'],
            fontSize=7,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=1 * mm,
        )
        elements.append(Paragraph("BILL TO:", bill_label))

        customer_style = ParagraphStyle(
            'Customer',
            parent=styles['Normal'],
            fontSize=7,
            leading=10,
            spaceAfter=3 * mm,
        )
        customer_text = f"""<b>{self._get_customer_name()}</b><br/>
Phone: {self._get_customer_phone()}"""
        elements.append(Paragraph(customer_text, customer_style))

        # ─── Items Table ───
        item_data = [
            [
                Paragraph("<b>Description</b>", ParagraphStyle('header', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold')),
                Paragraph("<b>Qty</b>", ParagraphStyle('header', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold', alignment=TA_CENTER)),
                Paragraph("<b>Price</b>", ParagraphStyle('header', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
                Paragraph("<b>Total</b>", ParagraphStyle('header', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
            ]
        ]

        # Add items
        for item in self.sale.items.all():
            item_data.append([
                Paragraph(item.product.name, ParagraphStyle('item', parent=styles['Normal'], fontSize=7)),
                Paragraph(f"{item.qty}", ParagraphStyle('item', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER)),
                Paragraph(self._format_currency(item.unit_price_paise), ParagraphStyle('item', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT)),
                Paragraph(self._format_currency(int(item.qty * item.unit_price_paise)), ParagraphStyle('item', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT)),
            ])

        # Add totals
        subtotal = sum(int(item.qty * item.unit_price_paise) for item in self.sale.items.all())
        tax = self.sale.tax_paise
        total = subtotal + tax

        item_data.append([Paragraph(""), Paragraph(""), Paragraph(""), Paragraph("")])  # Spacer
        item_data.append([
            Paragraph(""), Paragraph(""),
            Paragraph("<b>Subtotal</b>", ParagraphStyle('total', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold')),
            Paragraph(f"<b>{self._format_currency(subtotal)}</b>", ParagraphStyle('total', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
        ])
        item_data.append([
            Paragraph(""), Paragraph(""),
            Paragraph("<b>Tax</b>", ParagraphStyle('total', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold')),
            Paragraph(f"<b>{self._format_currency(tax)}</b>", ParagraphStyle('total', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
        ])
        item_data.append([
            Paragraph(""), Paragraph(""),
            Paragraph("<b>TOTAL DUE</b>", ParagraphStyle('total', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold')),
            Paragraph(f"<b>{self._format_currency(total)}</b>", ParagraphStyle('total', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
        ])

        item_table = Table(item_data, colWidths=[
            page_width * 0.4,
            page_width * 0.15,
            page_width * 0.225,
            page_width * 0.225,
        ])
        item_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#374151')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#374151')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, -3), (-1, -1), colors.HexColor('#f9fafb')),
            ('LINEABOVE', (0, -3), (-1, -3), 1, colors.HexColor('#d1d5db')),
            ('LINEBELOW', (0, -1), (-1, -1), 2, colors.HexColor('#1e3a8a')),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 3 * mm))

        # ─── Payment Info ───
        payment_style = ParagraphStyle(
            'Payment',
            parent=styles['Normal'],
            fontSize=7,
        )
        payment_data = [
            [
                Paragraph(f"<b>Payment:</b> {self._get_payment_method()}", payment_style),
                Paragraph(f"<b>Status:</b> COMPLETED", payment_style),
            ]
        ]
        payment_table = Table(payment_data, colWidths=[page_width * 0.5, page_width * 0.5])
        payment_table.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), 7)]))
        elements.append(payment_table)
        elements.append(Spacer(1, 3 * mm))

        # ─── Footer ───
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#6b7280'),
            spaceAfter=1 * mm,
            alignment=TA_CENTER,
        )
        if self.footer_text:
            elements.append(Paragraph(self.footer_text, footer_style))
        elements.append(Paragraph("Powered by Neuroqaa.ai", footer_style))
        elements.append(Spacer(1, 2 * mm))

        # ─── Signature ───
        sig_style = ParagraphStyle(
            'Signature',
            parent=styles['Normal'],
            fontSize=6,
            alignment=TA_CENTER,
        )
        elements.append(Paragraph("_____________________", sig_style))
        elements.append(Paragraph("Authorized Signature", sig_style))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


class ModernTemplate(BaseReceiptTemplate):
    """Clean, contemporary template"""

    def generate_pdf(self):
        """Generate modern receipt with minimal design"""
        buffer = BytesIO()
        margin = self._get_margin_mm() * mm
        page_width = self._get_page_width()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.pagesize,
            rightMargin=margin,
            leftMargin=margin,
            topMargin=margin * 1.2,
            bottomMargin=margin,
        )

        elements = []
        styles = self._get_styles()
        primary_color = colors.HexColor('#6366f1')  # Indigo

        # ─── Header ───
        header_data = [
            [
                Paragraph(self.shop.get("shop_name", "SHOP"), ParagraphStyle(
                    'name', parent=styles['Normal'], fontSize=12, fontName='Helvetica-Bold',
                    textColor=primary_color
                )),
                Paragraph(f"INV-{self.sale.id:06d}", ParagraphStyle(
                    'inv', parent=styles['Normal'], fontSize=12, fontName='Helvetica-Bold',
                    textColor=primary_color, alignment=TA_RIGHT
                )),
            ]
        ]
        header_table = Table(header_data, colWidths=[page_width * 0.5, page_width * 0.5])
        header_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f4f4f9')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 2 * mm))

        # ─── Date and Customer ───
        date_style = ParagraphStyle('date', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor('#6b7280'))
        elements.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d %b %Y')}", date_style))
        elements.append(Paragraph(f"<b>Customer:</b> {self._get_customer_name()}", date_style))
        customer_phone = self._get_customer_phone()
        if customer_phone != "N/A":
            elements.append(Paragraph(f"<b>Phone:</b> {customer_phone}", date_style))
        elements.append(Spacer(1, 2 * mm))

        # ─── Items ───
        item_data = [
            [
                Paragraph("<b>Item</b>", ParagraphStyle('h', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold')),
                Paragraph("<b>Qty</b>", ParagraphStyle('h', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold', alignment=TA_CENTER)),
                Paragraph("<b>Price</b>", ParagraphStyle('h', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
                Paragraph("<b>Total</b>", ParagraphStyle('h', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
            ]
        ]

        for item in self.sale.items.all():
            item_data.append([
                Paragraph(item.product.name, ParagraphStyle('i', parent=styles['Normal'], fontSize=7)),
                Paragraph(f"{item.qty}", ParagraphStyle('i', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER)),
                Paragraph(self._format_currency(item.unit_price_paise), ParagraphStyle('i', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT)),
                Paragraph(self._format_currency(int(item.qty * item.unit_price_paise)), ParagraphStyle('i', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT)),
            ])

        subtotal = sum(int(item.qty * item.unit_price_paise) for item in self.sale.items.all())
        tax = self.sale.tax_paise
        total = subtotal + tax

        item_table = Table(item_data, colWidths=[page_width * 0.4, page_width * 0.15, page_width * 0.225, page_width * 0.225])
        item_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f4f4f9')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 3 * mm))

        # ─── Totals ───
        total_data = [
            [Paragraph("Subtotal", ParagraphStyle('l', parent=styles['Normal'], fontSize=7)), Paragraph(self._format_currency(subtotal), ParagraphStyle('r', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT))],
            [Paragraph("Tax", ParagraphStyle('l', parent=styles['Normal'], fontSize=7)), Paragraph(self._format_currency(tax), ParagraphStyle('r', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT))],
            [Paragraph("<b>Total</b>", ParagraphStyle('l', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=primary_color)), Paragraph(f"<b>{self._format_currency(total)}</b>", ParagraphStyle('r', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=primary_color, alignment=TA_RIGHT))],
        ]
        total_table = Table(total_data, colWidths=[page_width * 0.5, page_width * 0.5])
        total_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('LINEABOVE', (0, -1), (-1, -1), 2, primary_color),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(total_table)
        elements.append(Spacer(1, 3 * mm))

        # ─── Footer ───
        footer_style = ParagraphStyle('f', parent=styles['Normal'], fontSize=6, alignment=TA_CENTER, textColor=colors.HexColor('#9ca3af'))
        elements.append(Paragraph(self.footer_text, footer_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


class ItemizedTemplate(BaseReceiptTemplate):
    """Detailed template with borders for each item"""

    def generate_pdf(self):
        """Generate itemized receipt with detailed borders"""
        buffer = BytesIO()
        margin = self._get_margin_mm() * mm
        page_width = self._get_page_width()

        # For itemized, use taller page if it's a custom size
        if self.page_format.startswith("thermal"):
            height = 14 * inch
        else:
            height = self.pagesize[1]  # Use native height for A4/A5

        doc = SimpleDocTemplate(
            buffer,
            pagesize=(self.pagesize[0], height),
            rightMargin=margin,
            leftMargin=margin,
            topMargin=margin * 1.2,
            bottomMargin=margin,
        )

        elements = []
        styles = self._get_styles()

        # ─── Header ───
        title_style = ParagraphStyle('t', parent=styles['Heading1'], fontSize=13, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.HexColor('#1e3a8a'), spaceAfter=1*mm)
        elements.append(Paragraph(self.shop.get("shop_name", "SHOP NAME"), title_style))

        subtitle_style = ParagraphStyle('s', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, textColor=colors.HexColor('#6b7280'))
        elements.append(Paragraph("Professional POS Invoice", subtitle_style))

        info_style = ParagraphStyle('info', parent=styles['Normal'], fontSize=6, alignment=TA_CENTER, leading=8)
        shop_info = f"""{self.shop.get("shop_address", "")}<br/>
Phone: {self.shop.get("shop_phone", "")} | {self.shop.get("shop_email", "")}"""
        elements.append(Paragraph(shop_info, info_style))
        elements.append(Spacer(1, 3 * mm))

        # ─── Invoice Details ───
        details_data = [
            [Paragraph(f"<b>Invoice #:</b> INV-{self.sale.id:06d}", ParagraphStyle('d', parent=styles['Normal'], fontSize=7))],
            [Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d %B %Y, %I:%M %p')}", ParagraphStyle('d', parent=styles['Normal'], fontSize=7))],
        ]
        details_table = Table(details_data, colWidths=[page_width - 6*mm])
        details_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(details_table)
        elements.append(Spacer(1, 3 * mm))

        # ─── Customer Section ───
        customer_header = ParagraphStyle('ch', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold', textColor=colors.HexColor('#1e3a8a'))
        elements.append(Paragraph("CUSTOMER INFORMATION", customer_header))

        customer_data = [[
            Paragraph(f"<b>Name:</b> {self._get_customer_name()}", ParagraphStyle('c', parent=styles['Normal'], fontSize=7)),
        ], [
            Paragraph(f"<b>Phone:</b> {self._get_customer_phone()}", ParagraphStyle('c', parent=styles['Normal'], fontSize=7)),
        ]]
        customer_table = Table(customer_data, colWidths=[page_width - 6*mm])
        customer_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9fafb')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(customer_table)
        elements.append(Spacer(1, 3 * mm))

        # ─── Items Section ───
        items_header = ParagraphStyle('ih', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold', textColor=colors.HexColor('#1e3a8a'))
        elements.append(Paragraph("ITEMS ORDERED", items_header))

        for idx, item in enumerate(self.sale.items.all(), 1):
            item_style = ParagraphStyle('is', parent=styles['Normal'], fontSize=7)
            item_content = f"""<b>{idx}. {item.product.name}</b><br/>
SKU: {item.product.sku} | Qty: {item.qty} × {self._format_currency(item.unit_price_paise)} = {self._format_currency(int(item.qty * item.unit_price_paise))}"""

            item_para = Paragraph(item_content, item_style)

            item_data = [[item_para]]
            item_table = Table(item_data, colWidths=[page_width - 6*mm])
            item_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1.5, colors.HexColor('#e5e7eb')),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ffffff')),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(item_table)
            if idx < len(list(self.sale.items.all())):
                elements.append(Spacer(1, 2 * mm))

        elements.append(Spacer(1, 3 * mm))

        # ─── Totals ───
        subtotal = sum(int(item.qty * item.unit_price_paise) for item in self.sale.items.all())
        tax = self.sale.tax_paise
        total = subtotal + tax

        totals_data = [
            [Paragraph("Subtotal", ParagraphStyle('tl', parent=styles['Normal'], fontSize=7)), Paragraph(self._format_currency(subtotal), ParagraphStyle('tr', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT))],
            [Paragraph("Tax (0%)", ParagraphStyle('tl', parent=styles['Normal'], fontSize=7)), Paragraph(self._format_currency(tax), ParagraphStyle('tr', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT))],
            [Paragraph("<b>TOTAL DUE</b>", ParagraphStyle('tl', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold')), Paragraph(f"<b>{self._format_currency(total)}</b>", ParagraphStyle('tr', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold', alignment=TA_RIGHT))],
        ]
        totals_table = Table(totals_data, colWidths=[page_width * 0.5, page_width * 0.5])
        totals_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f4ff')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 3 * mm))

        # ─── Footer ───
        footer_style = ParagraphStyle('f', parent=styles['Normal'], fontSize=6, alignment=TA_CENTER, textColor=colors.HexColor('#6b7280'))
        elements.append(Paragraph(self.footer_text, footer_style))
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph("_________________________", footer_style))
        elements.append(Paragraph("Authorized Signature", footer_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


class CompactTemplate(BaseReceiptTemplate):
    """Compact template optimized for 80mm thermal printers"""

    def generate_pdf(self):
        """Generate compact thermal printer receipt"""
        buffer = BytesIO()
        margin = self._get_margin_mm() * mm
        page_width = self._get_page_width()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.pagesize,
            rightMargin=margin,
            leftMargin=margin,
            topMargin=margin,
            bottomMargin=margin,
        )

        elements = []
        styles = self._get_styles()

        # ─── Header ───
        header_style = ParagraphStyle('h', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', alignment=TA_CENTER)
        elements.append(Paragraph(self.shop.get("shop_name", "SHOP"), header_style))

        shop_style = ParagraphStyle('sh', parent=styles['Normal'], fontSize=6, alignment=TA_CENTER, leading=8)
        elements.append(Paragraph(f"{self.shop.get('shop_address', '')}<br/>Ph: {self.shop.get('shop_phone', '')}", shop_style))
        elements.append(Spacer(1, 1.5 * mm))

        # ─── Invoice Details ───
        inv_style = ParagraphStyle('i', parent=styles['Normal'], fontSize=6)
        elements.append(Paragraph(f"INV: {self.sale.id} | {datetime.now().strftime('%d %b %Y')}", inv_style))
        elements.append(Spacer(1, 1 * mm))

        # ─── Customer ───
        cust_style = ParagraphStyle('c', parent=styles['Normal'], fontSize=6)
        elements.append(Paragraph(f"Customer: {self._get_customer_name()}", cust_style))
        customer_phone = self._get_customer_phone()
        if customer_phone != "N/A":
            elements.append(Paragraph(f"Phone: {customer_phone}", cust_style))
        elements.append(Spacer(1, 1.5 * mm))

        # ─── Items ───
        item_data = [[
            Paragraph("Item", ParagraphStyle('h', parent=styles['Normal'], fontSize=6, fontName='Helvetica-Bold')),
            Paragraph("Qty", ParagraphStyle('h', parent=styles['Normal'], fontSize=6, fontName='Helvetica-Bold')),
            Paragraph("Price", ParagraphStyle('h', parent=styles['Normal'], fontSize=6, fontName='Helvetica-Bold')),
            Paragraph("Total", ParagraphStyle('h', parent=styles['Normal'], fontSize=6, fontName='Helvetica-Bold')),
        ]]

        for item in self.sale.items.all():
            item_data.append([
                Paragraph(item.product.name[:15], ParagraphStyle('i', parent=styles['Normal'], fontSize=6)),
                Paragraph(str(item.qty), ParagraphStyle('i', parent=styles['Normal'], fontSize=6)),
                Paragraph(f"{item.unit_price_paise/100:.0f}", ParagraphStyle('i', parent=styles['Normal'], fontSize=6)),
                Paragraph(f"{int(item.qty * item.unit_price_paise)/100:.0f}", ParagraphStyle('i', parent=styles['Normal'], fontSize=6)),
            ])

        item_table = Table(item_data, colWidths=[page_width*0.4, page_width*0.15, page_width*0.225, page_width*0.225])
        item_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 1.5 * mm))

        # ─── Totals ───
        subtotal = sum(int(item.qty * item.unit_price_paise) for item in self.sale.items.all())
        tax = self.sale.tax_paise
        total = subtotal + tax

        totals_style = ParagraphStyle('t', parent=styles['Normal'], fontSize=6)
        elements.append(Paragraph(f"Subtotal: {self._format_currency(subtotal)}", totals_style))
        elements.append(Paragraph(f"Tax: {self._format_currency(tax)}", totals_style))
        elements.append(Spacer(1, 0.5 * mm))

        total_style = ParagraphStyle('tt', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold')
        elements.append(Paragraph(f"TOTAL: {self._format_currency(total)}", total_style))
        elements.append(Spacer(1, 1.5 * mm))

        # ─── Footer ───
        footer_style = ParagraphStyle('f', parent=styles['Normal'], fontSize=5, alignment=TA_CENTER)
        elements.append(Paragraph(self.footer_text, footer_style))
        elements.append(Paragraph("Powered by Neuroqaa.ai", footer_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


def get_template_class(template_type):
    """Factory function to get template class"""
    templates = {
        "classic": ClassicTemplate,
        "modern": ModernTemplate,
        "itemized": ItemizedTemplate,
        "compact": CompactTemplate,
    }
    return templates.get(template_type, ClassicTemplate)