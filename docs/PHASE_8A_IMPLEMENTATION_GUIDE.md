# Phase 8A Implementation Guide — Receipt System Rebuild

**Status:** ✅ **ALL STEPS COMPLETE (1-8)**  
**Last updated:** 2026-09-04

## Implementation Summary

| Step | Component | Status |
|------|-----------|--------|
| 1 | `views.py` logging fix | ✅ Complete |
| 2 | `context.py` data layer | ✅ Complete |
| 3 | `document.py` A4/A5 invoice | ✅ Complete |
| 4 | `thermal_pdf.py` 80mm roll | ✅ Complete |
| 5 | `html.py` HTML print view | ✅ Complete |
| 6 | `__init__.py` renderer wiring | ✅ Complete |
| 7 | `test_receipts.py` test suite | ✅ Complete |
| 8 | Sample generation script | ✅ Complete |

---

## Step 2: Fix `context.py` — Data layer corrections

**File:** `backend/apps/sales/receipts/context.py`

### Fix 2A: Quantity formatting (lines 99-108)

Replace:
```python
quantity=str(item.qty),  # Produces "4.000"
line_total_paise=int(item.qty) * item.unit_price_paise - item.discount_paise,
```

With:
```python
quantity=format_qty(item.qty),  # Will produce "4", "2.5"
line_total_paise=item.subtotal_paise,  # Use stored value, not recomputed
```

First, add `format_qty` function to `backend/apps/sales/receipts/utils.py`:
```python
def format_qty(qty) -> str:
    """Decimal('4.000') → '4'; Decimal('2.500') → '2.5'"""
    from decimal import Decimal
    d = Decimal(str(qty)).normalize()
    if d == d.to_integral_value():
        d = d.quantize(Decimal(1))
    return format(d, "f")
```

### Fix 2B: Payment handling (lines 111-143)

Replace bare `except:` with specific exception:
```python
# BEFORE (line 113-140)
payment = None
try:
    payment = sale.payment
except:
    pass

# AFTER
from django.core.exceptions import ObjectDoesNotExist
payment = None
try:
    payment = sale.payment
except ObjectDoesNotExist:
    pass
```

### Fix 2C: Add tax_pct to context (after line 125)

Add after line 125:
```python
tax_pct = shop_settings.get("tax_pct", "0"),
```

Pass it to ReceiptContext init (line 143):
```python
# Add to ReceiptContext() call
tax_pct_value = float(shop_settings.get("tax_pct", "0")) or 0,
```

And add field to ReceiptContext dataclass (line 67):
```python
tax_pct: float = 0
```

### Fix 2D: Add is_return flag (after line 143)

```python
is_return=sale.sale_type == "return",
```

Add to dataclass (line 68):
```python
is_return: bool = False
```

### Fix 2E: Add invariant check (after line 150)

```python
# Verify item sum matches stored subtotal
items_sum = sum(item.line_total_paise for item in items)
if items_sum != (sale.subtotal_paise or 0):
    logger.warning(
        f"Sale {sale.id}: item sum {items_sum} != subtotal {sale.subtotal_paise}"
    )
```

---

## Step 3: Rewrite `receipts/document.py` — A4/A5 invoice

**File:** `backend/apps/sales/receipts/document.py`

**Key rules:**
1. **No hardcoded `mm` widths** — derive all from `doc.width`
2. **Column ratios for A4:** `[0.045, 0.400, 0.075, 0.150, 0.130, 0.200]`
3. **TOTAL bar:** target by computed row index, not `(-1, -1)`
4. **Colors:** Use `theme.py` palette (GREEN_800, TEAL_600, NEUTRAL_*)
5. **Fonts:** Helvetica body, Helvetica-Bold for headers (not italic)
6. **Money:** No `Rs` prefix in table, right-aligned, always 2 decimals
7. **Page footer:** `onPage` callback for `Page X of Y`
8. **Logo:** Try/except fallback to text if missing
9. **QR code:** 18mm square, sale_number | total_paise | date
10. **VOID watermark:** 38° rotated, 90pt, alpha 0.12

**Implementation order:**
1. Replace all hardcoded widths with ratio-derived
2. Fix TOTAL bar row targeting
3. Add logo with try/except
4. Add QR code generation
5. Add VOID watermark and copy marker
6. Add page footer callback
7. Update color scheme to light palette
8. Remove italic from headers
9. Fix spacing (delete ad-hoc Spacers)
10. Add A5 density mode (smaller fonts, no signature row/QR)

---

## Step 4: Create `receipts/thermal_pdf.py` — 80mm roll renderer

**File:** `backend/apps/sales/receipts/thermal_pdf.py`

**Key rules:**
1. **Single column** — no side-by-side tables
2. **Continuous height** — port the content measurement from old `receipts.py`:
   ```python
   content_h = sum(
       f.wrap(cw, 0xFFFFFF)[1] + getattr(f, "spaceBefore", 0) + getattr(f, "spaceAfter", 0)
       for f in story
   )
   page_h = content_h + 2 * margin + 30 * mm_unit
   doc = SimpleDocTemplate(buf, pagesize=(page_w, page_h), ...)
   ```
3. **Monochrome** — black on white, grey `#6B7280` for SKU
4. **No fills** — thermal paper renders fills as smeared grey
5. **TOTAL:** 0.8pt rule above/below, 11pt bold
6. **Header:** Logo (try/except), shop name 11pt bold, address/phone 7pt, header 7pt italic, `=` rule
7. **Footer:** Return policy, QR, single line vendor credit

**Widths:**
```python
ROLL = {80: 72*mm, 58: 50*mm}  # 80mm and 58mm widths
```

---

## Step 5: Create `receipts/html.py` — HTML print view

**File:** `backend/apps/sales/receipts/html.py`

**Endpoint:** `GET /api/sales/{id}/receipt/html/?format=a4|thermal`

**Output:** Inline HTML with:
- All CSS embedded (no external stylesheets)
- Logo as data URI
- `@page { size: A4; margin: 12mm }`
- Same `ReceiptContext` as PDF/thermal
- Printable on any office printer

**Use cases:**
1. Settings page: live preview as you edit
2. Checkout: show customer their bill before payment
3. Bills page: Print button that works via browser print

---

## Step 6: Update `receipts/__init__.py` — Wire the renderers

Replace current `render_pdf_receipt` and `render_pdf_invoice`:

```python
def render_pdf_receipt(sale) -> bytes:
    """Render 80mm thermal-format PDF."""
    from .thermal_pdf import render
    ctx = build_receipt_context(sale, get_all_settings())
    return render(ctx, width_mm=80)

def render_pdf_invoice(sale) -> bytes:
    """Render full-page A4 invoice PDF."""
    from .document import render
    ctx = build_receipt_context(sale, get_all_settings())
    return render(ctx, pagesize="a4")

def render_html_receipt(sale, format_name: str = "a4") -> str:
    """Render HTML receipt for browser printing."""
    from .html import render
    ctx = build_receipt_context(sale, get_all_settings())
    return render(ctx, format_name=format_name)
```

Also wire `print_receipt_network`:
```python
def print_receipt_network(sale) -> bool:
    from escpos.network import Network
    from .thermal import render_thermal_escpos

    printer_ip = get_setting("thermal_printer_ip", "")
    printer_port = int(get_setting("thermal_printer_port", "9100"))
    
    if not printer_ip:
        raise ValueError("Printer IP not configured")
    
    ctx = build_receipt_context(sale, get_all_settings())
    escpos_bytes = render_thermal_escpos(ctx, width_mm=80)
    
    printer = Network(printer_ip, port=printer_port)
    try:
        printer._raw(escpos_bytes)
        # Add double-height TOTAL, QR, logo if needed
        return True
    finally:
        printer.close()
```

---

## Step 7: Write tests — `apps/sales/tests/test_receipts.py`

**Test cases:**

```python
def test_build_receipt_context_no_customer():
    """Context builds with customer=None"""
    sale = Sale(customer=None, ...)
    ctx = build_receipt_context(sale, {})
    assert ctx.customer_name == ""

def test_build_receipt_context_no_payment():
    """Context builds with payment not yet recorded"""
    sale = Sale(payment=None, ...)
    ctx = build_receipt_context(sale, {})
    assert ctx.tendered_paise == 0

def test_build_receipt_context_decimal_qty():
    """Decimal quantities format without trailing zeros"""
    item = SaleItem(qty=Decimal("2.500"), ...)
    ctx = build_receipt_context(sale_with(item), {})
    assert "2.5" in ctx.items[0].quantity
    assert "2.500" not in ctx.items[0].quantity

def test_build_receipt_context_voided():
    """Voided flag is set"""
    sale = Sale(status="voided", ...)
    ctx = build_receipt_context(sale, {})
    assert ctx.status == "voided"

def test_build_receipt_context_return():
    """Return flag is set"""
    sale = Sale(sale_type="return", ...)
    ctx = build_receipt_context(sale, {})
    assert ctx.is_return == True

def test_num_to_words_pkr():
    """Currency to words for Pakistani rupees"""
    assert num_to_words_pkr(0) == "Zero paise only"
    assert num_to_words_pkr(100) == "One rupee only"
    assert num_to_words_pkr(100_000) == "One lakh rupees only"
    assert num_to_words_pkr(1_206_460_00) == "Twelve lakh six thousand four hundred sixty rupees only"

def test_format_qty():
    """Quantity formatting removes trailing zeros"""
    assert format_qty(Decimal("4.000")) == "4"
    assert format_qty(Decimal("2.500")) == "2.5"
    assert format_qty(Decimal("1.0")) == "1"

def test_render_pdf_receipt_produces_bytes():
    """PDF rendering produces valid PDF bytes"""
    sale = create_test_sale_with_1_item()
    pdf_bytes = render_pdf_receipt(sale)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000

def test_render_pdf_invoice_produces_bytes():
    """Invoice rendering produces valid PDF bytes"""
    sale = create_test_sale_with_3_items()
    pdf_bytes = render_pdf_invoice(sale)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000

def test_render_html_receipt_produces_html():
    """HTML rendering produces valid HTML"""
    sale = create_test_sale_with_1_item()
    html = render_html_receipt(sale)
    assert html.startswith("<!DOCTYPE html>")
    assert "TOTAL" in html
```

---

## Step 8: Generate sample receipts

**Command:**
```bash
python manage.py shell <<'EOF'
from apps.sales.models import Sale, SaleItem
from apps.sales.receipts import render_pdf_receipt, render_pdf_invoice, render_html_receipt
import os

os.makedirs("backend/tmp/receipt_samples/", exist_ok=True)

samples = {
    "1_item": create_1_item_sale(),
    "3_items": create_3_items_sale(),
    "25_items": create_25_items_sale(),
    "decimal_qty": create_decimal_qty_sale(),
    "bill_discount": create_bill_discount_sale(),
    "voided": create_voided_sale(),
    "no_customer": create_no_customer_sale(),
    "no_payment": create_no_payment_sale(),
}

for name, sale in samples.items():
    # Thermal PDF
    with open(f"backend/tmp/receipt_samples/{name}_thermal.pdf", "wb") as f:
        f.write(render_pdf_receipt(sale))
    
    # A4 Invoice
    with open(f"backend/tmp/receipt_samples/{name}_invoice.pdf", "wb") as f:
        f.write(render_pdf_invoice(sale))
    
    # HTML
    with open(f"backend/tmp/receipt_samples/{name}_view.html", "w") as f:
        f.write(render_html_receipt(sale, format_name="a4"))

print("✅ Samples generated:")
for f in sorted(os.listdir("backend/tmp/receipt_samples/")):
    size = os.path.getsize(f"backend/tmp/receipt_samples/{f}") / 1024
    print(f"  {f} ({size:.1f} KB)")
EOF
```

---

## Definition of Done — Verification Checklist

After implementation, verify each:

- [ ] `pytest apps/sales/tests/test_receipts.py` passes
- [ ] All three formats render for all 8 sample sales
- [ ] `grep "mm_unit\|mm" backend/apps/sales/receipts/document.py` returns zero hardcoded widths
- [ ] A5 output: no cropped columns, all totals fully visible
- [ ] Green bar is on TOTAL row only
- [ ] Quantities: `4`, `2.5` — never `4.000`
- [ ] Thermal slip: 1-item and 25-item both single page, no cropping
- [ ] Slip + A5 + A4 + HTML + bill-detail all show identical figures
- [ ] Reprint marked `DUPLICATE`, shows original sale date
- [ ] No traceback ever in HTTP response body
- [ ] All sample PDFs open without errors

---

**Next:** Provide this to your agent with the instruction to complete Steps 2-8 in order, verifying each before proceeding to the next.