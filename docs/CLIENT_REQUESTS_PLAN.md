# The client's six requests — what I built, and how I'd build the rest

From the meeting on 05 Sep 2026. **Item 1 (installation charges) is done and
in the working tree: 218 backend tests pass, `tsc --noEmit` clean.** The other
five are designed below with the decisions that matter called out, so you can
sign them off before I write the code.

---

## Before anything else: going cloud changes the risk

He picked the hosted option. That is the right call commercially, and it moves
four findings from my audit out of "worth doing" and into "must be done before
the first real bill is written":

| From `ROADMAP_AUDIT.md` | Why it changes |
|---|---|
| **0.1** — a cashier can zero a khata with one PATCH | On a LAN, whoever could reach it was standing in the shop. On the internet, it is anyone with a staff password. |
| **0.2** — no permissions on the catalog app | Same. Repricing stock from a phone, from anywhere. |
| **1.4** — no rate limiting on login | A LAN-only login page is not brute-forced. A public one is, continuously, by bots, within days of the DNS record appearing. |
| **0.4** — no backups | You have now *sold* backups. There is currently no code that makes one. |

That is item 7 on his list and items 0.1/0.2/0.4 on mine converging on the same
work, which is convenient: **do the roles-and-users piece properly and most of
this closes together.**

Also worth pricing honestly into the 80k: HTTPS and a real domain, a managed
Postgres or at least a backed-up volume, and somewhere for the receipt-share
links to live (`public_base_url` finally becomes a real setting rather than a
LAN address).

---

## 1 & 2. Installation charges — **built**

### The problem with the obvious approach

The obvious thing is to add the installation amount to `total_paise`. That
would have been wrong in a way that is hard to spot and expensive to unwind:
`total_paise` is summed by the daily summary, the audit P&L, gross margin, the
khata, the dashboard and the CSV exports. Fold labour into it and every one of
those overstates the business — quietly, and in a way that looks plausible.
By the time anyone notices, months of reports are wrong.

So `total_paise` keeps its exact meaning. Two new fields sit beside it:

```
subtotal_paise      goods, before discount
discount_paise
tax_paise
total_paise         = subtotal − discount + tax     ← REVENUE. Unchanged.
installation_paise  ← NEW. Labour. Never revenue.
amount_due_paise    = total_paise + installation_paise   (a property, not stored)
```

Because `total_paise` did not move, **every existing report stayed correct with
no changes at all** — which is why 192 tests passed before I had written a
single line of reporting code.

### What changed, and why

- **Tax does not apply to installation.** Labour is not goods; it is added
  after tax. If Speed Tech is FBR-registered and their accountant says
  otherwise, this is a one-line change — but the default should be the
  conservative one.
- **The customer pays it, so the tenders and the khata work against
  `amount_due_paise`.** Change from cash is calculated against the amount due,
  not the goods total. There is a test for a Rs 16,000 note against a Rs 15,000
  bill returning Rs 1,000, not Rs 6,000.
- **On credit it becomes two ledger entries**, `sale` and `installation`, as
  you asked. The khata balance is one number, but the debt is now tellable
  apart — goods owed to the shop, labour owed onward to a technician.
- **Money at the till settles the labour first.** Rs 5,000 down on a Rs 15,000
  bill clears the technician in full and leaves the goods outstanding. The
  reasoning: the technician did the work and is an outside party, so making him
  wait on the customer's credit is the owner's risk to take, not something the
  software should impose silently. If he wants goods-first instead it is two
  lines in `Sale.installation_unpaid_paise` — the comment says which.
- **Labour on credit counts against the credit limit.** It is money owed.
- **A void clears the labour debt; a return does not.** The camera comes back;
  the technician's day on a ladder does not. Only a full cancellation of the
  bill cancels the labour.

### The bug I found while testing this

The amount in words on the invoice was rendering `total_paise`. With
installation on the bill it said *"Eleven thousand seven hundred rupees only"*
under a box reading **Rs 16,700.00** — a legal document contradicting itself.
Fixed, and there is a test asserting the words match the payable figure.

### What he can now see

`daily_summary` and the audit report both gained an `installation` block:

```json
"installation": {
  "bill_count": 3,
  "charged_paise": 1500000,      // Rs 15,000 of labour billed
  "collected_paise": 1200000,    // Rs 12,000 already in hand
  "outstanding_paise": 300000    // Rs 3,000 customers still owe
}
```

`collected_paise` is what he owes his technicians right now. `outstanding_paise`
is what he cannot pay out yet because the customer has not paid him.

**Honest limitation:** once a khata payment is made later against the balance
as a whole, the system does not re-split it into goods and labour. So
"collected" counts money taken at the till only. Fixing that properly is item
2.3 in the audit (per-bill payment allocation) and is the natural follow-up.

### On the bill

```
Subtotal              10,000.00
Tax                    1,700.00
Goods total           11,700.00
Installation / labour  5,000.00
  Imran — 3rd floor mounting
AMOUNT DUE        Rs 16,700.00     ← the emphasised bar moves here
Paid (Cash)            7,000.00
BALANCE DUE (Khata)    9,700.00
```

With no installation, the receipt is byte-for-byte what it was. I rendered both
the A4 invoice and the 80 mm slip and looked at them.

### At the till

An **Installation / labour** row under the tax line, with an optional note
field that appears once an amount is entered — "Imran — 3rd floor mounting"
prints on the bill so the owner knows who to pay. The cart panel shows *Goods
total* above *Amount due* only when there is labour on the bill.

### To test it

1. Cart worth Rs 10,000, enter **5000** in Installation, note "Imran".
   Amount due Rs 15,000, goods total shown above it.
2. Complete it in cash → the A4 and thermal receipts both show the split, and
   the words match Rs 15,000.
3. Dashboard / Audit → revenue is Rs 10,000, and the installation block shows
   Rs 5,000 charged and collected.
4. Same bill on khata for a customer → balance goes up by Rs 15,000, and the
   khata detail shows two entries.
5. Void it → balance returns to zero. Return the goods instead → Rs 5,000 of
   labour is still owed.

---

## 4. Warranty disclaimer on the bill

### Where it should live

Settings, as four keys — not hardcoded, because he will want to reword it after
the first argument with a customer:

| Key | Default |
|---|---|
| `warranty_note_enabled` | `true` |
| `warranty_note_language` | `en` · `ur` · `both` |
| `warranty_note_en` | *"Warranty is void if the device is damaged by electrical spark, power surge, lightning, water ingress, physical impact, or unauthorised repair."* |
| `warranty_note_ur` | the same, in Urdu |

Editable by owner/manager only — it is a legal statement, not a preference.

On the A4 invoice it belongs in a bordered **WARRANTY TERMS** block below the
totals, in small type. On the thermal slip, small centred text above the
footer. It should be visually distinct from "Goods returnable within 7 days",
which is a different promise.

### The Urdu problem, plainly

You picked A4/A5 PDF and the web receipt, which is the right scope. Here is why
the thermal slip was worth excluding:

- **The web receipt is free.** The browser shapes and lays out Urdu correctly
  with no work from us.
- **The PDF needs three things**: a bundled Urdu font (Noto Naskh Arabic —
  about 200 KB; Nastaliq is the more beautiful Urdu style but ReportLab cannot
  shape it properly, so Naskh is the honest choice), plus `arabic-reshaper` and
  `python-bidi` to join the letters and reverse the run order. Without those
  two libraries you get disconnected letters in the wrong order — worse than
  nothing, because it looks like contempt.
- **The 80 mm thermal slip cannot do it at all.** Printing goes out as ESC/POS
  *text* on a printer whose character ROM has no Urdu. The only way is to
  render the slip as a bitmap and send it in graphics mode — slower to print,
  and dependent on the printer supporting it. Not worth it for a disclaimer.

So: **Urdu on the A4 invoice and the shared link; English on the till slip.**
Which is the right split anyway, because a warranty argument is had over the
A4 invoice, not the thermal receipt.

**Effort:** half a day for the setting and English; one more day for Urdu done
properly with the font bundled and rendering verified by eye.

---

## 5. Quotations

### Not a Sale with a flag

A quotation must not touch stock, must not appear in revenue, must not take a
`SALE-` number, and must be able to contain items that are not in the catalogue
at all. Bolting a status onto `Sale` would mean auditing every query in the
system for "and not a quotation" — the same trap as folding installation into
`total_paise`. Its own model:

```
Quotation          QT-20260906-00001, customer, business profile, validity,
                   status (draft / sent / accepted / expired), notes,
                   discount, tax, installation
QuotationItem      product FK (nullable!) OR free-text name + description,
                   qty, unit price entered by hand, line discount
```

The nullable product FK is the point: a quotation can list *"Cat-6 cable,
90m, supplied and laid — Rs 18,000"* with no such product in stock. When the
line does reference a real product, it pre-fills the price and keeps the SKU on
the printed quotation, which looks more professional.

### The shop identity — profiles, not free text

You chose named business profiles, and I think that is right. Free-typing the
shop name on every quotation means retyping an address wrong on a tender
document, and no record of which identity a quotation went out under.

So: a **Business profiles** section in Settings — name, address, phone, email,
tax number, logo — with one marked default. The quotation page has a dropdown.
The PDF renders that profile's letterhead.

This is also reusable: the same profiles can later drive the invoice
letterhead, which is probably where this is heading anyway.

### The feature that makes it worth building

**Convert to sale.** An accepted quotation pre-fills the checkout cart —
catalogue lines by SKU, off-catalogue lines as manual entries — and the sale
records which quotation it came from. Without that, a quotation tool is a
worse version of Word. With it, quoting becomes the front of the sales
pipeline, and he can be shown a conversion rate.

Only catalogue lines can deduct stock, so off-catalogue lines convert as
manual entries and I'd flag them at the point of conversion.

### Also worth having

- **Validity** — "Valid for 15 days", printed. Stops a customer returning in
  March with a January price.
- **Revisions** — QT-…-00001 **rev 2** rather than a new number, so a
  negotiation is one thread.
- A quotation is a **quotation**, not a tax invoice: the header must say so,
  and it must not carry an invoice number.

**Effort:** two to three days for model, API, page and PDF; half a day more
for convert-to-sale.

---

## 6. Editable tax

You chose open at the till. Fine — but three things go with it.

**First, a real bug this exposes.** The server currently accepts whatever
`tax_paise` the browser sends and stores it without checking. So tax is
*already* editable by anyone who can craft a request; the UI is the only thing
pretending otherwise. Whatever we do at the till, the server should recompute
tax from a rate and the taxable amount, and reject a figure that does not
reconcile. That is a genuine integrity fix, not a feature.

**Second, log every override.** `ActivityLog` already has the machinery and
`Action.SETTING_CHANGED` is defined and never written. A bill where the tax was
changed from the default should say so in the activity log with who and what —
that is what makes "anyone at the till" safe rather than reckless.

**Third, the display bug it will cause.** The receipts print `Tax (17%)` from
the `tax_pct` *setting*. The moment someone enters a tax *amount* that does not
match that rate, the receipt will print a percentage that is arithmetically
wrong — on a tax invoice. So the sale needs to store the rate that was actually
applied (`tax_pct` on `Sale`), and the receipts must print that, falling back to
no percentage when tax was entered as a flat amount.

**At the till:** the existing tax checkbox becomes a small control — a rate box
defaulting to the Settings value, with the computed amount beside it and an
override for a flat figure. Same control on the quotation page.

**One caution to pass to the client:** if Speed Tech is FBR-registered, a tax
field that any cashier can change on any bill is something an auditor will ask
about. Worth him confirming with his accountant before we ship it wide open —
the owner/manager-only version is a two-line difference.

**Effort:** one day including the server-side recompute and the rate on the
sale.

---

## 7. Roles and user management — the honest answer

**You asked whether the system has it. It mostly does not.** Here is exactly
what is there, verified by logging in as a cashier and trying it:

| | Today |
|---|---|
| Roles on the user record | ✅ owner / manager / cashier / stock_clerk |
| Void a sale | ✅ blocked (403) |
| Change a setting | ✅ blocked (403) |
| Audit report | ✅ blocked (403) |
| Activity log | ✅ blocked (403) |
| **Reprice any product** | ❌ **allowed** — I set a Rs 1,000 camera to 1 paisa |
| **Add stock out of thin air** | ❌ **allowed** |
| **See every cost price and margin** | ❌ **allowed** |
| **Zero a customer's khata** | ❌ **allowed** — one request, Rs 5,000 debt gone |
| **Process a return** | ❌ **allowed**, any sale, any amount, unlimited |
| **The sidebar** | ❌ every page shown to everyone; no route is role-guarded |
| **Create a staff account** | ❌ **no API at all** — Django Admin only |
| **Change a role, deactivate a leaver** | ❌ Django Admin only |
| **Reset a forgotten password** | ❌ **nothing** — needs a command line |

That last group is the one I would worry about first. Today, if the owner
forgets his password, the system is inaccessible until a developer runs
`manage.py changepassword`. On a cloud deployment where you are the developer,
that is a phone call to you at 9pm.

### What it needs

**Server side** — one clean pass, roughly a day:

- `permission_classes` on the four catalog viewsets, so cashiers read but do
  not write.
- `outstanding_paise` and other derived money fields set read-only.
- Cost price and the inventory valuation report gated to owner/manager.
- Returns gated, or capped by value with manager approval above it.
- Login throttled, and failed logins written to the activity log.

**A Users page** — one to two days:

- List staff with role and last login.
- Add a user: name, email, role, temporary password.
- Change role, deactivate (never delete — sales point at the cashier).
- Reset password, and force a change on first login.
- Owner-only. A manager should not be able to promote himself.

**Frontend gating** — half a day:

- Nav items filtered by role, so a cashier does not see Audit, Activity or
  Settings at all.
- Route guards, so typing `/audit` redirects rather than showing an error.
- This is cosmetic security on its own — the server checks are what matter —
  but a cashier staring at a page he cannot open all day is bad product.

**A suggested default for Speed Tech:**

| | Owner | Manager | Cashier |
|---|---|---|---|
| Sell, print, share bills | ✅ | ✅ | ✅ |
| Customers, khata, take payments | ✅ | ✅ | ✅ |
| Returns | ✅ | ✅ | under a limit |
| Void | ✅ | ✅ | ✗ |
| Products, prices, stock-in | ✅ | ✅ | read only |
| Cost prices and margin | ✅ | ✅ | ✗ |
| Credit limits | ✅ | ✅ | ✗ |
| Reports and audit | ✅ | ✅ | ✗ |
| Activity log | ✅ | ✗ | ✗ |
| Settings, users | ✅ | ✗ | ✗ |

Worth asking him whether he wants a **Manager** at all, or just himself and
cashiers. Fewer roles is better if there is no real manager in the shop.

---

## 8. Removing a product

There is no delete or archive in the UI at all, and `DELETE /api/products/{id}/`
currently returns **500** when the product has any stock movement.

**Hard-deleting a product that has ever been sold must never be possible.** Old
bills reference it; delete the row and you corrupt history, which for a shop
that has to produce an invoice from two years ago for a warranty claim is
exactly the wrong trade.

So two operations, and the UI should offer whichever applies:

- **Archive** (the normal case) — sets `is_active = false`, which already
  exists. Disappears from search and the till, stays on every old bill, and can
  be restored. An "Archived" filter on the Products page.
- **Delete** — offered *only* when the product has no sales, no stock movements
  and no stock. Genuinely a typo being cleaned up. Owner/manager only, with a
  confirmation naming the product.

And the 500 becomes a 400 explaining that the product has history and offering
to archive it instead.

**Effort:** half a day, both ends.

---

## Suggested order

| | Why here |
|---|---|
| 1. **7 — roles, users, permissions** | Cloud makes it urgent, it closes three audit findings with it, and the password-reset gap is a 9pm phone call waiting to happen |
| 2. **8 — archive/delete a product** | Half a day, he asked for it, and it rides on the same permission work |
| 3. **6 — editable tax** | Fixes a real server-side integrity hole on the way |
| 4. **4 — warranty note** | English same day; Urdu once the font work is done |
| 5. **5 — quotations** | The biggest build, and the only one that is a new surface rather than a change to an existing one |

Backups (**0.4** in the audit) belong before any of it, because you have now
sold them.

---

*Item 1 applied and verified against the working tree · 218 backend tests · tsc clean · both receipts rendered and inspected · three mutations introduced and caught*
