# Roles, product removal, editable tax, warranty clause

All four applied to the working tree. **290 backend tests pass (77 new),
`tsc --noEmit` clean, ESLint clean on every file touched.**

---

## Run it

```powershell
cd "D:\Neuroqaa Stuff\POS System\pos-system-GT\backend"
.\venv311\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"

pip install -r requirements\base.txt   # two new packages — see §4
python manage.py migrate               # 7 migrations
pytest -q                              # expect 290 passed
python manage.py runserver
```

```powershell
cd ..\frontend ; npm run dev
```

**`pip install` is not optional this time.** The Urdu warranty clause needs
`arabic-reshaper` and `python-bidi`. Without them the invoice still prints —
it drops the Urdu line rather than crashing — but you will wonder why the Urdu
never appears.

---

## 1. Roles, permissions and staff accounts

### What was open, and now is not

Every one of these I reproduced as a signed-in cashier before fixing, and each
now has a test that only ever acts as a cashier — the reason these holes lived
so long is that **every existing catalog and sales test signs in as an owner.**

| | Before | Now |
|---|---|---|
| Reprice a product | Rs 1,000 camera → 1 paisa, **200 OK** | 403 |
| Add stock from nothing | 9,999 units, **201** | 403 |
| Create a category | **201** | 403 |
| See cost price and margin | **visible** | field removed from the response |
| Inventory valuation report | **200** | 403 |
| Zero a customer's khata | **200 OK**, Rs 5,000 gone | ignored — read-only |
| Return against any bill, any amount | **unlimited** | capped, see below |

`outstanding_paise` is now read-only for **everyone including the owner** —
balances move through the credit ledger or they do not move. That is what
`check_khata` was written to detect drift in; this closes the door that was
causing it.

Cost price is *removed from the payload*, not hidden in the UI. Knowing what a
DVR costs tells a cashier exactly how far a price can be dropped before anyone
notices, which is the opening move in most till fraud.

### Returns are capped, not blocked

A return puts stock back and takes money off a bill — it is a void with extra
steps — so it could not stay looser than voiding. But a cashier handling
everyday returns is normal shop life, so:

- **`cashier_return_limit_paise`**, default **Rs 5,000**, in Settings.
- Under it, a cashier proceeds. Over it, they get a message naming the amount
  and telling them to fetch an owner or manager.
- Owners and managers are never capped.

**Raise or lower that number to suit the shop** — it is the one default here I
picked on your behalf.

### Staff accounts — the part that did not exist at all

New **Staff** page in the sidebar, owner only:

- Add a member of staff with a role and a temporary password.
- Change a role from the row.
- Deactivate and reactivate. **Never delete** — every bill points at the
  cashier who rang it up, and that has to survive them leaving.
- Reset a forgotten password.

And `POST /api/auth/change-password/` for anybody changing their own. Before
this, a forgotten owner password meant `manage.py changepassword` at a command
line — on a hosted deployment, a phone call to you at 9pm.

Three guards worth knowing about, each with a test:

- **A manager cannot manage staff.** If he could, he could promote himself and
  the difference between the roles would mean nothing.
- **You cannot demote or deactivate yourself.**
- **The last active owner cannot be demoted** — somebody has to be able to put
  everything back.

New accounts are flagged `must_change_password`, so the first thing a new
cashier sees is a dialog with no close button asking them to choose their own.
The owner hands over a password and then stops knowing it. This one is enforced
in the interface rather than the API — it is about not sharing passwords, not
a security boundary, and the owner knows the temporary password either way.

### The sidebar

Audit, Activity Log, Settings and Staff no longer appear for roles that cannot
open them, and typing `/audit` redirects instead of showing a page of failed
requests. The server refuses all four regardless — this is manners, not
security, and the code says so.

### The activity log finally records what it was built to

`Action.STOCK_IN`, `SETTING_CHANGED`, and failed logins were all defined in the
model and **never written**. Now:

| Recorded | Why it matters |
|---|---|
| Failed logins | A password-guessing run left no trace whatsoever |
| Stock adjustments | Stock appearing from nowhere is where shrinkage hides |
| Settings changes | The tax rate, credit limits, the sharing kill switch |
| Staff created / changed | Who gave whom what access |
| Password resets | Both by the owner and by the user |
| Tax overridden on a bill | See §3 |

**Login is now rate-limited** to 10 attempts a minute. On a LAN that was
academic; on the internet, a login page is found and hammered by bots within
days of the DNS record appearing. Throttling is off in tests via
`backend/conftest.py` and on everywhere else.

---

## 2. Removing a product

There was no delete or archive in the interface at all, and the API returned
**500** on a `ProtectedError`. Both fixed, with the distinction that matters:

- **Archive** — the normal answer. The product leaves the till, the search and
  the barcode scanner; it stays on every bill it has ever appeared on, and can
  be restored. There is a test that an archived product's old invoice still
  renders, because a warranty claim two years on is exactly when you need it.
- **Delete** — offered *only* when the product has never been sold, never been
  stocked, and holds no stock. A typo entered five minutes ago.

The dialog asks the server which it will be before offering a button, so it can
use the right word and say why. An **Archived** filter on the Products page
finds them again; each archived row carries a badge and a Restore button.

Owner and manager only, like the rest of the catalogue.

---

## 3. Editable tax

You said the client is not FBR-registered, so the till can change it.

### The bug underneath the feature

**The server was storing whatever `tax_paise` the browser sent, unexamined.**
So tax was already editable by anyone who could craft a request — the interface
was the only thing pretending otherwise. Tax is now computed on the server:

```
tax_pct given    → the server computes the amount and stamps the rate on the bill
tax_paise given  → taken as a flat figure, with no rate behind it
neither          → the shop's rate from Settings
```

Refused: a rate outside 0–100, a negative amount, and an amount larger than the
bill it is charged on.

### A receipt that changed its own history

The receipts printed `Tax (17%)` by reading the **live** shop setting. So
raising the shop rate silently rewrote the percentage on every past invoice the
next time it was printed — and a tax typed as a flat amount printed a
percentage that was simply wrong.

Each sale now carries `tax_pct`, the rate it was actually charged at.
Migration `0012` gives every existing bill its own, **derived from that bill's
own numbers** rather than from the setting. Where no sane rate can be derived,
and where tax was a flat amount, no percentage is printed at all — better
nothing than a wrong one.

### At the till

The tax checkbox is now a checkbox plus a rate box, defaulting to the shop
rate. Change it and a line appears saying what the shop rate is with a **reset**
link. Any bill taxed at something other than the shop rate is written to the
activity log with both figures.

The server rounds half-up to match the JavaScript `Math.round` the till uses to
show the number, so the customer is never quoted one figure and charged
another by a paisa.

---

## 4. The warranty clause

Four settings, in their own **Warranty Clause** section:

| Setting | Default |
|---|---|
| `warranty_note_enabled` | on |
| `warranty_note_language` | English / Urdu / Both |
| `warranty_note_en` | a sensible clause, editable |
| `warranty_note_ur` | the same in Urdu, in a right-to-left box |

He will want to reword it after the first argument with a customer, so it is
text in Settings rather than anything in code.

### Where it prints

- **A4/A5 invoice** — a bordered **WARRANTY TERMS** box below the totals,
  deliberately separate from the "goods returnable within 7 days" footer. That
  is a returns promise; this is what voids a warranty, and a customer arguing
  about a burnt-out DVR needs to be able to point at one of them.
- **Shared web bill** — same, and Urdu costs nothing there because the browser
  shapes and lays it out itself.
- **80 mm till slip** — English only, and **only when the bill carries serial
  numbers**, as you asked. No serial, no warranty to void, and roll is not free.

### What Urdu on a PDF actually took

Three things, and skipping any one produces something worse than English:

1. **A font with the glyphs.** Helvetica has none — Urdu comes out as empty
   boxes. Noto Naskh Arabic is now bundled in `receipts/assets/` (178 KB).
   Nastaliq is the more beautiful Urdu style but needs contextual positioning
   ReportLab cannot do; Naskh is the honest choice.
2. **Letter joining** — `arabic-reshaper`. Without it every letter renders in
   its isolated form, readable to nobody.
3. **Direction** — `python-bidi`. Without it the words are backwards.

Everything degrades to English, and then to nothing, rather than raising. A
missing font must never take a receipt down.

### The bug I shipped and then caught by looking at the page

I rendered the first Urdu invoice and the letters joined correctly, the line
was right-aligned, and it was **wrong**: the opening clause was printing at the
*bottom* of the box.

Reordering a whole paragraph right-to-left and then letting ReportLab wrap it
gives lines that are each individually correct but stacked backwards. The wrap
has to happen first, in logical order, with each line reordered on its own.
Fixed, rendered again, read it — and there is now a test that fails if the old
behaviour returns. I reintroduced the bug to confirm the test catches it.

**This is why the deliverable is a rendered page and not a passing assertion.**
Every assertion I had written was green while the clause read bottom-to-top.

---

## What to test

**Staff and roles** — create a cashier from Staff, sign in as them:

1. Audit, Activity Log, Settings and Staff are **absent from the sidebar**.
   Type `/audit` in the address bar → redirected.
2. Products: no cost price column, editing a price is refused.
3. Try a return worth more than Rs 5,000 → refused with the ceiling named.
   Under it → allowed.
4. Khata: a customer's balance cannot be edited by anyone.
5. Sign in as that cashier the first time → the password dialog appears and
   cannot be dismissed.
6. As owner: reset their password, deactivate them, confirm they cannot sign
   in, reactivate.
7. Try to demote yourself → refused.

**Products**

8. Products → bin icon on a product that has stock → the dialog says *archive*,
   explains why, and it disappears from the list.
9. **Archived** filter → it is there with a badge → Restore.
10. Add a product and immediately remove it → the dialog says *delete
    permanently*.
11. Open an old bill for an archived product → it still prints.

**Tax**

12. Checkout: change the tax rate on a bill → the amount follows, a line
    appears naming the shop rate with a reset link.
13. Complete it → Activity Log shows `tax_overridden` with both rates.
14. Change the shop rate in Settings → reprint an **old** invoice → it still
    shows the rate it was charged at.

**Warranty**

15. Settings → Warranty Clause → set **Both** → print an A4 invoice. English
    then Urdu, and **read the Urdu**: it must start top-right and run down.
16. Print the 80 mm slip for a bill **with** a serial → English clause. For a
    bill **without** → no clause.
17. Turn `warranty_note_enabled` off → gone everywhere.

---

## Verification

- **290 backend tests**, 77 new across four files.
- **Mutations introduced and confirmed caught**: folding installation into
  revenue (8 failures), a return eating labour debt (1), goods-settled-first
  (2), and the Urdu line-order bug (1). All restored.
- Both PDFs rendered and **looked at** — which is how the Urdu ordering bug and
  the amount-in-words bug were found.
- `tsc --noEmit` clean; ESLint clean on every file touched.

---

## Still open

1. **Quotations** — the remaining item from the client meeting. Designed in
   `CLIENT_REQUESTS_PLAN.md` §5; the biggest of the six and the only one that
   is a new surface rather than a change to an existing one.
2. **Backups** — you have sold these. There is still no code that makes one,
   and it is the largest risk in the system.
3. **The ESLint palette rule.** Still 219 raw palette classes across 17 files,
   146 lines of them with no dark-mode variant. The rule exists but its regex
   omits the seven colours that matter. `ROADMAP_AUDIT.md` §3.1.
4. **`AuditPage.tsx:158` calls `useQuery` conditionally** — a real React
   hooks-order bug, pre-existing, and ESLint has been flagging it. Worth
   fixing before it produces a confusing crash.
5. **Serving the frontend from Django** so the shop can run this without two
   terminals. `ROADMAP_AUDIT.md` §1.1.

---

*Applied and verified against the working tree · 290 backend tests · tsc and ESLint clean · invoices rendered and inspected · four mutations introduced and caught*
