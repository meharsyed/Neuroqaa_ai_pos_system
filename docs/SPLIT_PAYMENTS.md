# Split payments — "Rs 2,000 now, the rest on khata"

Applied to the working tree. **192 backend tests pass (27 new); `tsc --noEmit` clean.**

---

## 1. What was actually wrong

`Payment` was a `OneToOneField` on `Sale`. One bill, one method, no amount of
its own — the tender was assumed to settle the whole total. So a bill was
*cash* or *card* or *khata*, and there was no way to say the customer put
Rs 2,000 down and took the rest on account.

That is the normal way this shop sells. It also made the credit-limit message
I shipped last time a lie: it told the cashier to "take a part payment" using
a till that could not take one.

## 2. The shape it has now

`Payment` is a plain ForeignKey with an `amount_paise` of its own, so a sale
carries a *list* of tenders. Two derived numbers hang off `Sale`:

```python
amount_paid_paise   # stored: the sum of every non-credit tender
credit_paise        # total_paise − amount_paid_paise: what went on khata
```

The khata is never a tender you choose. It is **whatever the tenders leave
unpaid** — so the arithmetic cannot disagree with itself, and passing
`credit` in a tender list is rejected rather than quietly double-counted.

`create_sale` now takes an optional `tenders=[{method, amount_paise,
amount_tendered_paise}]`. The old `payment_method` / `amount_tendered_paise`
call still works exactly as before and is what every existing caller uses.

### Two migrations

| Migration | What it does |
|---|---|
| `sales/0008_…` | OneToOne → FK, adds `Payment.amount_paise` and `Sale.amount_paid_paise` |
| `sales/0009_backfill_payment_amounts` | Every existing payment settled its whole bill, so `amount_paise = sale.total_paise`; sales get `amount_paid_paise` from their non-credit tender |

Old data comes out with exactly the meaning it had before.

---

## 3. Three bugs this exposed, all of which lose money

These were not in the plan. They only became visible once a bill could be
part-paid, and each one is checked by a test that fails if the fix is undone
(I reverted each in turn to confirm).

**Voiding a split sale handed the customer free credit.** `void_sale`
reversed `sale.total_paise` off the ledger. On a Rs 10,000 bill with Rs 2,000
paid in cash, only Rs 8,000 was ever owed — reversing Rs 10,000 left the
customer at **minus Rs 2,000**, i.e. Rs 2,000 of spendable credit conjured
from a refund they also got back in cash. It now reverses `credit_paise`.
Same fix in `create_return`.

**The till count expected cash that was never taken.** Shift reconciliation
summed the *totals* of sales whose method was cash. A Rs 10,000 bill settled
with Rs 2,000 cash and Rs 3,000 card would have expected Rs 10,000 in the
drawer and reported a Rs 8,000 shortfall every single evening. It now sums
the cash *tenders*.

**Reports attributed whole bills to one method.** `payment_breakdown`
grouped sales by `payment__method` and summed `total_paise`. It now sums
`Payment.amount_paise` grouped by method, so a split bill contributes its
Rs 2,000 to cash and its Rs 8,000 to khata, and the columns add up to
revenue. The per-method *counts* can now overlap — one bill appears under
each tender it used — so the Audit page says "3 bills" rather than
"3 transactions".

---

## 4. The till

The four method buttons still work the way they did: one tap settles the
whole bill that way. What is new is the **Paying now** block underneath.

```
Payment Method   [Cash] [Card] [Bank] [Khata]

Paying now
  [Cash ▾]  Rs [ 2,000.00 ]        change Rs 500.00
  + Add another method

Paid now                    Rs 2,000.00
Goes on khata               Rs 8,000.00
Customer                       Split Ali
Currently owes              Rs 4,000.00
Will owe after this        Rs 12,000.00

            [ Pay part & put rest on khata ]
```

Type less than the total and the remainder is put on the khata — no mode to
switch into, no checkbox to find. The button relabels itself so nobody
completes a part payment by accident.

Three details worth knowing:

- **A cash box is what the customer handed over, not what it settles.** Hand
  over Rs 500 for a Rs 350 bill and Rs 350 settles it, Rs 150 comes back as
  change. Type Rs 2,000 against a Rs 10,000 bill and Rs 2,000 settles it.
  One box does both, which is how a till actually works.
- **Card and bank give no change.** Overpaying on those is refused with an
  explanation rather than silently pocketed.
- **No customer, and a remainder** → the sale is blocked with "Nobody to bill
  the rest to". Previously this whole state was unreachable; the server
  refuses it too.

The credit-limit check now applies to the **remainder**, so a part payment is
a real way through it. The refusal message says how much more to collect:

> Only Rs 5,000.00 of credit is left — collect at least Rs 3,000.00 more now,
> or ask an owner to raise the limit.

---

## 5. Everywhere a bill is shown

| Surface | What changed |
|---|---|
| A4/A5 invoice | PAYMENT reads `Cash + Khata`; one Paid line per tender, then Change, then BALANCE DUE (Khata) |
| 80 mm thermal | Same, in the totals block; the bold rule stays on TOTAL |
| HTML / public link | Same; the WhatsApp message adds `Paid now` and `On khata` |
| Checkout success | Lists every tender and the khata amount |
| Bills | Expanded row lists each tender; the method column reads `cash + credit` |
| Khata detail (eye icon) | A credit purchase shows the amount that went **on the khata**, with "paid Rs 2,000 at the till" underneath — the bill total would overstate the debt |

The API keeps `sale.payment` — the largest non-credit tender — so nothing
that read a single method broke. It gains `payments[]`, `amount_paid_paise`
and `credit_paise`.

---

## 6. Run it

```powershell
cd "D:\Neuroqaa Stuff\POS System\pos-system-GT\backend"
.\venv311\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
python manage.py migrate        # 0008 + 0009
pytest -q                       # expect 192 passed
python manage.py runserver
```

```powershell
cd ..\frontend ; npm run dev
```

### Test checklist

1. Cart worth Rs 10,000, attach a khata customer, F12. Type **2000** in the
   cash box. It should read Paid now Rs 2,000 / Goes on khata Rs 8,000, and
   the button should say *Pay part & put rest on khata*.
2. Complete it. The success screen lists both lines; the A4 and thermal
   receipts show `Paid (Cash) 2,000` and `BALANCE DUE (Khata) 8,000`.
3. Khata → eye icon on that customer → the purchase shows **8,000**, not
   10,000, with "paid Rs 2,000.00 at the till" beneath it. Balance +8,000.
4. **Void that sale** (Bills → Void). The balance must go back to what it was
   — not Rs 2,000 below it.
5. Remove the customer and try a part payment → blocked, "Nobody to bill the
   rest to".
6. Set a Rs 5,000 credit limit, try the same Rs 10,000 bill on khata → refused
   with the amount to collect. Enter that amount as cash → it completes.
7. Two tenders: **+ Add another method**, Rs 4,000 cash + Rs 6,000 card. No
   khata line anywhere, and the customer's balance is untouched.
8. Open a shift, do step 7, then Shifts → reconcile. Expected cash must count
   the **Rs 4,000**, not Rs 10,000.
9. Dashboard / Audit → the payment breakdown splits that bill across cash and
   card and the money sums to the day's revenue.

---

## 7. Verification

- **192 backend tests**, 27 new in `apps/sales/tests/test_split_payments.py`.
- **Mutation-tested three times.** Removing the overpayment guard failed 1
  test; reverting void/return to `total_paise` failed 2 (one asserting the
  customer would land at −Rs 2,000); reverting the drawer count to sale
  totals failed 1. All restored.
- A split invoice and thermal receipt were rendered and **looked at**, not
  just asserted on — the green TOTAL bar stays on TOTAL with the extra rows
  present.
- `tsc --noEmit` clean; ESLint clean on the changed files.

---

## 8. Still open

1. **The ESLint palette rule.** `PaymentModal` is on tokens again (its
   `amber-*` / `orange-*` classes went back to `text-warning`), but without
   the rule this keeps recurring — it is the third time.
2. **Serials at stock-in.** Captured only at the point of sale, so you know
   what left the building but not what is in it.
3. **Recording a later payment against one specific bill.** Payments go
   against the customer's balance as a whole; you cannot yet say "this
   Rs 3,000 clears SALE-20260905-00041". The ledger has the `sale` column to
   support it.
4. **`Claude outputs/`** — a folder of sample PDFs in the repo root. Safe to
   delete.

---

*Applied and verified against the working tree · 192 backend tests · tsc clean · receipts rendered and inspected*
