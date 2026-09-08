# Speed Tech POS — Phase 7: Remediation

**Audience:** the coding agent working in this repository.
**Prerequisite:** `docs/UI_UX_REVAMP_SPEC.md` (Phases 1–6). This document is the **defect list from reviewing your Phase 1–6 output** against that spec and against the running app.
**Repo:** `pos-system-GT` · reviewed at commit `d5b0f47`

---

## 0. What you got right

Say it plainly so you don't undo it: the shell landed. `AppSidebar` / `AppTopbar` / `PageHeader` / `PageContainer` exist and every page uses them; the sidebar now uses the `chrome-*` tokens and the nav is legible; the shift pill in the topbar works and is genuinely useful; `index.html` carries the real title, favicon and theme-color; the brand SVGs are on disk; the `receipts/` package has the right shape with a real `ReceiptContext`; and the primitives (`Card`, `DataTable`, `StatTile`, `Money`, `DateTime`, `Toast`, `EmptyState`, `Skeleton`, `Pagination`, `ConfirmDialog`, `Tooltip`, `FormField`) all got built.

The problems below are of three kinds: **things that are broken**, **things you built but never connected**, and **things the spec asked for that were skipped**. The second category is the largest — a lot of good code is sitting unused.

**Work P0 → P1 → P2, in order. Do not start P1 until every P0 item is verified fixed.**

---

# P0 — Broken. Fix first.

## P0-1 · The receipt PDF 500 — full root-cause chain

`GET /api/sales/34/receipt/pdf/?template=invoice` → 500. There are **six** independent faults in this one code path. The first one is what's firing today; the rest are behind it and will each surface in turn as you fix the one above.

### Fault 1 — `get_all_settings` does not exist *(this is today's 500)*

`apps/sales/receipts/__init__.py` calls, in four separate functions:

```python
from apps.config.utils import get_all_settings
```

`apps/config/utils.py` defines **only** `get_setting(key, default="")`. There is no `get_all_settings` anywhere in the codebase — I grepped. The import is inside the function bodies, so Django starts fine and every other endpoint works; the `ImportError` only fires when someone presses PDF. That is exactly the symptom.

**Fix — add the helper** to `apps/config/utils.py`:

```python
def get_all_settings() -> dict[str, str]:
    """Return every stored setting as a {key: value} dict, in one query."""
    from .models import Setting
    return dict(Setting.objects.values_list("key", "value"))
```

Then in `receipts/__init__.py`, hoist both imports to module level (there is no circular-import risk here) and stop repeating the same three lines in four functions:

```python
from apps.config.utils import get_all_settings

def _ctx(sale):
    return build_receipt_context(sale, get_all_settings())
```

…and have `render_text_receipt`, `render_pdf_receipt`, `render_pdf_invoice` and `print_receipt_network` all call `_ctx(sale)`.

### Fault 2 — `sale.items` is a manager, not a list

`receipts/context.py`:

```python
for item in sale.items:          # TypeError: 'RelatedManager' object is not iterable
```

**Fix:** `for item in sale.items.select_related("product").all():`
Use `select_related` — otherwise you fire one query per line item.

### Fault 3 — three field names that don't exist on the models

Check `apps/sales/models.py`. `SaleItem` has: `sale, product, qty, unit_price_paise, discount_paise, subtotal_paise`. `Sale` has `cashier` (a FK to User). So all three of these raise `AttributeError`:

| `context.py` uses | Reality |
|---|---|
| `item.product_name` | ✗ no such field → `item.product.name` |
| `item.product_sku` | ✗ no such field → `item.product.sku` |
| `sale.cashier_name` | ✗ no such field → `sale.cashier.get_full_name()` |

For the cashier, mirror what the UI already shows ("admin admin"):

```python
cashier = sale.cashier
cashier_name = (cashier.get_full_name() or cashier.email or "—") if cashier else "—"
```

### Fault 4 — `sale.payment` raises instead of returning `None`

```python
tendered_paise=sale.payment.amount_tendered_paise if sale.payment else 0,
```

`Payment` is a `OneToOneField` with `related_name="payment"`. On the reverse side, when no row exists, Django raises `Payment.DoesNotExist` — it does **not** return `None`. So `if sale.payment` raises before the ternary can evaluate. Any sale without a payment row (a return, a partially-rolled-back sale) 500s.

**Fix:** resolve it once, defensively:

```python
payment = getattr(sale, "payment", None)   # still raises on reverse o2o — use the explicit form:
try:
    payment = sale.payment
except ObjectDoesNotExist:
    payment = None
```

Import `from django.core.exceptions import ObjectDoesNotExist`. Then use `payment.amount_tendered_paise if payment else 0`, etc. Note `Payment.Method` has no `bank_transfer` member (only `cash/card/upi`) yet the activity log shows `bank_transfer` values in the DB — see **P1-9**.

### Fault 5 — line totals are recomputed, and truncated

```python
line_total_paise=int(item.qty) * item.unit_price_paise - item.discount_paise,
```

Two problems. `qty` is `DecimalField(max_digits=10, decimal_places=3)`, so `int()` silently floors 2.5 → 2 and the printed line total is wrong for any non-whole quantity. And this recomputes a value the row already stores.

**Fix:** use the stored value. This is the whole point of `ReceiptContext`:

```python
line_total_paise=item.subtotal_paise,
```

Then verify the invariant in the same function and log loudly if it breaks, rather than silently printing a number that disagrees with the database:

```python
computed = sum(i.subtotal_paise for i in sale.items.all()) 
if sale.subtotal_paise and computed != sale.subtotal_paise:
    logger.warning("Receipt %s: item sum %s != stored subtotal %s",
                   sale.sale_number, computed, sale.subtotal_paise)
```

Also format the quantity for display rather than dumping the raw Decimal — `str(Decimal("10.000"))` prints `10.000` on the invoice. Add to `receipts/utils.py`:

```python
def format_qty(qty) -> str:
    """10.000 -> '10';  2.500 -> '2.5'"""
    q = Decimal(qty).normalize()
    return format(q, "f")
```

### Fault 6 — the A5 path cannot lay out *(will fire as soon as you fix the above)*

`render_pdf_receipt()` calls `render_document_pdf(ctx, pagesize="a5")`. But `document.py` hardcodes:

```python
col_widths = [8*mm, 74*mm, 14*mm, 26*mm, 22*mm, 30*mm]   # = 174mm
```

A5 is 148mm wide; minus the 10mm margins the frame is **128mm**. A 174mm table in a 128mm frame raises `LayoutError: Table too wide`. So the *default* PDF button (`?template=thermal`, no query param) is broken even after Faults 1–5 are fixed. You only ever tested `?template=invoice`.

**Fix:** derive the widths from the frame instead of hardcoding millimetres:

```python
usable = page_size[0] - doc.leftMargin - doc.rightMargin
ratios = [0.042, 0.389, 0.074, 0.137, 0.116, 0.158]   # sums to 1.0
col_widths = [usable * r for r in ratios]
```

Apply the same treatment to `totals_table` (`70mm + 30mm` = 100mm, also too wide for A5) and `sig_table` (`60+20+60` = 140mm, too wide for A5).

### Fault 7 — `num_to_words_pkr` crashes above Rs 999,999

Not in this request's path, but it will take down the next one. In `receipts/utils.py`:

```python
def _words_from_rupees(num):
    ...
    thousands = num // 1000
    thousands_part = _words_under_thousand(thousands) + " thousand"
```

For Rs 1,206,460 (your Audit page already shows revenue of Rs 1,206,460.94), `thousands` = 1206, which is **not** under a thousand. `_words_under_thousand(1206)` falls to the `else` branch and evaluates `ones[1206 // 100]` = `ones[12]` → **`IndexError: list index out of range`**. Any invoice at or above Rs 1,000,000 will 500.

**Fix:** implement real scale grouping. Pakistani invoices conventionally use lakh/crore, so use that:

```python
SCALES = [(10_000_000, "crore"), (100_000, "lakh"), (1_000, "thousand")]

def _words_from_rupees(num: int) -> str:
    if num == 0:
        return ""
    for value, name in SCALES:
        if num >= value:
            head = _words_from_rupees(num // value)
            tail = num % value
            return f"{head} {name}" + (f" {_words_from_rupees(tail)}" if tail else "")
    return _words_under_thousand(num)
```

**Write the unit tests the spec asked for and you skipped** — `backend/apps/sales/tests/test_receipts.py`, covering `0`, `1` (→ "One rupee only"), `100`, `9999`, `100000`, `14791140`, `120646094`, and `999999999999`. The 1,206,460 case is the regression test for this bug.

### Fault 8 — the view swallows the traceback

`apps/sales/views.py` `receipt_pdf` wraps generation in a bare `try/except` that returns a 500 body with no logging. That is why you have been guessing at this for four rounds: the traceback never reached the console. **This is the reason this bug survived three attempts, so fix it before anything else.**

```python
import logging
logger = logging.getLogger(__name__)
...
except Exception:
    logger.exception("Receipt PDF failed for sale %s", sale.sale_number)
    return Response(
        {"detail": "Receipt generation failed. See server log."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
```

Also confirm `template` is bound before the `fname = ... if template == "invoice"` line at ~197 — if it is assigned inside the `try` and the `except` path falls through to it, you get a `NameError` masking the real error. Read it once and hoist the assignment above the `try`.

### P0-1 acceptance

- [ ] `pytest backend/apps/sales/tests/test_receipts.py` passes, including the Rs 1,206,460 words case.
- [ ] Add a management command or test that renders **both** templates for: a 1-item sale, a 25-item sale, a sale with a decimal quantity (2.5), a sale with a bill discount, a **voided** sale, a sale with **no** customer, and a sale with **no** payment row. Save them under `backend/tmp/receipt_samples/` and tell me they're there.
- [ ] Both the A4 invoice and the default (thermal) PDF open without error from the checkout screen.
- [ ] The server log shows a real traceback if generation ever fails again.

---

## P0-2 · Two dead 31 KB files are shadowing the new package

`backend/apps/sales/` currently contains **all three** of:

- `receipts/` — the new package (correct)
- `receipts.py` — 31 KB, the old module
- `receipt_templates.py` — 31 KB, the old four-template renderer

Python resolves the **package** over the module, so `receipts.py` is unreachable dead code that still looks live to grep, to you, and to the next developer. `receipt_templates.py` is imported by nothing.

**Fix:** `git rm backend/apps/sales/receipts.py backend/apps/sales/receipt_templates.py`. Confirm with a grep that nothing references them, and that `python manage.py check` passes. Delete the stale `__pycache__` entries too.

---

## P0-3 · `alert()` is still the error channel

`Toaster` is mounted in `App.tsx` and works. Yet five call sites still use blocking browser `alert()`:

| File | Line | What |
|---|---|---|
| `lib/reports.ts` | 74 | "Popup blocked…" |
| `lib/reports.ts` | 80 | "Failed to load receipt: …" ← **the black modal in my screenshot** |
| `pages/CheckoutPage.tsx` | 430 | receipt sent to printer |
| `pages/CheckoutPage.tsx` | 431 | printer not available |
| `pages/BillsPage.tsx` | 203 | printer not available |

A modal `alert()` freezes the whole page and, on a till, blocks the cashier mid-transaction. Replace all five with `toast({ variant: "error" | "success", ... })`. `lib/reports.ts` is not a component, so have it **throw** a typed error and let the calling component toast it — don't import the toast hook into a lib module.

While you are there: the PDF failure currently gives the user `Failed to load receipt: Request failed with status code 500`. Surface the server's `detail` field instead, and add a Retry action to the toast.

---

## P0-4 · `/api/shifts/current/` is fired four times and retried on 404

The console screenshot shows **four** `404 (Not Found)` entries for `api/shifts/current/`. `PROJECT_CONTEXT.md` §17.2 is explicit that a 404 here means "no shift open" and is expected — the frontend is supposed to set `retry: false`.

Three components call `shiftsApi.current` independently — `AppTopbar.tsx:14`, `DashboardPage.tsx:134`, `ShiftsPage.tsx:55` — and none of them sets `retry`, so TanStack Query retries each on failure.

**Fix:** extract one shared hook, `lib/shifts.ts` → `useCurrentShift()`, with:

```ts
useQuery({
  queryKey: ["shift", "current"],
  queryFn: shiftsApi.current,
  retry: false,
  staleTime: 30_000,
})
```

Have all three consume it. One query key means one request, deduplicated. Better still: have `shiftsApi.current` catch the 404 and resolve to `null`, so "no open shift" stops being an error at all and the console stays clean.

---

# P1 — Spec requirements not met

## P1-1 · The crossed-swords emoji is still the logo

This was finding #3 in the original audit and the single most damaging detail on screen. You **created** `public/brand/logo-mark.svg`, `logo-full.svg`, `logo-mark-mono-light.svg` and `favicon.svg` — and then didn't use them.

`layouts/components/AppSidebar.tsx:78`:

```tsx
<div className="h-7 w-7 bg-teal-600 rounded flex items-center justify-center text-white text-sm font-bold shrink-0">
  ⚔️
</div>
```

**Fix:** render `logo-mark-mono-light.svg` at 28px. Drop the teal chip background — a real mark does not need to sit in a coloured box. Use `logo-full.svg` on the login page. Then grep the whole `src/` tree for any remaining emoji used as UI chrome (`components/ReceiptTemplateSelector.tsx` still has 🎯 ✨ 📋 📄 as template icons — replace those with rendered thumbnails or Lucide icons).

Confirm the SVGs are real vectors and not auto-traced raster; if they were traced from the JPG, stop and tell me, and I'll get the originals from the client.

## P1-2 · The fabricated dashboard deltas are still there

`pages/DashboardPage.tsx` lines 158, 186, 200:

```tsx
trend={{ value: 8,  isPositive: true }}   // Total Products
trend={{ value: 15, isPositive: true }}   // Revenue Today
trend={{ value: 3,  isPositive: true }}   // Transactions Today
```

Hardcoded. The screenshot shows "↑ 3% vs yesterday" against a transaction count of **4**, and "↑ 8% vs yesterday" against a *product catalogue size* — a number that has no meaningful daily trend at all.

**Fix, in order of preference:**

1. Compute the real delta. `/api/reports/daily/?date=` already exists — fetch yesterday alongside today and derive it. Applies to Revenue and Transactions only.
2. If a comparison isn't available, **render nothing**. `StatTile` should treat `trend` as optional and omit the row entirely.

Never show a trend on Total Products or Low Stock — those are stock levels, not flows.

## P1-3 · `Money` and `DateTime` were built and never adopted

This was the Phase 3 exit criterion and it is not met. Current usage:

```
paiseToRupees(...)   79 call sites across 8 page files
toLocale*(...)       12 call sites across 8 page files
```

The visible consequence: the Dashboard prints `Rs 80,262.00` while the Bills table prints `Rs. 147,911.40` — **with and without the period, on two screens of the same app.** The Products table prints `Rs. 14,000.00` where `Rs 14,000` would do.

**Fix:** replace every `paiseToRupees()` in `src/pages/` and `src/components/` with `<Money paise={...} />`, and every `toLocaleDateString`/`toLocaleString` with `<DateTime value={...} />`. Give `Money` a `decimals="auto"` mode that drops `.00` for whole rupees in table cells but always shows two decimals in totals and on receipts. Settle on **`Rs`** with no period, everywhere, including the PDF.

When you're done, this must return nothing:

```bash
grep -rn "paiseToRupees\|toLocaleString\|toLocaleDateString" frontend/src/pages frontend/src/components
```

(`paiseToRupees` stays in `lib/catalog.ts` as the implementation `Money` calls.)

## P1-4 · Toasts are wired into exactly one page

`grep -rl "useToast\|toast(" src/pages/` returns **only `CheckoutPage.tsx`**. The spec said every mutation.

Still silent: settings save, sale void, stock-in, product create/edit, CSV import, shift open, shift close, return processed, customer add. Wire each one with success and error variants. Settings in particular needs it — the current per-field save gives no confirmation at all.

## P1-5 · Native date inputs still render `mm/dd/yyyy`

Four remaining: `pages/BillsPage.tsx:294,305` and `pages/AuditPage.tsx:230,241`. Visible in both screenshots — a Quetta shop reading US date order.

**Fix:** build `components/ui/date-range-picker.tsx` with presets (Today · Yesterday · This week · This month · Custom) rendering `dd/mm/yyyy`, and replace all four. The Audit page's separate "Today / This month / Last 7 days" buttons then fold into the picker instead of sitting beside it.

## P1-6 · `DarkModeToggle` is built and mounted nowhere

`components/dark-mode-toggle.tsx` and `store/darkModeStore.ts` both exist. Grepping `main.tsx`, `App.tsx`, `layouts/` and `pages/` for either name returns **nothing**. The feature is unreachable.

**Fix:** mount the toggle in `AppTopbar`, next to the language toggle. Verify the `.dark` token block in `index.css` actually covers the new `chrome-*`, `success`, `warning`, `info` and `teal-*` tokens — the original `.dark` block predates them, so a dark-mode pass will show unstyled patches. Check every page in dark mode before calling this done.

## P1-7 · `/dev/kitchen-sink` is still routed

`router/index.tsx:19`. The spec said screenshot it for review, then delete the route. It ships to production as-is. Remove the route and `pages/DevKitchenSink.tsx`, or move it behind `import.meta.env.DEV`.

## P1-8 · Raw palette classes are back, in colours that aren't ours

The token layer is being bypassed again — the exact failure mode the original audit called out. Counts in `src/pages`, `src/layouts`, `src/components`:

```
emerald-600  14      slate-300  10      indigo-600   3
amber-600    12      slate-900   4      purple-500   2
emerald-500   7      slate-700   4      purple-700   1
emerald-50    5      slate-200   4      purple-900   1
emerald-200   5      slate-100   3
emerald-700   4      slate-50    2
```

`emerald`, `indigo` and `purple` are not in the Speed Tech palette at all. `emerald` is a *different green* from the brand green and the two sit side by side on the dashboard.

**Fix:** map each one to a token — `emerald-*` → `success` or `green-*`, `amber-*` → `warning`, `slate-*` → `n-*`, and delete `indigo`/`purple` outright. Then add a lint guard so this cannot regress:

```js
// .eslintrc — eslint-plugin-tailwindcss, or a simple no-restricted-syntax rule
"no-restricted-syntax": ["error", {
  selector: "Literal[value=/\\b(slate|gray|zinc|neutral|stone|emerald|cyan|sky|indigo|violet|purple|rose|pink|fuchsia|lime)-[0-9]{2,3}\\b/]",
  message: "Use a design token, not a raw Tailwind palette class. See docs/UI_UX_REVAMP_SPEC.md §3."
}]
```

Run `npm run lint` and fix every hit. **This rule is what makes the token layer actually hold.**

## P1-9 · `Payment.Method` doesn't include the methods you're storing

`apps/sales/models.py` declares `Method = cash | card | upi`. The Activity Log and Bills page both show `BANK_TRANSFER`. Django doesn't enforce choices at the DB layer, so it writes fine — but any serializer validation, admin form, or report grouping on choices will mis-handle it, and `upi` is an Indian rail that this shop doesn't use.

**Fix:** change to `cash | card | bank_transfer | mobile_wallet`, add a data migration mapping any existing `upi` rows, and update the checkout payment modal and the receipt renderer's `payment_method.capitalize()` (which would print "Bank_transfer" — use `get_method_display()`).

---

# P2 — Page-level work from Phase 4 that was skipped

Each of these was specified and is visibly absent from the screenshots.

## P2-1 · Products — zero stock looks identical to low stock

`MON-215-LED` at **0** and `BUL-2MP-OUT` at **1** both render the same amber "Low Stock" badge. Out-of-stock is a different operational state: you cannot sell it. Add a distinct `Out` badge using `destructive`, keep `Low` on `warning`, `OK` on `success`. Add the small stock-level bar (current vs threshold) the spec described, and fold the SKU column into the Name cell as a mono sub-line — it currently eats a full column.

## P2-2 · Audit — still five accent colours on one KPI row

The screenshot shows Transactions (blue), Revenue (blue), COGS (amber), Gross Profit (green), Gross Margin (emerald). Five accents means none of them signals anything.

Make Revenue and Gross Profit the teal headline pair; Transactions, COGS and Margin become neutral tiles. Then add the two charts the spec asked for — revenue vs COGS by day, and a payment-method donut — as inline SVG. Move the Download split-button into a `DropdownMenu`.

## P2-3 · Dashboard — quick actions, sparkline, low-stock panel

- Quick Actions are still four saturated gradient blocks including a large orange one that pulls the eye away from "New Sale". Spec: `bg-card border` with a teal icon chip, and only **New Sale** filled as primary. Add the F-key hints.
- The **revenue sparkline** under the revenue tile was not built.
- The **Low Stock panel** (5 most-depleted SKUs with an inline `+Stock` button) was not built. "8" is still a dead-end number.
- Recent Sales is still a hand-rolled list, not `DataTable`, and rows aren't clickable.

## P2-4 · Checkout — the flagship items

- The shortcut legend (`+/−`, `F9`, `F12`, `Esc`) still lives in the bottom of the right rail. Spec: move it into the **empty-cart state**, where it is actually needed and currently there's nothing but a grey cart icon.
- **Held carts** (park a sale, serve the next customer, resume) was not built. Every real counter needs this.
- The post-sale overlay works, but the change amount should be the largest thing on it — a cashier reads it across a counter. `Rs 738.00` is currently smaller than the total above it.
- Payment modal denomination quick-buttons (500 / 1000 / 5000 / exact) — verify these exist; I couldn't see the modal.

## P2-5 · Bills — detail slide-over, summary strip, void styling

- The eye icon at the end of each row should open a **slide-over** with items, payment, cashier, timeline and Print / PDF / Void / Return actions — not navigate away.
- No summary strip above the table (count · gross · discounts · net for the current filter).
- Pagination is still the text "Page 1 of 4" — use the `Pagination` primitive you built.
- Confirm voided bills get `line-through text-muted-foreground` + a danger badge; I have no voided rows to check.

## P2-6 · Returns, Customers, Activity, Settings

- **Returns:** the three-step stepper (Find bill → Select items → Confirm refund) was not built; it's still a single search box. The empty-state copy also wraps awkwardly — constrain it to ~48ch.
- **Customers:** no sortable columns, no segment filter, no detail slide-over. The Gender column is still there — move it into the detail panel; it's noise on a wholesale list.
- **Activity:** filter chips don't show counts; no user or date-range filter; no pagination.
- **Settings:** still a single long column with per-field saves. Missing: the two-column layout with sticky section nav, the **live receipt preview** (the highest-value item on that page), the logo upload, and the sticky "Unsaved changes — Save / Discard" bar.

## P2-7 · Phase 5 leftovers

- **`receipts/html.py` was never written.** The HTML print view (§7.6) doesn't exist, so there is no browser-print path and no live preview source for the Settings page.
- **`render_pdf_receipt` is not a thermal receipt.** It renders an A5 copy of the A4 document. A real 80mm PDF at 227pt width is still missing — see spec §7.5 for the layout.
- **`render_thermal_escpos` is orphaned.** `print_receipt_network()` builds plain text with `render_thermal_text()` and sends that, ignoring the ESC/POS renderer. So no double-height TOTAL, no logo raster, no QR, no cut command.
- Not built: **QR / barcode**, **VOID watermark** on voided sales, **ORIGINAL / DUPLICATE** marker, **`Page X of Y`** footer, **logo image** in the PDF header.
- `document.py` header cells use `styles['Heading4']` for the column labels. A `Paragraph` carries its own colour, so the `TEXTCOLOR → whitesmoke` in the `TableStyle` does **not** apply — you get dark heading text on the dark green header band, i.e. invisible. Define an explicit white `ParagraphStyle` for those six cells.
- `document.py` uses `('PADDING', (0,0), (-1,-1), 4)` in two `TableStyle` blocks. `PADDING` is not a ReportLab command — the valid ones are `LEFTPADDING` / `RIGHTPADDING` / `TOPPADDING` / `BOTTOMPADDING`. Remove or replace it.
- `render_pdf_receipt`'s docstring says *"For now, use A5 as 'thermal' equivalent - can adjust later."* Leaving a TODO in shipped code that the UI labels "Thermal Receipt" means the user gets something other than what the dropdown promised. Fix it or rename the dropdown option.

## P2-8 · Fonts declared but not shipped

`public/fonts/` exists and is **empty**, while `tailwind.config.js` asks for `"Inter var"` and `"JetBrains Mono"`. Every screenshot is rendering the Segoe UI fallback. Either drop the `.woff2` files in and add the `@font-face` blocks, or remove the font names from the config so the stack is honest. Do **not** add a Google Fonts `<link>` — this has to run offline.

## P2-9 · Small things

- The floating beach-ball emoji at the bottom-right of every screenshot: confirm it is a browser extension and not something in this app. Grep for it. If it's ours, remove it.
- `hooks/useTranslation.ts` and `lib/useTranslation.ts` both still exist. Consolidate to one.
- Verify `LanguageToggle` is imported from `components/LanguageToggle.tsx` and not still duplicated inline in `AppSidebar`.
- The topbar greeting reads "Good evening admin" at 10:49 pm on every page. Fine — but it takes prime real estate on all 11 screens. Consider showing it on the Dashboard only and using that space for the breadcrumb the spec specified (`Operations / Products`), which was not built.
- No `PageHeader` breadcrumb anywhere — check §4.3 of the spec.

---

# Order of work and prompts

Give these to the agent one at a time, and verify between each.

> **P0 —** Read `docs/PHASE_7_REMEDIATION.md` section P0. Fix the receipt PDF 500 completely: all eight faults in P0-1, in the order listed, starting with the logging fix in Fault 8 so you can see what you're doing. Then P0-2 (delete the two dead files), P0-3 (replace all five `alert()` calls with toasts), and P0-4 (single deduplicated `useCurrentShift` hook with `retry: false`). Add the pytest coverage described, generate the seven sample PDFs into `backend/tmp/receipt_samples/`, and report back with the sample list and the test output. Do not touch any page component in this pass.

> **P1 —** Read `docs/PHASE_7_REMEDIATION.md` section P1 and implement P1-1 through P1-9. P1-8 last, since the ESLint rule will surface work from the others. Run `npm run lint`, `npm run type-check` and `npm run build`, and paste the remaining lint output.

> **P2 —** Read `docs/PHASE_7_REMEDIATION.md` section P2. Work through P2-1 … P2-9, one commit each, in that order. Stop after each for review.

---

# Revised definition of done

Everything in `UI_UX_REVAMP_SPEC.md` §10, plus:

1. Both PDF templates render for all seven sample sales, including decimal quantities, a voided sale, and one over Rs 1,000,000.
2. Zero `alert()` calls in `src/`.
3. `grep -rn "paiseToRupees\|toLocale" frontend/src/pages frontend/src/components` returns nothing.
4. The ESLint raw-palette rule is in place and `npm run lint` is clean.
5. No emoji anywhere in application chrome.
6. Every mutation in every page produces a toast.
7. Dark mode is reachable from the topbar and every page is legible in it.
8. `receipts.py`, `receipt_templates.py` and the `/dev/kitchen-sink` route are gone.
9. No trend indicator is displayed unless it was computed from real data.
10. The server log carries a real traceback whenever receipt generation fails.

---

*Speed Tech Solutions POS · Phase 7 remediation · reviewed against commit `d5b0f47`*
