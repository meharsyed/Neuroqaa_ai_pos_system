# Speed Tech POS — Phase 9: Khata review + demo-day triage

**Audience:** the coding agent working in this repository.
**Context:** client demo is today. §1 is what must be true before the demo. Everything after is post-demo.

> **Already done for you — do not redo.** `receipts/document.py` and `receipts/thermal_pdf.py` have been **replaced with working, render-verified versions** and committed to the repo. Both were rendered to PDF and visually inspected before delivery: A4, A5, with/without item discounts, 10-item overflow, voided, and 80 mm thermal all lay out correctly. Read §0 so you understand *why* they are written the way they are, and don't reintroduce the bugs.

---

## 0. The receipt problems — root causes, so they stay fixed

### 0.1 Why the A4 invoice bled off both page edges

`_build_header()` had:

```python
colWidths=[logo_w, usable_w * 0.45, usable_w * 0.55]
```

That is `doc.width + logo_w` — 22 mm wider than the frame. **ReportLab's default `hAlign` for a Table is `CENTER`**, so an over-wide table isn't pushed off the right edge, it's centred and overflows *equally on both sides*, then clipped by the page. That is the exact signature you saw: `2MP…` losing its `2`, `Serials:` losing its `S`, and `AMOUNT` running off the right.

Three rules now enforced throughout both files:

1. **Every `Table` gets `hAlign="LEFT"`** (or `"RIGHT"` for the totals block, which is intentional and sized to fit).
2. **`colWidths` must sum to exactly the available width.** Ratios are multiplied by `doc.width` and the last column absorbs the floating-point remainder: `widths[-1] = W - sum(widths[:-1])`.
3. **No hardcoded `mm` widths for anything that spans the page.**

### 0.2 Why the totals values were missing entirely

Same cause, one level down. The totals table was `[70mm, 30mm]` = 100 mm, nested inside a cell that was only half the page. The label column fit; the *value* column was pushed outside the page and clipped. Labels rendered, numbers vanished.

It is now `hAlign="RIGHT"` inside a cell sized `tot_w + 10mm`, where `tot_w = W * 0.42`. It cannot exceed its container.

### 0.3 Why serials printed twice

`document.py` had the "append serials row" block **duplicated verbatim** — lines 252-278 and again 280-296. Both ran.

Worse, the second copy always appended **6 cells** while `col_widths` had **5** when no line had a discount. A ragged row makes ReportLab invent an extra column, which is a *second* reason the table was wider than the page.

The new file removes the whole category of bug: **serials render inside the DESCRIPTION cell**, as extra `Paragraph`s in that cell's flowable list. A row is now structurally incapable of going ragged, and there is an `assert len(row) == ncols` as a tripwire.

### 0.4 Why the shop name printed twice on the thermal slip

`thermal_pdf.py` `_build_story()`:

```python
logo = _get_logo_image(...)
if logo: story.append(logo)
else:    story.append(Paragraph(ctx.shop_name, ...))   # ← fallback prints the name
story.append(Spacer(...))
story.append(Paragraph(ctx.shop_name, ...))            # ← and this prints it again
```

With no logo asset on disk, both fire. Now the logo block appends **only** the logo; the name is printed exactly once, by the block below it.

### 0.5 Other things fixed in the same pass

| | |
|---|---|
| **DISC column** | Now appears only when at least one line actually has a discount — exactly as you asked. Two ratio sets, chosen by `any(i.discount_paise > 0 …)`. |
| **TOTAL bar** | Targeted by a **computed row index**, never `(0, -1)`. That is why the green bar was landing on *Change* — `-1` is the last row, and Change is last when change is due. |
| **Customer signature** | Removed from the A4 entirely, per your request. |
| **Header dead space** | Label and value now sit on one right-aligned line (`No.  SALE-…`) instead of two table columns with a gap between them. |
| **Footer** | Drawn on the canvas as a pale teal band pinned to the page bottom, with the shop tagline left and `Page N` right — on every page. |
| **Thermal totals** | `TOTAL` now has a rule above and below and is 10.5 pt bold; the rest are 8 pt. |
| **Thermal items** | Now show `qty × rate` and serial numbers, which were missing. |
| **Thermal roll length** | Trailing padding cut from 30 mm to 8 mm — you were feeding 3 cm of blank paper per sale. |
| **VOID** | Rotated watermark drawn on canvas for voided sales. |
| **Amount in words / QR** | Both present on A4. |

### 0.6 Two things you must still do for the receipts

1. **Drop in the logo files.** Both renderers look for, and silently skip:
   - `backend/apps/sales/receipts/assets/logo-invoice.png` (A4/A5, ~600 px, transparent)
   - `backend/apps/sales/receipts/assets/logo-thermal.png` (thermal, **1-bit black-and-white**, ~380 px)

   Create the `assets/` directory. Until then both fall back cleanly to text.

2. **Port the same fixes into `receipts/html.py`.** It was written before this pass and has not been reviewed. Check it against §0.1–§0.3: conditional DISC column, serials inside the description cell, TOTAL emphasised, no signature block, single shop name.

---

# 1. Demo-day triage — do these before showing the client

Ordered by how likely the client is to hit it on screen. Nothing here is a refactor; each is small.

### D1 · Scanning the same serial twice kills the sale — 500, cart lost

`CheckoutPage.tsx:221-233` (`addSerialToItem`) does not dedupe. `services.py:166` hits `unique_together` on `SaleItemSerial` → `IntegrityError`, which `sales/views.py:96` does not catch (it only catches `ValueError`) → 500, transaction rolls back, **the cashier loses the entire cart** with a generic error.

This is the single most likely thing to break live: serials are the new feature, so it's what you'll demo, and scanning a duplicate is the natural mistake.

**Fix:** dedupe client-side in `addSerialToItem` (reject with a toast if the serial is already on the line), and catch `IntegrityError` in `views.py`, returning a 400 with a readable message.

### D2 · Exporting a report crashes if any credit sale is in range

`reports.py:29-43` groups by `payment__method`. For credit sales that value is `None` (see D3), and `reports.py:419` then calls `method.upper()` → `AttributeError: 'NoneType' object has no attribute 'upper'`.

Audit Reports → Download → PDF is a natural demo click, and it will 500 the moment a khata sale exists in the period.

**Fix:** `(method or "credit").upper()` at `reports.py:419` as the immediate guard; D3 is the real fix.

### D3 · A khata sale prints as a CASH sale

`services.py:186-192` creates the credit `Payment` with **`sale=None`**:

```python
Payment.objects.create(sale=None, method=payment_method, ...)
```

`Payment.sale` was made nullable in migration `0006`. Consequences, all confirmed:

- `sale.payment` raises `ObjectDoesNotExist`, so `context.py:146-150` falls through and the receipt prints `payment_method="cash"`, `tendered=0`. **A credit sale hands the customer a receipt that says they paid cash.**
- Every `payment__method="credit"` filter matches zero rows — `customers/views.py:122-124` and `serializers.py:43-45` — so the **entire aging report is dead**: every customer shows "0 days overdue" and the URGENT badge never renders (`KhataPage.tsx:316,331`).
- The orphan row has no FK back to the sale, so it isn't an audit trail either.
- `Payment.__str__` (`models.py:143`) does `self.sale.sale_number` → `AttributeError` in admin.

**Fix:** pass `sale=sale`. One argument. It unblocks D2, the aging report, and the receipt.

### D4 · A credit sale with no customer silently charges nobody

`services.py:183` guards with `if sale.customer:`. `CreateSaleSerializer` (`serializers.py:109-115`) accepts `payment_method="credit"` with no `customer_id`. The sale completes, stock is deducted, revenue is booked — and no one is billed, with no error.

Compounded by `CheckoutPage.tsx:377-379`, which swallows customer-creation failures and proceeds without a customer.

**Fix:** raise a `ValidationError` in the serializer when `payment_method == "credit"` and `customer_id` is absent.

### D5 · The khata screen shows "All customers are paid up!" when the API fails

`KhataPage.tsx:26-30` destructures only `data` and `isLoading`. On any error `report` is `undefined` and line 86 renders the `EmptyState`: **"No outstanding balances — All customers are paid up!"**

For a receivables screen that is the worst possible failure mode — it reports the opposite of the truth. Given D2/B10 can make this endpoint fail, it could happen in front of the client.

**Fix:** destructure `isError`, render an error state with a Retry.

### D6 · The khata report is 2000+ queries and unpaginated

`customers/views.py:113-147` loops all customers with a balance; `CustomerSerializer` fires 4+ queries each (`serializers.py:31,34,43`) with no `select_related` or annotation, and no pagination — and `KhataPage.tsx:29` refetches every 30 s.

Fine with 2 demo customers; it will visibly hang with real data. Annotate and paginate.

**Demo-day set: D1, D2, D3, D4, D5.** Roughly an hour, all small, all things a client can trip over live.

---

# 2. Data integrity — the khata design needs a ledger

Post-demo, but do it before real money goes through this.

### 2.1 There is no ledger, so a wrong balance can never be found or repaired

`PaymentReceived` (`customers/models.py:33-47`) records only payments **in**. Credit sales — the debits — exist nowhere as rows; they only mutate the denormalised `Customer.outstanding_paise` (`models.py:16`). There is no `sum(entries) == balance` invariant that can ever be checked, no audit trail, and no way to repair drift.

Every defect below is downstream of this one. Fix it structurally:

```python
class CreditLedgerEntry(models.Model):          # append-only
    customer      = FK(Customer, related_name="ledger")
    sale          = FK(Sale, null=True, blank=True)     # debit source
    payment       = FK(PaymentReceived, null=True, blank=True)  # credit source
    kind          = CharField(choices=["sale", "payment", "return", "void", "adjustment"])
    delta_paise   = BigIntegerField()            # +ve owed, -ve paid
    balance_after_paise = BigIntegerField()
    note          = TextField(blank=True)
    created_by    = FK(User, null=True)
    created_at    = DateTimeField(auto_now_add=True)
```

Block `save()` on an existing pk and `delete()` outright, exactly as `StockMovement` does (`PROJECT_CONTEXT.md` §6.2). Then `Customer.outstanding_paise` becomes a cache you can rebuild with a management command.

### 2.2 Lost updates — the balance is a read-modify-write with no lock

`services.py:183-185`:

```python
sale.customer.outstanding_paise += total_paise
sale.customer.save(update_fields=["outstanding_paise"])
```

Inside `transaction.atomic()`, but the customer row is never locked — only `Inventory` is (`services.py:86`). Two concurrent credit sales both read the old balance and one charge disappears. Same bug in `customers/views.py:96-97`.

**Fix:** `select_for_update()` on the customer, or `F("outstanding_paise") + total_paise` at minimum.

### 2.3 Voids and returns never reverse the balance

`void_sale` (`services.py:383-411`) restores stock and flips status but never touches `outstanding_paise`. `create_return` (`:282-380`) likewise, and never links the return to the original sale's customer (`:336-346`).

**Void a Rs 50,000 khata sale and the customer still owes Rs 50,000, forever, with no sale to point at.**

### 2.4 Overpayment silently forges a write-off

`customers/views.py:88-97` clamps with `max(0, balance - amount)` while writing a `PaymentReceived` for the full amount. `CreatePaymentReceivedSerializer` (`serializers.py:70-74`) only enforces `min_value=1`. Post Rs 999,999.99 against a Rs 500 balance and the ledger and the balance permanently disagree. The only guard is client-side (`KhataPage.tsx:56`).

**Fix:** validate server-side that `amount_paise <= outstanding_paise`, or record the excess explicitly as advance credit.

### 2.5 Credit write-offs are not role-restricted

`customers/views.py:22` — `permission_classes = [IsAuthenticated]`, inherited by `record_payment` (`:61`) and `khata_report` (`:107`). **A cashier can zero out any customer's khata.** The route isn't role-gated on the frontend either (`router/index.tsx:38`, `AppSidebar.tsx:39`).

Compare `SaleViewSet.void` (`sales/views.py:112`), which does check. There is no permission class anywhere in `apps/accounts` — every role check in this codebase is an ad-hoc inline `if`. Write a real `IsOwnerOrManager` permission class and apply it to void, settings, and all credit writes.

### 2.6 No credit limit exists

No `credit_limit_paise` on `Customer`, no check in `create_sale`. Any customer can take on unlimited debt. `PaymentModal.tsx:129-145` shows "After This Sale" but never blocks.

### 2.7 `PaymentReceived` is invisible and mutable

No `editable=False`, no immutability guard, not in `customers/admin.py`, and **no list endpoint** — so after recording a payment, nobody can ever see what was paid, when, or by whom. Add a per-customer khata detail view with the ledger.

### 2.8 Partial payment is impossible

`Payment` is a `OneToOneField` to `Sale` (`models.py:137`), so a sale has one method. `PaymentModal.tsx:195` sends the full total for credit. "Pay 2000 now, rest on account" — the normal khata pattern in this market — cannot be expressed.

**Fix:** make `Payment` a FK, add `Sale.amount_paid_paise`, and invariant-check `sum(payments) == amount_paid`.

---

# 3. Serial numbers — correctness

- **B3 · Serial count is never validated against line quantity.** `serializers.py:94-99` takes a free-length list; `services.py:162-170` loops blindly. Sell qty 1 with 5 serials, or qty 10 with 0.
- **B4 · Reducing qty keeps the serials.** `CheckoutPage.tsx:157-179` and `:181-199` carry `serials` through unchanged, so a qty-2 line dropped to 1 still submits 2 serials — accepted because of B3.
- **B6 · Serials are not globally unique.** `models.py:118-123` scopes uniqueness to `(sale_item, serial)`, so **the same physical camera can be sold on unlimited separate invoices.** For warranty lookup — the entire point — this must be unique across all sales. Add a `UniqueConstraint` on `serial` and a friendly duplicate error.
- **B8 · Serials were missing from `thermal_pdf.py` and `html.py`.** Now fixed in `thermal_pdf.py`; **`html.py` still needs it.** The `show_serial_numbers_on_receipt` setting (`SettingsPage.tsx:239`) has no effect there.
- Serials exist only at point of sale — never at stock-in. Long-term, capture them on the `StockMovement` so you know what's in the building, not just what left it.

---

# 4. Frontend polish on the new screens

- **C1 · Raw palette classes are back on the new pages.** `KhataPage.tsx` uses `text-red-500` `:135`, `text-red-600` `:138`, `bg-green-50`/`text-green-600` `:147-148`, `bg-yellow-50`/`text-yellow-600` `:169-170`, `bg-orange-50`/`text-orange-600` `:191-192`, `bg-red-50` `:213-214`. `PaymentModal.tsx:130-144` is a whole `border-blue-200 bg-blue-50 text-blue-700` block; also `text-amber-600` `:78,:87`, `text-orange-600` `:93`. Serial chips in `BillsPage.tsx:149-151` and `CheckoutPage.tsx:1028-1079` are the same. **None have dark-mode variants.** Map them to `success` / `warning` / `destructive` / `info` tokens.
  This is the third phase running where new pages arrive with raw palette classes. **Add the ESLint rule from `PHASE_8` §5.1** — without it this recurs every time.
- **C2 · `Money` used inconsistently.** `KhataPage` uses it correctly (`:119,240,329`) but `PaymentModal` bypasses it with `paiseToRupees()` for the totals (`:75,80,89,95,100,166,174`), so two money formats appear in one dialog. `DateTime` is used nowhere in khata — no "last payment", no "oldest invoice", despite `received_date` existing.
- **C3 · Hand-rolled modal.** `KhataPage.tsx:233-302` builds a fixed-overlay dialog by hand instead of `components/ui/dialog.tsx` — no focus trap, no Escape, no scroll lock, no `role="dialog"`, no autofocus on the amount field.
- **C7 · `bank_transfer` is unreachable from the POS.** It exists in `Payment.Method` (`models.py:134`) but is missing from `PaymentModal.tsx:22-27`.
- **C8 · Zero test coverage** for khata, `outstanding_paise`, credit, or `SaleItemSerial`.

---

# 5. Prompts

> **Demo now.** Read `docs/PHASE_9_KHATA_AND_DEMO_FIXES.md` §1. Implement D1–D5 only. Do not refactor anything else, do not touch `receipts/document.py` or `receipts/thermal_pdf.py` — those are already fixed and verified. Report what you changed, file by file.

> **9A — receipts finish.** Read §0.6. Create `backend/apps/sales/receipts/assets/`, wire the two logo files, then bring `receipts/html.py` in line with §0.1–§0.3 (conditional DISC column, serials inside the description cell, TOTAL emphasised by computed index, no signature block, shop name printed once). Then write `apps/sales/tests/test_receipts.py` covering all three renderers for: 1 item, 25 items, decimal qty, item discount, bill discount, serials, voided, no customer, no payment, and a credit sale.

> **9B — khata integrity.** Read §2. Implement in order: 2.1 (`CreditLedgerEntry`, append-only, with a rebuild management command), 2.2 (locking), 2.3 (reverse on void and return), 2.4 (server-side amount validation), 2.5 (`IsOwnerOrManager` permission class applied to void, settings and credit writes), 2.6 (credit limit), 2.7 (ledger endpoint + customer khata detail view). One commit each, stop for review after 2.1.

> **9C — serials + polish.** Read §3 and §4. Serial/qty validation, frontend trim on qty change, global uniqueness, `html.py` serials. Then add the ESLint palette rule and clear every hit on the new pages.

---

# 6. Definition of done

1. `document.py` and `thermal_pdf.py` contain no hardcoded page-spanning `mm` widths, and every `Table` sets `hAlign` explicitly. *(Already true — keep it true.)*
2. A credit sale's receipt says the sale was on credit and shows the customer's new balance.
3. `sum(CreditLedgerEntry.delta_paise) == Customer.outstanding_paise` for every customer, verified by a management command.
4. Voiding or returning a credit sale reverses the balance.
5. Only an owner or manager can record a payment or write off a balance.
6. A serial number cannot be sold twice, and serial count matches line quantity.
7. Scanning a duplicate serial produces a toast, never a 500.
8. Report export succeeds with credit sales in range.
9. The khata screen distinguishes "no debtors" from "the request failed".
10. `npm run lint` is clean with the palette rule enabled.

---

*Speed Tech Solutions POS · Phase 9 · receipts verified by render; khata reviewed against the working tree*
