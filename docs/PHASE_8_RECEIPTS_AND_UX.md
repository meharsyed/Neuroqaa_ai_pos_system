# Speed Tech POS — Phase 8: Receipt Rebuild & Remaining UX

**Audience:** the coding agent working in this repository.
**Reads with:** `docs/UI_UX_REVAMP_SPEC.md` (Phases 1–6), `docs/PHASE_7_REMEDIATION.md` (P0–P2).
**Reviewed against:** working tree on top of commit `d5b0f47`.

---

## 0. Phase 7 scorecard — verified, not taken on trust

I checked every item. Here is the real state.

### Done ✅

| Item | Evidence |
|---|---|
| P0-1 Fault 1 — `get_all_settings` | Added to `apps/config/utils.py`. The 500 is gone. |
| P0-1 Faults 2, 3, 4 | `sale.items.all()`, `item.product.name/sku`, `sale.cashier.get_full_name()`, payment in try/except — all correct in `context.py`. |
| P0-1 Fault 7 — `num_to_words_pkr` | Lakh branch added; the `IndexError` above Rs 999,999 is fixed. |
| P0-2 — dead files | `receipts.py` and `receipt_templates.py` deleted. |
| P0-4 — shift 404 retries | `retry: false` on all three call sites. |
| P1-1 — sidebar emoji | ⚔️ gone, real SVG mark in place. |
| P1-2 — fabricated deltas | All three `trend={{...}}` props removed. |
| P1-6 — dark mode | `DarkModeToggle` now mounted in `AppTopbar`. |
| P1-7 — dev route | `/dev/kitchen-sink` removed. |

### Not done ❌

| Item | Reality |
|---|---|
| **`document.py` — untouched** | File mtime `Sep 3 14:34`; `context.py` is `18:40`. It was never opened. **Every layout defect from Phase 7 is still there, and it is the cause of both problems you reported.** |
| P0-1 Fault 5 | `line_total_paise=int(item.qty) * ...` still recomputes and truncates. `quantity=str(item.qty)` is why your invoice prints **`4.000`, `3.000`, `20.000`**. |
| P0-1 Fault 6 | `col_widths` still hardcoded at 174 mm. **This is your cropped thermal receipt.** |
| P0-1 Fault 8 | The view returns the **full Python traceback in the JSON response body**. That is a security leak — it exposes file paths and code to any authenticated user. It must be logged server-side, not returned. |
| P0-1 tests | `apps/sales/tests/` still holds only `test_api.py` and `test_services.py`. No `test_receipts.py`. |
| P1-3 Money / DateTime | **Zero progress.** Still 79 `paiseToRupees` and 11 `toLocale*` calls across 8 page files — identical counts to last review. |
| P1-4 toasts | 1 page → 2 pages (`CheckoutPage`, `BillsPage`). Settings, void, stock-in, shift open/close, returns, customer add are all still silent. |
| P1-5 date pickers | All 4 native `type="date"` inputs remain; Bills and Audit still show `mm/dd/yyyy`. |
| P1-8 palette guard | 55 → 37 raw hits. `emerald`/`amber`/`indigo` cleared ✅, but **30 × `slate-*`** and 6 × `purple`/`pink` remain, and **the ESLint rule was not added** — so this will drift again. |
| P1-9 `Payment.Method` | Still `cash / card / upi`. `bank_transfer` is still being written to a field that doesn't declare it. |
| P2-1 … P2-6 | Products still shows one "Low Stock" badge for both 0 and 1. No sparkline, no low-stock panel, no held carts, no bill slide-over, no returns stepper. |
| P2-7 | No `html.py`. No real thermal PDF. `render_thermal_escpos` still orphaned. No QR, VOID watermark, page numbers, or logo. |
| P2-8 | `public/fonts/` still empty while Tailwind asks for Inter var. |

**Read that middle row again:** the agent fixed the *crash* in the receipt path and then reported the whole receipt section complete without opening the file that draws the receipt. Everything in §1–§3 below is a consequence.

---

# 1. Why your thermal receipt is cropped

`receipts/__init__.py`:

```python
def render_pdf_receipt(sale) -> bytes:
    """Render 80mm thermal-format PDF (default for POS)."""
    ...
    # For now, use A5 as "thermal" equivalent - can adjust later
    pdf_buffer = render_document_pdf(ctx, pagesize="a5")
```

It is not a thermal renderer. It renders **the A4 invoice on A5 paper**. And `document.py` hardcodes:

```python
col_widths  = [8*mm, 74*mm, 14*mm, 26*mm, 22*mm, 30*mm]   # 174 mm
totals_table colWidths=[70*mm, 30*mm]                      # 100 mm
sig_table    colWidths=[60*mm, 20*mm, 60*mm]               # 140 mm
```

A5 is 148 mm wide. Minus the 10 mm margins the frame is **128 mm**. A 174 mm table in a 128 mm frame doesn't error — ReportLab just draws past the right edge and the page clips it. That is precisely your screenshot: `ESCRIPTION` sheared on the left, `AMOUNT` running off the right, and every totals value missing because the 100 mm totals table sits in a 64 mm half-column.

**It "worked before" because it used to be a different renderer.** The old `receipts.py` — which Phase 7 told you to delete because it was shadowed and unreachable — contained a genuine 80 mm roll renderer. That is what produced the good narrow receipt you have. Deleting it removed the last copy.

### Good news: it is recoverable

The deletion is not committed. The file is still in git at `HEAD`:

```bash
git show HEAD:backend/apps/sales/receipts.py > /tmp/old_receipts.py
```

The part worth studying is its page-sizing trick, which is why it always produced exactly one continuous slip with no cropping and no trailing blank space:

```python
content_h = sum(
    f.wrap(cw, 0xFFFFFF)[1] + getattr(f, "spaceBefore", 0) + getattr(f, "spaceAfter", 0)
    for f in story
)
page_h = content_h + 2 * margin + 30 * mm_unit
doc = SimpleDocTemplate(buf, pagesize=(page_w, page_h), ...)
```

It measures the story, then sizes the page to the content. **Port this into the new `receipts/thermal_pdf.py`.** Do not re-derive it; it is correct and it is the whole reason a variable-length receipt fits on one continuous page.

---

# 2. The A4 / A5 invoice — rebuild `document.py`

Your screenshot of `SALE-20260903-00036` shows nine distinct defects. Rather than patch them, rewrite the file against the spec below.

## 2.1 What is wrong now

1. **The shop name is printed twice** — once in the green band, again in the company block 8 mm below.
2. **The green TOTAL bar is on the wrong row.** `('BACKGROUND', (0,-1), (1,-1), ...)` targets the *last* row, and the last row is `Change`. So `Change 665.06` is emphasised and the actual total is plain text. This is the most damaging defect on the page — the one number a customer looks for is the one you didn't highlight.
3. **Quantities print as `4.000`, `3.000`, `20.000`** — `str(Decimal)` straight from the DB.
4. **Column headers are bold-italic.** `styles['Heading4']` is `Helvetica-BoldOblique`. Italic column headers read as an accident.
5. **Dead vertical space.** An empty `Paragraph("")` cell in `billto_table`, an empty-string `rule_table` row that still claims default 6 pt padding top and bottom, and five stacked `Spacer`s. That is the irregular spacing you're seeing.
6. **`BILL TO` and the invoice metadata are in two different tables** stacked vertically, so they don't align and the block is twice as tall as it needs to be.
7. **`('PADDING', ...)`** is not a valid ReportLab command (only `LEFT/RIGHT/TOP/BOTTOMPADDING`). It is silently ignored in two places.
8. **No logo, no page numbers, no QR, no VOID watermark, no `TAX INVOICE` label.**
9. **`−` (U+2212)** is used for the discount sign. Base-14 Helvetica under WinAnsi has no such glyph. Use ASCII `-`.

## 2.2 Light theme — as you asked

Your instinct is right and it goes further than preference: **this is printed on white paper.** A dark ground wastes toner, and on a laser printer a large dark fill produces banding. The mockup you liked read dark only because you were viewing it in dark mode; the design was always light.

Keep the token values already in `theme.py` and use them like this:

| Element | Colour | Notes |
|---|---|---|
| Page ground | white | never fill it |
| Top accent rule | `GREEN_800 #1A3A28` | a 4 mm bar, full content width — the letterhead echo |
| Shop name | `GREEN_800` | 13 pt bold |
| `TAX INVOICE` label + field labels | `TEAL_600 #12898A` | 8 pt, caps, tracked |
| Items header row | `GREEN_800` fill, white text | the only heavy fill above the total |
| Zebra rows | `TEAL_50 #EEFAF9` | even rows only |
| Row rules | `NEUTRAL_200 #DFE6E8` | 0.4 pt under each row, no vertical grid lines |
| Body text | `NEUTRAL_800 #1D272C` | |
| Muted / SKU / meta | `NEUTRAL_500 #64757D` | |
| TOTAL bar | `GREEN_800` fill, white text | the second and last heavy fill |
| Footer band | `TEAL_50` fill, `TEAL_800` text | light, not solid teal — matches the letterhead's pale end |

Two filled elements per page: the items header and the TOTAL bar. Everything else is ink on white.

## 2.3 The layout, exactly

A4 portrait, margins **14 mm** left/right, **12 mm** top, **14 mm** bottom → **182 mm** usable.

```
┌──────────────────────────────────────────────────────────────┐
│ ████████████████████████████████████████████████████████████ │  4mm GREEN_800 bar
│                                                              │  6mm
│  ┌────┐  SPEED TECH SOLUTIONS            TAX INVOICE         │  ← teal, right
│  │LOGO│  Agha Siraj Complex,             No.    SALE-…-00036 │
│  │22mm│  Circular Road, Quetta           Date   04 Sep 2026  │
│  └────┘  +92 321 8131109                 Time   00:49        │
│          speedtech.solutions             Cashier admin admin │
│                                                              │  5mm
│  ──────────────────────────────────────────────────────────  │  0.8pt TEAL_600
│                                                              │  4mm
│  BILL TO                                 PAYMENT             │  ← both teal labels,
│  Walk-in Customer                        Cash                │    ONE table, two cols
│  —                                       Completed           │
│                                                              │  5mm
│  ┌──────────────────────────────────────────────────────────┐│
│  │ #  DESCRIPTION            QTY      RATE    DISC   AMOUNT ││  GREEN_800 / white
│  ├──────────────────────────────────────────────────────────┤│  7.5pt BOLD, not italic
│  │ 1  Blue Ceramic Tile 30x30  4  3,500.00       —  14,000.00││
│  │    TILE-001                                              ││  ← SKU 6pt muted
│  │ 2  PVC Elbow 4 inch         3     80.00       —     240.00││  ← TEAL_50 zebra
│  │    ELBOW-4IN                                             ││
│  │ 3  UPVC Pipe 4 inch        20    480.00       —   9,600.00││
│  │    PIPE-4IN                                              ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │  5mm
│  NOTES                          Subtotal          23,840.00  │
│  Thanks for your purchase.      Bill discount       -476.80  │
│  Goods returnable within 7      Tax (17%)          3,971.74  │
│  days with this receipt.       ┌───────────────────────────┐ │
│                                │ TOTAL       Rs 27,334.94  │ │  ← GREEN_800, white,
│  AMOUNT IN WORDS               └───────────────────────────┘ │    12pt bold
│  Twenty-seven thousand three    Paid (Cash)       28,000.00  │
│  hundred thirty-four rupees     Change               665.06  │
│  and ninety-four paise only.                                 │
│                                                              │  10mm
│  ____________________            ____________________        │
│  Customer Signature              For Speed Tech Solutions    │
│                                                              │
│  [QR]                                                        │  ← bottom-left, 18mm
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  A name of Trust, Reliability and Quality!    Page 1 of 1     │  TEAL_50 band
└──────────────────────────────────────────────────────────────┘
```

### Column widths — derive them, never hardcode

```python
usable = doc.width          # ReportLab already computes pagesize - margins
RATIOS = [0.045, 0.400, 0.075, 0.150, 0.130, 0.200]   # sums to 1.0
col_widths = [usable * r for r in RATIOS]
```

Apply the same treatment to the totals block (`[0.62, 0.38]` of the right half) and the signature row (`[0.45, 0.10, 0.45]` of `doc.width`). **After this change, nothing in the file may contain a hardcoded `mm` width.** That single rule is what makes A5 work.

### Fix the TOTAL bar targeting

Stop using `-1`. Record the index when you build the row:

```python
rows, total_row = [], None
rows.append(["Subtotal", money(ctx.subtotal_paise)])
if ctx.bill_discount_paise:
    rows.append(["Bill discount", "-" + money(ctx.bill_discount_paise)])
if ctx.tax_paise:
    rows.append([f"Tax ({tax_pct}%)", money(ctx.tax_paise)])
total_row = len(rows)
rows.append(["TOTAL", "Rs " + money(ctx.total_paise)])
rows.append([f"Paid ({method_label})", money(ctx.tendered_paise)])
if ctx.change_paise:
    rows.append(["Change", money(ctx.change_paise)])
```

Then style `(0, total_row), (1, total_row)` — never `(0, -1)`.

### Column-header style

Replace all six `styles['Heading4']` with one explicit style:

```python
th = ParagraphStyle("TH", parent=styles["Normal"],
                    fontName="Helvetica-Bold", fontSize=7.5,
                    textColor=colors.white, leading=9,
                    spaceBefore=0, spaceAfter=0)
```

`Heading4` carries `spaceBefore=6` / `spaceAfter=4`, which is also inflating your header row height.

### Vertical rhythm

Delete every ad-hoc `Spacer` and use one scale: `Spacer(1, 4*mm)` between blocks, `Spacer(1, 6*mm)` before the signature row. Delete the empty `Paragraph("")` cell and the empty-string `rule_table`; draw the rule with `HRFlowable(width="100%", thickness=0.8, color=THEME.ACCENT_RULE, spaceBefore=4, spaceAfter=4)`.

### Money and quantity formatting

In `receipts/utils.py`:

```python
from decimal import Decimal

def format_qty(qty) -> str:
    """Decimal('4.000') -> '4';  Decimal('2.500') -> '2.5'"""
    d = Decimal(str(qty)).normalize()
    if d == d.to_integral_value():
        d = d.quantize(Decimal(1))
    return format(d, "f")
```

Money inside the table: **no `Rs` prefix, always two decimals, right-aligned.** `Rs` appears exactly once, on the TOTAL row. Use `Helvetica` for money, not `Courier` — Courier is a typewriter face and looks cheap next to Helvetica; Helvetica's digits are already fixed-width, so columns still align.

### Page footer

Use an `onPage` callback so `Page X of Y` is real:

```python
def _footer(canvas, doc_):
    canvas.saveState()
    canvas.setFillColor(THEME.ACCENT_SOFT_BG)
    canvas.rect(0, 0, doc_.pagesize[0], 12*mm, stroke=0, fill=1)
    canvas.setFillColor(THEME.TEAL_800); canvas.setFont("Helvetica", 7.5)
    canvas.drawString(14*mm, 4.5*mm, ctx.receipt_header)
    canvas.drawRightString(doc_.pagesize[0] - 14*mm, 4.5*mm, f"Page {doc_.page}")
    canvas.restoreState()

doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
```

For a true `Page X of Y`, subclass `BaseDocTemplate` with a two-pass build, or accept `Page X` — for a retail invoice, `Page X` is enough. Add repeating table headers on page 2+ with `items_table.repeatRows = 1`.

### Void watermark and copy marker

```python
if ctx.status == "voided":
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 90)
    canvas.setFillColor(colors.Color(0.71, 0.14, 0.09, alpha=0.12))
    canvas.translate(doc_.pagesize[0]/2, doc_.pagesize[1]/2)
    canvas.rotate(38); canvas.drawCentredString(0, 0, "VOID")
    canvas.restoreState()
```

Accept `?copy=original|duplicate` on the endpoint and print the word top-right at 7 pt in `NEUTRAL_400`.

### QR code

Use ReportLab's built-in — no new dependency:

```python
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing

code = qr.QrCodeWidget(f"{ctx.sale_number}|{ctx.total_paise}|{ctx.created_at:%Y-%m-%d}")
b = code.getBounds()
d = Drawing(18*mm, 18*mm, transform=[18*mm/(b[2]-b[0]), 0, 0, 18*mm/(b[3]-b[1]), 0, 0])
d.add(code)
```

### Logo

Add `frontend/public/brand/logo-invoice.png` (600 px wide, transparent) and mirror it to `backend/apps/sales/receipts/assets/logo-invoice.png` so the backend has no dependency on the frontend build. Load with `Image(path, width=22*mm, height=22*mm, kind='proportional')` and **wrap it in a try/except** — a missing logo must degrade to text, never 500.

## 2.4 A5 is a size, not a layout

Once widths are ratio-derived, A5 works from the same code. Add one density switch:

```python
DENSITY = {"a4": dict(base=8, header=7.5, row_pad=4, logo=22),
           "a5": dict(base=7, header=6.5, row_pad=2.5, logo=16)}
```

Drop the signature row and the QR on A5 — there isn't room.

---

# 3. The 80 mm thermal receipt — a separate renderer

Create `receipts/thermal_pdf.py`. **Do not route this through `render_document_pdf`.**

```python
ROLL = {80: 72*mm, 58: 50*mm}     # printable width, not paper width
```

Rules that make a thermal slip work and an A4 layout fail:

- **Single column.** No side-by-side tables anywhere. `BILL TO` / `PAYMENT` stack; notes and totals stack.
- **Continuous page height.** Port the `content_h` measurement from `git show HEAD:backend/apps/sales/receipts.py`. One page, no trailing whitespace, no cropping — regardless of item count.
- **Item lines wrap, never truncate.** Name on its own line at full width; `qty × rate` and the amount on the next line, amount right-aligned. Your old receipt broke `Rs.22,000` across two lines as `Rs.22,00 / 0` — that is a too-narrow column, and this layout removes the cause.
- **Two columns only in the totals block:** label left, amount right, at 100% width.
- **TOTAL** gets a 0.8 pt rule above and below and 11 pt bold. No fills — thermal paper renders solid blocks as smeared grey and it wastes the roll.
- **Monochrome only.** No greens, no teals, no zebra. Black on white, plus grey `#6B7280` for the SKU line.
- Header: logo as a 1-bit raster if available, then shop name 11 pt bold, address and phone 7 pt, `receipt_header` 7 pt italic, then a `=` rule.
- Footer: return policy, QR of the bill number, then `Powered by Neuroqaa.ai`.

### Remove the vendor advertisement from the customer's receipt

The old slip printed four lines of Neuroqaa marketing:

```
Neuroqaa.ai Pvt. Ltd. — Modern POS for Modern Businesses
Sales & Support: 0333-1445252
www.neuroqaa.ai
```

That is your sales pitch on **Speed Tech's** customer receipt, with your support number where the customer expects Speed Tech's. Reduce it to a single 6 pt line, `Powered by Neuroqaa.ai`, and make even that removable via a `show_vendor_credit` setting. A white-label client will ask.

### Wire the ESC/POS renderer that already exists

`render_thermal_escpos()` is written and never called. `print_receipt_network()` sends `render_thermal_text()` instead, so you lose the cut command and the double-height total. Fix:

```python
printer._raw(render_thermal_escpos(ctx, width_mm))
```

Add the double-height TOTAL (`\x1d\x21\x11` before, `\x1d\x21\x00` after), `printer.qr(ctx.sale_number)` guarded by a capability check, and `printer.image()` for the logo guarded by try/except.

## 3.1 Name the options honestly

The dropdown says "Full Invoice (A4)" and — per `CheckoutPage.tsx` — the alternative resolves to `thermal`. Once the three renderers are real, offer exactly three and label them for a shopkeeper, not a developer:

| Value | Label | Renderer |
|---|---|---|
| `thermal` | Thermal slip (80 mm) | `thermal_pdf.render(ctx, 80)` |
| `a5` | Half-page receipt (A5) | `document.render(ctx, "a5")` |
| `invoice` | Full invoice (A4) | `document.render(ctx, "a4")` |

Delete `components/ReceiptTemplateSelector.tsx`'s four fictional templates (Classic / Modern / Itemized / Compact with 🎯 ✨ 📋 📄) — those renderers no longer exist, so the picker is offering choices the backend cannot honour. Replace with three real options and rendered thumbnails.

## 3.2 Build the HTML print view — it is the cheapest win left

`receipts/html.py` was specified in Phase 5 and never written. One function, one template, same `ReceiptContext`:

```
GET /api/sales/{id}/receipt/html/?format=a4|thermal
```

Inline all CSS, embed the logo as a data URI, `@page { size: A4; margin: 12mm }`. It buys three things: any office printer works without ReportLab, the Settings page gets a **live receipt preview** as it changes, and the checkout screen can show the customer their bill before payment.

---

# 4. Shared fixes in `context.py`

```python
# WRONG — recomputes and truncates a decimal quantity
line_total_paise=int(item.qty) * item.unit_price_paise - item.discount_paise
quantity=str(item.qty)

# RIGHT
line_total_paise=item.subtotal_paise
quantity=format_qty(item.qty)
```

Also:

- Replace the bare `except:` around `sale.payment` with `except ObjectDoesNotExist:` — a bare except swallows `KeyboardInterrupt` and masks real errors.
- Add `tax_pct` to the context from settings, so the invoice can print `Tax (17%)` instead of a bare `Tax`.
- Add `is_return = sale.sale_type == "return"` and have the renderers print **CREDIT NOTE** instead of **TAX INVOICE**, with negative amounts. `sale_type` exists on the model and no renderer reads it.
- Add the invariant check and log a warning when the item sum disagrees with `sale.subtotal_paise`.

**Fix `views.py` first:** it currently returns the traceback to the client.

```python
except Exception:
    logger.exception("Receipt PDF failed for sale %s", pk)
    return Response({"detail": "Receipt generation failed."}, status=500)
```

**Then write `apps/sales/tests/test_receipts.py`** — `build_receipt_context` (no customer, no payment, decimal qty, voided, return), `num_to_words_pkr` (0, 1, 99, 100, 9999, 100000, 1206460, 14791140), `format_qty`, and a render smoke test for all three renderers asserting non-empty PDF bytes starting with `%PDF`.

### Also: `Payment.Method` still doesn't include what you store

`cash / card / upi` — but the DB holds `bank_transfer` and the UI offers it. `upi` is an Indian payment rail this shop does not use. Change to `cash / card / bank_transfer / mobile_wallet`, migrate any `upi` rows, and use `get_method_display()` in the renderers so the invoice prints "Bank Transfer" and not "Bank_transfer".

---

# 5. Remaining UI/UX work

## 5.1 Carried over and still open

- **P1-3 — adopt `Money` and `DateTime`.** 79 + 11 call sites. This is why Dashboard prints `Rs 80,262.00` and Bills prints `Rs. 147,911.40`. Convert all of them, standardise on `Rs` with no period, and add `decimals="auto"` so table cells show `Rs 14,000` while totals show `Rs 14,000.00`.
- **P1-4 — toasts on every mutation.** Settings save especially; it currently gives no confirmation at all.
- **P1-5 — the date range picker.** Four native inputs still showing US order.
- **P1-8 — add the ESLint rule.** Without it this regresses every phase:

```js
"no-restricted-syntax": [
  "error",
  {
    selector: "Literal[value=/\\b(slate|gray|zinc|neutral|stone|emerald|cyan|sky|indigo|violet|purple|rose|pink|fuchsia|lime)-[0-9]{2,3}\\b/]",
    message: "Use a design token. See docs/UI_UX_REVAMP_SPEC.md §3."
  }
]
```

Then clear the remaining 37 hits — `slate-*` → `n-*`, delete `purple`/`pink`.

- **P2-1** Products: `Out` (danger) must be visually distinct from `Low` (warning). Zero stock is unsellable; one unit is not.
- **P2-3** Dashboard: revenue sparkline and the low-stock panel with inline `+Stock`.
- **P2-4** Checkout: move the shortcut legend into the empty-cart state; build held carts.
- **P2-5** Bills: detail slide-over behind the eye icon, summary strip, use the `Pagination` primitive.
- **P2-6** Returns stepper; Settings two-column layout with live receipt preview.
- **P2-8** Ship the `.woff2` files or drop the font names from the Tailwind config.

## 5.2 New — worth doing, in value order

These are not in any earlier document. They come from the domain: a security-equipment dealer in Quetta.

**1. Serial-number capture on sale.** Cameras, NVRs and hard drives carry serials, and warranty claims are settled by serial. Add a `SaleItemSerial` model (`sale_item`, `serial`, `warranty_months`), an optional per-line serial field at checkout, print serials under each line on the invoice, and make them searchable. When a customer walks in with a failed camera, "which invoice was this on and is it in warranty" becomes one lookup instead of a shoebox. **For this client this is more valuable than anything else on this list.**

**2. Khata / customer credit.** Trade customers — electricians, contractors, integrators — buy on account. Add `credit` as a payment method, an `outstanding_paise` balance on Customer, a payments-received screen, and an ageing view. Today a partial payment cannot be recorded at all.

**3. Share receipt on WhatsApp.** The dominant channel in Pakistan. Once `receipts/html.py` exists, a `wa.me/{phone}?text={summary+link}` button on the post-sale screen and in the bill slide-over costs almost nothing.

**4. Quotations.** Security work is quoted before it is sold. A quote is a Sale with `status="quote"` that reserves no stock, prints on the same invoice layout marked **QUOTATION**, and converts to a sale in one click.

**5. Reprint / duplicate from Bills.** No way to reprint a past bill today. Add Print / PDF / WhatsApp to the bill slide-over, marked `DUPLICATE`.

**6. Warn when selling with no open shift.** Sales are being created with `shift = null` — your Shift page shows no open shift while 34 bills exist. Cash reconciliation is meaningless. Show a dismissible banner at checkout, and let Settings enforce it as a hard block.

**7. Stock-out guard at the point of search.** Grey out zero-stock products in checkout search results and show the live count next to each. Cheaper than an error after the fact.

**8. Daily closing report.** One button at shift close producing a printable summary — opening float, sales by method, discounts, expected vs counted, variance. That is what an owner actually wants at 9 pm.

**9. Offline queue (desktop mode).** The product promises offline operation. Queue sales in IndexedDB when the API is unreachable and sync on reconnect. Non-trivial — schedule it, don't bolt it on.

---

# 6. Prompts

Give one at a time. Verify between each.

> **8A — Receipts, backend only.** Read `docs/PHASE_8_RECEIPTS_AND_UX.md` §1–§4. First fix `views.py` so tracebacks are logged, not returned in the response body. Then fix `context.py` (§4). Then rewrite `receipts/document.py` completely against the §2.3 layout — every width derived from `doc.width`, the TOTAL bar targeted by computed row index, explicit non-italic header style, `HRFlowable` rules, `onPage` footer, VOID watermark, QR, logo with a try/except fallback, and the §2.2 light palette. Then create `receipts/thermal_pdf.py` per §3, porting the content-measured page-height technique from `git show HEAD:backend/apps/sales/receipts.py` — do not route it through `render_document_pdf`. Then `receipts/html.py` per §3.2. Then write `apps/sales/tests/test_receipts.py`. Finally, render samples for: 1 item, 3 items, 25 items, a decimal quantity, a bill discount, a voided sale, no customer, no payment — in all three formats — into `backend/tmp/receipt_samples/`, and list them for me.

> **8B — Frontend carry-over.** Read §5.1. Do them in this order: ESLint rule + clear the 37 hits; `Money`/`DateTime` adoption; toasts on every mutation; the date-range picker; then P2-1, P2-3, P2-4, P2-5, P2-6, P2-8. One commit each, stop for review after each.

> **8C — New capability.** Read §5.2. Implement item 1 (serial numbers) first, as a full vertical slice: model, migration, checkout capture, invoice print, search. Stop for review before starting item 2.

---

# 7. Definition of done for the receipt system

1. All three formats render for all eight sample sales without error.
2. **No hardcoded `mm` width remains in `document.py`.** Grep to prove it.
3. A5 output has nothing cropped — every column and every total value is fully inside the page.
4. The green bar is on the TOTAL row and nowhere else.
5. Quantities print `4`, `2.5` — never `4.000`.
6. The thermal slip is one continuous page for 1 item and for 25 items, with no line exceeding the roll width and no number broken across lines.
7. Slip, A5, A4, HTML view and the on-screen bill all show identical figures, sourced from one `ReceiptContext`.
8. A reprint of an old bill shows the original sale date and is marked `DUPLICATE`.
9. No traceback ever reaches an HTTP response body.
10. `pytest apps/sales/tests/test_receipts.py` passes.

---

*Speed Tech Solutions POS · Phase 8 · reviewed against the working tree on `d5b0f47`*
