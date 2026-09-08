# 📄 Multi-Template Billing Receipt System - Implementation Guide

Complete guide for implementing 3-4 professional receipt templates with admin selection.

---

## 🎯 Overview

**What we're building:**
- 4 professional receipt template designs
- Admin setting to select which template to use
- Dynamic receipt generation based on selected template
- Professional, readable, well-formatted output
- Includes: Logo, shop info, customer info, items, totals, signature line

---

## 📋 The 4 Templates

### **Template 1: Classic (Traditional)**
Professional, traditional invoice style
- Large shop logo at top
- Clear section headers
- Traditional table layout
- Best for: Professional retail shops
- Paper: A4 or thermal 80mm

```
═══════════════════════════════════
        NEUROQAA POS SYSTEM
═══════════════════════════════════

Quetta, Balochistan, Pakistan
Phone: +92-123-456-7890
Email: shop@neuroqaa.ai

───────────────────────────────────
INVOICE #: INV-20260614-0001
Date: 14 Jun 2026, 03:15 PM
───────────────────────────────────

BILL TO:
Customer Name: Ali Ahmed
Phone: +92-300-1234567

───────────────────────────────────
Description          Price  Qty  Total
───────────────────────────────────
Blue Ceramic Tile    1200   2    2,400
Red Floor Tile       1500   3    4,500
Faucet Set           2500   1    2,500

───────────────────────────────────
Subtotal:                      9,400
Tax (0%):                          0
Total Due:                     9,400

Paid: CASH
───────────────────────────────────

Thank you for your business!
Powered by Neuroqaa.ai

_____________________
Authorized Signature
```

### **Template 2: Modern Minimal**
Clean, contemporary design
- Minimalist layout
- Color accents (blue/indigo)
- Modern typography
- Best for: Tech-forward shops
- Paper: A4 or thermal

```
┌─────────────────────────────────────────┐
│  Neuroqaa POS  |  INVOICE #INV-026-0001 │
│  Modern Design |  Date: 14 Jun 2026     │
└─────────────────────────────────────────┘

CUSTOMER
Name: Ali Ahmed
Phone: +92-300-1234567
Location: Quetta, Balochistan

┌─────────────────────────────────────────┐
│ Item          │  Qty │  Price │  Total  │
├─────────────────────────────────────────┤
│ Blue Tile     │   2  │ 1200   │ 2400    │
│ Red Tile      │   3  │ 1500   │ 4500    │
│ Faucet Set    │   1  │ 2500   │ 2500    │
└─────────────────────────────────────────┘

Subtotal     ..................  9,400
Tax          ..................      0
                                ─────────
Total        ..................  9,400

Payment: CASH
Status: COMPLETED

Thank you!
```

### **Template 3: Detailed Itemized**
Maximum detail with clear item borders
- Large item boxes with borders
- More spacing for readability
- Detailed item information
- Best for: High-value items, detailed tracking
- Paper: A4

```
╔════════════════════════════════════════════════════════╗
║                  NEUROQAA - INVOICE                    ║
║              Professional POS System                   ║
╚════════════════════════════════════════════════════════╝

┌─ SHOP INFORMATION ─────────────────────────────────────┐
│ Neuroqaa Sanitary & Tiles                              │
│ Quetta, Balochistan, Pakistan                          │
│ Phone: +92-123-456-7890 | Email: shop@neuroqaa.ai     │
└────────────────────────────────────────────────────────┘

┌─ INVOICE DETAILS ──────────────────────────────────────┐
│ Invoice #: INV-20260614-0001                           │
│ Date: 14 June 2026                                     │
│ Time: 03:15 PM                                         │
└────────────────────────────────────────────────────────┘

┌─ BILL TO ──────────────────────────────────────────────┐
│ Customer: Ali Ahmed                                    │
│ Phone: +92-300-1234567                                 │
│ Address: Main Bazaar, Quetta                           │
└────────────────────────────────────────────────────────┘

┌─ ITEMS ────────────────────────────────────────────────┐
│                                                        │
│  1. Blue Ceramic Tile 30×30                           │
│     SKU: TILE-001 | Qty: 2 × Rs. 1,200 = Rs. 2,400  │
│     Description: Premium glazed ceramic tiles         │
│                                                        │
├────────────────────────────────────────────────────────┤
│                                                        │
│  2. Red Floor Tile 20×20                              │
│     SKU: TILE-002 | Qty: 3 × Rs. 1,500 = Rs. 4,500  │
│     Description: Durable floor tiles                  │
│                                                        │
├────────────────────────────────────────────────────────┤
│                                                        │
│  3. Chrome Faucet Set                                  │
│     SKU: FAUCET-001 | Qty: 1 × Rs. 2,500 = Rs. 2,500│
│     Description: Modern kitchen faucet set            │
│                                                        │
└────────────────────────────────────────────────────────┘

┌─ TOTALS ───────────────────────────────────────────────┐
│                                                        │
│  Subtotal (3 items) ..................... Rs. 9,400  │
│  Tax (0%) ................................ Rs.    0  │
│  Discount ................................ Rs.    0  │
│                                    ─────────────────  │
│  TOTAL DUE ....................... Rs. 9,400        │
│                                                        │
│  Amount Paid: Rs. 9,400                               │
│  Payment Method: CASH                                 │
│  Change: Rs. 0                                        │
│                                                        │
└────────────────────────────────────────────────────────┘

┌─ THANK YOU ────────────────────────────────────────────┐
│         Thank you for your business!                  │
│    Please visit us again soon.                        │
│                                                        │
│  Powered by Neuroqaa.ai                               │
└────────────────────────────────────────────────────────┘

_________________________
Authorized Signature
```

### **Template 4: Compact (Thermal Printer)**
Optimized for 80mm thermal printers
- Narrow width (fits 80mm)
- Minimal spacing
- Quick printing
- Best for: Fast checkout, thermal printers
- Paper: 80mm thermal roll

```
====================================
   NEUROQAA - THERMAL RECEIPT
====================================

Shop: Neuroqaa Sanitary & Tiles
Quetta, Balochistan
Ph: +92-123-456-7890

────────────────────────────────────
INV: INV-026-0001  14 Jun 2026
────────────────────────────────────

CUSTOMER: Ali Ahmed
PHONE: +92-300-1234567

────────────────────────────────────
Item           Qty  Price   Total
────────────────────────────────────
Blue Tile       2   1200    2400
Red Tile        3   1500    4500
Faucet Set      1   2500    2500
────────────────────────────────────

Subtotal:              9400
Tax:                      0
                    ────────
TOTAL:              9400

Payment: CASH
Status: COMPLETED

════════════════════════════════════
Thank you! Visit us again.
════════════════════════════════════
```

---

## 🔧 Implementation Steps

### **Step 1: Add Setting for Template Selection**

Already done via migration:
```
Key: receipt_template_type
Values: "classic", "modern", "itemized", "compact"
```

### **Step 2: Update SettingsPage (Frontend)**

Add a dropdown for template selection in the Receipt settings section:

```typescript
// In frontend/src/pages/SettingsPage.tsx

// In the Receipt group, add:
{
  labelKey: "appearance", // or create new group "receiptTemplates"
  keys: ["receipt_template_type", "receipt_header", "receipt_footer", "receipt_width"]
}

// Update renderInput to handle template selection:
const renderInput = (setting: Setting) => {
  if (setting.key === "receipt_template_type") {
    return (
      <Select
        options={[
          { value: "classic", label: "Classic (Traditional)" },
          { value: "modern", label: "Modern Minimal" },
          { value: "itemized", label: "Detailed Itemized" },
          { value: "compact", label: "Compact (Thermal)" },
        ]}
        value={values[setting.key] ?? "classic"}
        onChange={(e) => handleChange(setting.key, e.currentTarget.value)}
        disabled={!canEdit}
      />
    );
  }
  // ... rest of renderInput logic
};
```

### **Step 3: Create Receipt Template Generator (Backend)**

Create a new file: `backend/apps/sales/receipt_templates.py`

```python
# backend/apps/sales/receipt_templates.py

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from datetime import datetime

class ReceiptTemplate:
    """Base class for receipt templates"""
    
    def __init__(self, sale, shop_settings):
        self.sale = sale
        self.shop = shop_settings
        self.width = float(shop_settings.get("receipt_width", "48"))  # mm
        self.header = shop_settings.get("receipt_header", "")
        self.footer = shop_settings.get("receipt_footer", "")
    
    def generate_pdf(self):
        """Override in subclasses"""
        raise NotImplementedError


class ClassicTemplate(ReceiptTemplate):
    """Professional traditional template"""
    
    def generate_pdf(self):
        # Implementation using ReportLab
        # See full code below
        pass


class ModernTemplate(ReceiptTemplate):
    """Clean, contemporary template"""
    pass


class ItemizedTemplate(ReceiptTemplate):
    """Detailed with borders for each item"""
    pass


class CompactTemplate(ReceiptTemplate):
    """80mm thermal printer optimized"""
    pass


def get_template_class(template_type):
    """Factory function to get template class"""
    templates = {
        "classic": ClassicTemplate,
        "modern": ModernTemplate,
        "itemized": ItemizedTemplate,
        "compact": CompactTemplate,
    }
    return templates.get(template_type, ClassicTemplate)
```

### **Step 4: Update Receipt API Endpoint**

Modify existing receipt endpoints to use selected template:

```python
# In backend/apps/sales/views.py

class SaleViewSet(viewsets.ModelViewSet):
    # ... existing code ...
    
    @action(detail=True, methods=["get"])
    def receipt_pdf(self, request, pk=None):
        """Generate PDF receipt using selected template"""
        sale = self.get_object()
        
        # Get selected template from settings
        template_type = get_setting("receipt_template_type", "classic")
        
        # Get shop settings
        shop_settings = {
            "shop_name": get_setting("shop_name", ""),
            "shop_address": get_setting("shop_address", ""),
            "shop_phone": get_setting("shop_phone", ""),
            "shop_email": get_setting("shop_email", ""),
            "receipt_header": get_setting("receipt_header", ""),
            "receipt_footer": get_setting("receipt_footer", ""),
            "receipt_width": get_setting("receipt_width", "48"),
        }
        
        # Get template and generate PDF
        template_class = get_template_class(template_type)
        template = template_class(sale, shop_settings)
        
        pdf_bytes = template.generate_pdf()
        
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="receipt-{sale.id}.pdf"'
        return response
```

### **Step 5: Update Frontend Receipt Display**

The receipt display will automatically use the backend's selected template, so no frontend changes needed for template selection. The API will handle template logic.

---

## 📐 Detailed Template Implementation (Classic Example)

Here's how to implement the Classic template with ReportLab:

```python
# backend/apps/sales/receipt_templates.py

from reportlab.lib.pagesizes import landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime


class ClassicTemplate(ReceiptTemplate):
    """Professional traditional invoice template"""
    
    def generate_pdf(self):
        buffer = BytesIO()
        
        # Page size: 80mm width (thermal printer width)
        # Or A4 for normal printers
        page_width = float(self.width) * mm
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=(page_width, 11 * inch),
            rightMargin=3 * mm,
            leftMargin=3 * mm,
            topMargin=5 * mm,
            bottomMargin=5 * mm,
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # HEADER: Shop Name
        shop_name_style = ParagraphStyle(
            'ShopName',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=2 * mm,
            alignment=1,  # Center
        )
        elements.append(Paragraph(self.shop.get("shop_name", ""), shop_name_style))
        
        # Subtitle
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            spaceAfter=3 * mm,
            alignment=1,
        )
        elements.append(Paragraph("Sanitary & Tiles", subtitle_style))
        
        # Shop Info
        info_text = f"""
        {self.shop.get("shop_address", "")}<br/>
        Phone: {self.shop.get("shop_phone", "")}<br/>
        Email: {self.shop.get("shop_email", "")}
        """
        info_style = ParagraphStyle(
            'ShopInfo',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.black,
            spaceAfter=4 * mm,
            alignment=1,
        )
        elements.append(Paragraph(info_text, info_style))
        
        # Divider
        elements.append(Spacer(1, 2 * mm))
        
        # INVOICE HEADER
        inv_data = [
            ["INVOICE #:", f"INV-{self.sale.id:06d}"],
            ["Date:", datetime.now().strftime("%d %b %Y, %I:%M %p")],
        ]
        inv_table = Table(inv_data, colWidths=[page_width * 0.4, page_width * 0.6])
        inv_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(inv_table)
        elements.append(Spacer(1, 3 * mm))
        
        # BILL TO
        bill_style = ParagraphStyle(
            'BillLabel',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.black,
            spaceAfter=1 * mm,
            fontName='Helvetica-Bold',
        )
        elements.append(Paragraph("BILL TO:", bill_style))
        
        customer_text = f"""
        {self.sale.customer_name or "Walk-in Customer"}<br/>
        Phone: {self.sale.customer_phone or "N/A"}
        """
        customer_style = ParagraphStyle(
            'Customer',
            parent=styles['Normal'],
            fontSize=7,
            spaceAfter=3 * mm,
        )
        elements.append(Paragraph(customer_text, customer_style))
        
        # ITEMS TABLE
        item_data = [
            ["Description", "Qty", "Price", "Total"]
        ]
        
        for item in self.sale.saleitem_set.all():
            item_data.append([
                item.product.name,
                str(item.qty),
                f"Rs. {item.unit_price_paise / 100:.2f}",
                f"Rs. {item.line_total_paise / 100:.2f}",
            ])
        
        # Add totals
        item_data.append(["", "", "Subtotal:", f"Rs. {self.sale.subtotal_paise / 100:.2f}"])
        item_data.append(["", "", "Tax:", f"Rs. {self.sale.tax_paise / 100:.2f}"])
        item_data.append(["", "", "TOTAL:", f"Rs. {self.sale.total_paise / 100:.2f}"])
        
        item_table = Table(item_data, colWidths=[
            page_width * 0.4,
            page_width * 0.2,
            page_width * 0.2,
            page_width * 0.2,
        ])
        item_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -2), 1, colors.grey),
            ('LINESTYLE', (0, -2), (-1, -2), 1, colors.black),
            ('BACKGROUND', (0, -2), (-1, -1), colors.HexColor('#f0f0f0')),
            ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 4 * mm))
        
        # PAYMENT INFO
        payment_data = [
            ["Payment Method:", self.sale.payment_method.upper()],
            ["Status:", "COMPLETED"],
        ]
        payment_table = Table(payment_data, colWidths=[page_width * 0.5, page_width * 0.5])
        payment_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        elements.append(payment_table)
        elements.append(Spacer(1, 4 * mm))
        
        # FOOTER
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.grey,
            spaceAfter=2 * mm,
            alignment=1,
        )
        footer_text = self.footer or "Thank you for your business!"
        elements.append(Paragraph(footer_text, footer_style))
        elements.append(Spacer(1, 2 * mm))
        
        # Signature line
        elements.append(Paragraph("_____________________", footer_style))
        elements.append(Paragraph("Authorized Signature", footer_style))
        
        # Build PDF
        doc.build(elements)
        
        buffer.seek(0)
        return buffer.getvalue()
```

---

## 🗂️ File Structure Summary

```
backend/
├── apps/
│   ├── sales/
│   │   ├── receipt_templates.py      ← NEW: Template classes
│   │   ├── views.py                  (update receipt endpoints)
│   │   └── ...
│   └── config/
│       └── migrations/
│           └── 0004_receipt_template_setting.py  ← NEW
│
frontend/
├── src/
│   └── pages/
│       └── SettingsPage.tsx          (update to add template selector)
```

---

## 🚀 Implementation Roadmap

### **Phase 1: Backend Setup** (2-3 hours)
1. ✅ Create migration for receipt_template_type setting
2. Create `receipt_templates.py` with all 4 template classes
3. Update receipt API endpoints to use selected template

### **Phase 2: Frontend Setup** (1-2 hours)
1. Update SettingsPage to show template dropdown
2. Test template selection saves to settings

### **Phase 3: Testing & Refinement** (2-3 hours)
1. Generate receipts with each template
2. Test on thermal printer (80mm width)
3. Verify all information displays correctly
4. Refine spacing/fonts as needed

**Total Effort:** ~5-8 hours

---

## 💡 Customization Tips

### **For Your Specific Needs:**

1. **Logo Integration:** Add `shop_logo_path` setting to include custom logo
   ```python
   from reportlab.platypus import Image
   logo = Image(logo_path, width=30*mm, height=30*mm)
   elements.insert(0, logo)
   ```

2. **Custom Colors:** Make template colors configurable
   ```python
   primary_color = get_setting("brand_color", "#1e3a8a")
   ```

3. **Footer Customization:** Already supported via `receipt_footer` setting

4. **Item Details:** Add descriptions/details
   ```python
   [item.product.name + "\n" + item.product.description]
   ```

---

## ✅ Checklist Before Production

- [ ] All 4 templates generate valid PDFs
- [ ] Templates tested on A4 paper
- [ ] Templates tested on 80mm thermal printer
- [ ] Settings dropdown shows all options
- [ ] Selected template persists in database
- [ ] Customer info displays correctly
- [ ] All totals calculate correctly
- [ ] Professional alignment and spacing
- [ ] Urdu text displays correctly (if using Urdu template)

---

## 🎯 Next Steps

1. **Decide:** Do you want me to implement the full Classic template code now?
2. **Customize:** Any specific colors/fonts you prefer?
3. **Timeline:** When do you need this ready?

---

**Would you like me to:**
1. ✅ Implement all 4 templates with full ReportLab code?
2. ✅ Create the SettingsPage UI for template selection?
3. ✅ Update the receipt API to use templates?
4. ✅ Test everything end-to-end?

Let me know and I'll implement the complete solution! 🚀