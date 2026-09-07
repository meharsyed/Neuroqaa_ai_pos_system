# What is left — a full audit of the working tree

Read of the whole repo on 05 Sep 2026, after split payments landed.
**192 backend tests pass, `tsc --noEmit` clean.** Everything below is what
those green ticks do *not* cover.

Findings marked **PROVEN** were confirmed by running a throwaway test against
the real code — not read off the source and assumed. The probe file has been
deleted; nothing was left in the repo.

---

## First, a correction

I have told you three times that "the ESLint palette rule is still not in
place." **That was wrong.** The rule has been in `frontend/.eslintrc.cjs:14-20`
the whole time. Its regex is:

```
(slate|gray|zinc|neutral|stone|emerald|cyan|sky|indigo|violet|purple|rose|pink|fuchsia|lime)
```

It omits **red, orange, amber, yellow, green, teal and blue** — which are
218 of the 219 raw palette classes actually in the codebase. So the rule
exists, passes CI, and catches almost nothing. That is why the classes kept
coming back while I kept blaming a missing rule. The fix is one line, and it
is item 3.1 below.

---

## Tier 0 — Holes that lose money or data. Fix before the client touches it.

### 0.1 Any cashier can zero a customer's khata with one request — **PROVEN**

`backend/apps/customers/serializers.py:19-34` lists `outstanding_paise` in
`Meta.fields` with **no `read_only_fields`**, and `CustomerViewSet` includes
`UpdateModelMixin`. I logged in as a cashier and ran:

```
PATCH /api/customers/3/   {"outstanding_paise": 0}
→ 200 OK.  Rs 5,000 debt gone.
```

This walks straight past the append-only `CreditLedgerEntry` that the entire
khata design rests on. It is also almost certainly the source of the balance
drift that made me write `check_khata --repair` in the first place — I built
a tool to detect the drift without ever closing the door causing it.

**Fix:** add `read_only_fields = ["outstanding_paise", "created_at"]` to
`CustomerSerializer.Meta`. Balances may only move through `post_credit_entry`.
Add a test that a cashier's PATCH is ignored. **~30 minutes.**

### 0.2 The entire catalog app has no permission checks — **PROVEN**

`backend/apps/catalog/views.py:24, 32, 150, 186` — none of the four viewsets
declares `permission_classes`, so they fall back to plain `IsAuthenticated`.
As a cashier I got:

| Action | Result |
|---|---|
| `PATCH /api/products/1/ {"sell_price_paise": 1}` | **200** — a Rs 1,000 camera is now 1 paisa |
| `POST /api/inventory/stock-in/ {"qty": "9999"}` | **201** — 9,999 units invented from nothing |
| `POST /api/categories/` | **201** |
| `GET /api/products/1/` | cost price visible |
| `GET /api/reports/inventory/` | **200** — every cost and margin in the shop |

Meanwhile `void` correctly returns 403, settings writes return 403, and the
audit report returns 403. The pattern was started and never finished:
`apps/accounts/permissions.py` has `IsOwnerOrManager` and
`IsOwnerOrManagerOrReadOnly` ready to use, and the catalog app never imports
them.

Repricing is the classic till fraud — mark the item down, sell it, pocket the
difference. On DVR and NVR stock it is worth doing.

**Fix:** `permission_classes = [IsOwnerOrManagerOrReadOnly]` on the four
viewsets; `IsOwnerOrManager` on `stock_in`; drop `cost_price_paise` from the
product serializer for cashiers; gate `report_inventory` like `report_audit`
already is (`apps/sales/views.py:371-375`). Then add the test that is missing
— **every existing catalog test creates an owner**, so nothing here would ever
have been caught. **Half a day.**

### 0.3 A cash refund makes the till short every time — **PROVEN**

`create_return` (`apps/sales/services.py:409-525`) creates the negative sale,
restores stock, and reverses the khata — but for a cash sale it **never
creates a Payment row for the money handed back**. Since shift reconciliation
now sums cash tenders, refunds are invisible to it:

```
Sell Rs 5,000 cash          → drawer expects Rs 5,000
Refund the entire sale      → drawer still expects Rs 5,000
Actual cash in drawer: Rs 0 → a Rs 5,000 "shortage" at close
```

The cashier gets blamed for a shortage they did not cause, or — worse —
everyone learns to ignore the variance, which is the whole point of counting
the drawer. This existed before split payments; the new reconciliation just
makes it exact instead of vague.

**Fix:** write a negative `Payment` on the return sale for the refunded
amount and method, and let `_cash_taken_paise` net it off. Test: sell cash,
refund, expect the drawer back at the opening float. **Half a day.**

### 0.4 There is no backup. At all.

One SQLite file at `backend/data/pos.db` (`config/settings/desktop.py:26-31`),
one management command in the whole project (`check_khata`), no
`dumpdata` wrapper, no scheduled copy, nothing in `scripts/` (empty folder).

A failed disk, a ransomware hit, or one bad `rm` and Speed Tech loses every
sale, every customer, and every khata balance with no recovery. This is the
single largest risk in the system and it is also one of the cheapest to fix.

**Fix:** a `manage.py backup_db` command that does a SQLite online backup
(`sqlite3.Connection.backup()`, safe while the app is running) to a
timestamped file, keeps the last N, and can target a second drive or a
OneDrive folder — the client already has OneDrive on that PC. Wire it to
Windows Task Scheduler at close of business, and surface "last backup: 2
hours ago" on the dashboard so a silent failure is visible. **One day.**

### 0.5 A cashier can process a return but not a void — **PROVEN**

`apps/sales/views.py:140-163` — `create_return` has no role check, while
`void` at `:120-126` does. Returning every line of a bill is a void with extra
steps, so the void restriction is decorative. A cashier can also return
against **any** sale, any age, any amount.

**Fix:** either gate returns to owner/manager, or (better for a real shop)
allow cashiers to return under a configurable rupee ceiling and require a
manager above it. **Half a day.**

---

## Tier 1 — Before it can be handed over as a product

### 1.1 There is no desktop app. `desktop/` is an empty folder.

`docs/PROJECT_CONTEXT.md:31` says "Desktop shell: Tauri (Rust) — future
phase", and the folder confirms it: **zero files**, no `tauri.conf.json`, no
`Cargo.toml`. `config/settings/desktop.py` is written for a Tauri host that
does not exist.

So today, running the POS means opening a terminal, activating a venv,
starting Django, opening a second terminal, and starting Vite. That is not
something you can leave with a shop in Quetta.

**Options, cheapest first:**

1. **Two `.bat` files + a shortcut** (half a day) — `start-pos.bat` launches
   both servers minimised and opens the browser. Ugly, but it works Monday.
2. **Serve the built frontend from Django** (one day) — `npm run build`, point
   Whitenoise at `dist/`, one process on one port. Removes Node from the shop
   PC entirely. This is the one I would do next.
3. **Tauri as planned** (several days) — a real `.exe`, an icon, auto-start.
   Worth it once the shop is actually running on option 2.

Whichever you pick, it needs: auto-start on login, a fixed port, a visible
"the POS is running" indicator, and a documented recovery step for when it
is not.

### 1.2 The thermal printer only works over the network

`apps/sales/receipts/__init__.py:47-71` drives ESC/POS over **TCP port 9100
only**. Most counter printers in Pakistani shops are **USB**. If Speed Tech's
printer is USB, the Print button raises and the PDF is the only path.

**Ask first, then build:** find out what printer they actually have. If it is
USB, `python-escpos` supports it via `escpos.printer.Usb` (needs libusb on
Windows) — or, more reliably on Windows, print the PDF to the default printer
with SumatraPDF or the raw spooler. **Half a day once the printer is known.**

### 1.3 No way to add a member of staff

`apps/accounts/urls.py` exposes login / refresh / me / activity and nothing
else. To create a cashier account the owner must open Django Admin at
`/admin/`. There is also **no password reset** anywhere — a forgotten owner
password needs `manage.py changepassword` at a command line.

**Fix:** a Users page (owner-only) — list, invite, set role, deactivate,
reset password. **One to two days.** Nothing else in Tier 1 matters if the
owner locks himself out.

### 1.4 No rate limiting on login

`config/settings/base.py:112-127` sets no `DEFAULT_THROTTLE_RATES`, and
`LoginView` sets none. Failed logins are not written to `ActivityLog` either,
so a brute-force attempt leaves no trace. On a LAN-only install this is low
risk; the moment it is exposed for remote access it is not.

**Fix:** DRF `ScopedRateThrottle` on login (say 10/min per IP) plus a
`login_failed` activity entry. **One hour.**

### 1.5 Settings changes are silent

`ActivityLog` has `Action.SETTING_CHANGED` and `Action.STOCK_IN` defined
(`apps/accounts/models.py:47-57`) and **nothing ever writes them**. Only six
call sites exist: login, sale created, shift opened, shift closed, return
created, sale voided. So changing the tax rate, the shop name, the default
credit limit, or turning off receipt sharing leaves no record — and neither
does a stock adjustment, which is exactly where shrinkage hides.

**Fix:** `log_activity` in `SettingViewSet.update` and in the `stock_in`
action, with old and new values in `details`. **Two hours.**

---

## Tier 2 — What the shop will ask for within a month

### 2.1 There is no supplier side at all

Grep for `Supplier`, `PurchaseOrder`, `GoodsReceived` — nothing. Stock
appears through a bare `StockMovement` with a free-text `reference`. So the
system can tell you what every customer owes **you**, and nothing about what
**you** owe your distributors, which for a CCTV dealer buying on 30-day terms
from Karachi is the bigger number.

Minimum useful version: a `Supplier` model, a `supplier` FK on stock-in,
purchase history and cost trend per supplier, and a payables ledger reusing
the `CreditLedgerEntry` pattern that already works. **Three to four days.**
This is the largest genuinely missing feature in the product.

### 2.2 A returned faulty camera goes straight back on the shelf

`create_return` (`apps/sales/services.py:489-495`) calls `apply_stock_movement`
with a positive quantity for every returned line, unconditionally. There is no
"damaged / not resellable" flag on `ReturnItemSerializer`. A DVR returned
because it is dead is immediately sellable again — and will be sold again.

**Fix:** a `restock: bool` per return line; when false, write the movement as
`DAMAGE` instead of `RETURN` so it leaves stock and shows in shrinkage.
**Half a day.** For a security-equipment dealer this is close to Tier 1.

### 2.3 A payment cannot be applied to a specific bill

Khata payments land against the customer's total balance
(`PaymentReceived` + a ledger entry). You cannot say "this Rs 3,000 clears
SALE-20260905-00041". `CreditLedgerEntry` already has the `sale` column to
support it, so this is mostly UI plus a FIFO allocation rule.

Without it the aged-receivables buckets are approximate, and "which bills are
still open for this customer" cannot be answered exactly. **One to two days.**

### 2.4 No exchange

Returning and re-selling are two transactions with nothing linking them.
Common at a counter ("this one's the wrong lens"). **One day.**

### 2.5 Reporting gaps

`apps/sales/reports.py` covers daily summary, inventory valuation, and a P&L
audit report; `apps/customers/views.py:228-283` has a genuinely good aged-
receivables report. Missing:

- **Profit by category** — top products is per-SKU only (`reports.py:262-288`).
- **Cashier performance** — sales, voids, returns and average basket per
  cashier. Given 0.5, the voids-and-returns-per-cashier view is a control, not
  a vanity metric.
- **FBR / sales-tax export** — `tax_paise` is captured per sale but there is
  no filing-shaped export.
- **Return-rate and shrinkage** — no "most returned SKU", no adjustment
  summary. Pairs with 2.2.
- **COGS uses *current* cost, not cost at time of sale** — flagged in the
  code's own docstring at `reports.py:128-130`. When a camera's cost changes,
  last quarter's margin silently changes with it. Fix by stamping
  `cost_price_paise` onto `SaleItem` at sale time. **Half a day, and it gets
  harder the longer the history grows — do this one early.**

### 2.6 No stock take

There is an `ADJUSTMENT` movement type but no counting workflow: no way to
enter a physical count per SKU and have the system produce the variance. This
is how a shop finds out it has been robbed. **Two days.**

---

## Tier 3 — Debt that keeps costing you

### 3.1 The ESLint rule, properly this time

`frontend/.eslintrc.cjs:16` — extend the alternation with the seven missing
colours:

```js
selector: "Literal[value=/\\b(red|orange|amber|yellow|green|teal|blue|slate|gray|zinc|neutral|stone|emerald|cyan|sky|indigo|violet|purple|rose|pink|fuchsia|lime)-[0-9]{2,3}\\b/]",
```

Turning it on will fail the build on **219 existing occurrences across 17
files**. So do it in two commits: fix the files, then tighten the rule. Worst
offenders, in order:

| File | Count |
|---|---|
| `src/pages/DashboardPage.tsx` | 60 |
| `src/pages/CheckoutPage.tsx` | 37 |
| `src/pages/AuditPage.tsx` | 22 |
| `src/pages/ShiftsPage.tsx` | 21 |
| `src/components/ReceiptTemplateSelector.tsx` | 18 |
| `src/pages/SettingsPage.tsx` | 13 |
| `src/pages/LoginPage.tsx` | 11 |
| remaining 10 files | 37 |

**146 of the 151 affected lines have no `dark:` variant**, so the dark-mode
toggle currently produces unreadable panels on most pages —
`ShiftsPage.tsx:29-32` colours the cash-drawer over/short state this way,
which is the one status a manager reads in a hurry.

Every token these need already exists in `tailwind.config.js:95-109`
(`success`, `warning`, `destructive`, `info`, each with a `-bg` pair and
dark-aware `hsl(var(--x))`). **One day for all 17 files.**

### 3.2 The checkout keyboard legend lies to cashiers

`src/pages/CheckoutPage.tsx:647-650` tells the cashier:

```
F2 Print Receipt     F3 Payment Modes     F9 Discount     F12 Pay Now
```

The actual handler at `:456-461` binds F2 → focus search, F3 → focus barcode,
F9 → focus discount, F12 → open payment. Two of the four are simply wrong, and
this block is hardcoded English while the *other* legend in the same file
(`:606-614`) is correct **and** translated. **Ten minutes**, and it is the
first thing a new cashier reads.

### 3.3 Urdu exists but covers a quarter of the app

`src/lib/translations.ts` has full `en` and `ur` sets, and only **three of
twelve pages** call `t()` — Checkout, Dashboard, Login. Switch to Urdu and
Products, Bills, Returns, Customers, Khata, Shifts, Activity, Audit and
Settings stay in English. Either finish it or drop the toggle; a language
switch that changes a quarter of the screen reads as broken.

Also: `src/hooks/useTranslation.ts` is **dead code** — every import uses
`@/lib/useTranslation`, and the dead copy has a different signature (no
variable interpolation). Delete it before someone imports the wrong one.

### 3.4 The frontend has no tests, and the runner is configured to say so quietly

Vitest, Testing Library and jsdom are wired up in `vite.config.ts`, and
`src/test/setup.ts` imports jest-dom — but there is **not one `.test.tsx` file
in `src/`**, and `passWithNoTests: true` means `npm run test` reports green.
The only real test is `frontend/e2e/checkout.spec.ts`, a single Playwright
flow.

Start with the money paths: `PaymentModal`'s tender arithmetic (the cash-cap
and change logic in `applied`), and `Money` rendering. **Half a day for a
first meaningful set.**

### 3.5 Backend coverage excludes the risky code

`backend/pyproject.toml:27-33`:

```toml
omit = ["*/migrations/*", "*/tests/*", "*/customers/*", "*/receipts.py", "*/reports.py"]
```

The whole `customers` app — the khata, real money — plus the receipt renderer
and every report are exempt from the 70% gate. `customers/tests/test_khata.py`
is 389 lines, so the coverage is actually there; the config just means nobody
would notice if it disappeared. Also `apps/config` has **no test file at all**,
despite gating the tax rate, credit-limit default and the receipt-sharing kill
switch. **One hour to fix the config, then let it fail honestly.**

### 3.6 Smaller things

- `DELETE /api/products/{id}/` returns **500** on a `ProtectedError` when the
  product has stock movements. Should be a 400 saying "deactivate it instead".
  (Confirmed while probing.)
- Four places read only `response.data.detail` and swallow DRF field errors:
  `ShareReceiptButton.tsx:46`, `lib/customers.ts:83`, `lib/reports.ts:84`,
  `ReturnsPage.tsx:336`. I fixed this pattern on Checkout in Phase 9; these
  four were missed.
- `receipt_text`, `receipt_html` and `receipt_print` (`apps/sales/views.py:166,
  204, 242`) call `.get(pk=pk)` with no `DoesNotExist` guard — a bad id 500s.
  `receipt_pdf` does it correctly at `:182`.
- `aria-label` appears **four times in the whole frontend**. Icon-only buttons
  rely on `title`, which a screen reader does not announce.
- JWT `ROTATE_REFRESH_TOKENS=True` with `BLACKLIST_AFTER_ROTATION=False`
  (`base.py:133-134`) — a rotated-out refresh token stays valid for its full
  30 days on desktop.
- `low-stock` (`catalog/views.py:134-147`) returns unpaginated.
- **`Claude outputs/`** — 4 sample PDFs, 32 KB, in the repo root. Safe to
  delete. Fourth time of asking.

---

## If you only do five things

1. **0.1** — read-only `outstanding_paise`. Thirty minutes, closes a hole that
   makes the whole khata ledger optional.
2. **0.4** — a backup command and a scheduled task. One day, and it is the
   difference between a bad week and the end of the business.
3. **0.2** — permissions on the catalog app. Half a day, stops repricing.
4. **0.3** — refunds as negative payments. Half a day, makes the drawer count
   mean something.
5. **1.1 option 2** — serve the built frontend from Django. One day, and the
   shop can actually run this without a developer present.

That is roughly **three to four days** and takes the system from "impressive
demo" to "safe to leave with a client."

After that, **2.5's COGS-at-time-of-sale** is the one I would not delay — it
quietly corrupts historical margin every time a purchase price changes, and it
only gets more expensive to fix as history accumulates.

---

*Audit of the working tree at 05 Sep 2026 · findings marked PROVEN were reproduced against running code · probe files removed*
