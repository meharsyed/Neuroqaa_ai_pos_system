# Speed Tech POS — changes, verification, and how to run

Everything below is applied to your working tree.

---

## 1. What changed in this pass

### Logo — extracted from your JPEG, no placeholders left

Your file had the shield sitting on a textured "network" background with the wordmark underneath. The shield is three separate graphic elements (chevron / ST / V) divided by a white glow, so a naive largest-object crop grabbed only the middle third. I separated it on colour instead: the background and network lines are neutral-to-blue, the shield is green-tinted.

| File | What | Where it shows |
|---|---|---|
| `backend/apps/sales/receipts/assets/logo-invoice.png` | 320px, transparent, 48 KB | A4 / A5 invoice header |
| `backend/apps/sales/receipts/assets/logo-thermal.png` | 384px **1-bit**, 3 KB | 80mm / 58mm thermal slip |
| `frontend/public/brand/logo-mark.svg` | vector, `currentColor` | general use |
| `frontend/public/brand/logo-mark-mono-light.svg` | vector, white | sidebar, login |
| `frontend/public/brand/logo-full.svg` | vector + wordmark | login / marketing |
| `frontend/public/brand/favicon.svg` | vector, brand green | browser tab |

The four SVGs replace the ones the agent hand-drew, which were a **generic shield with a checkmark** — not your logo at all. These are traced from the real artwork.

**Invoice size: 428 KB → 48 KB.** My first logo export was 280 KB and got embedded in every single PDF. At 20mm print size you only need ~240px, so I requantised to 320px. Nine times smaller, no visible difference on paper.

### Build is green

| Was | Now |
|---|---|
| `components/Money.tsx` — unused `className`, orphan | **deleted** |
| `components/DateTime.tsx` — unused `className`, orphan | **deleted** |
| `ReturnsPage` — 2 dead handlers | removed; stepper rebuilt (below) |

The duplicate was resolved by deletion, not merging: **all 11 pages import `components/ui/money.tsx`**, and the two files at `components/` were imported by nobody. They were dead code that only existed to break the build.

`components/ui/money.tsx` also got two improvements:

- **Dropped `font-mono`.** Every price was rendering in a typewriter face next to a sans-serif UI. `tabular-nums` already fixes digit alignment, so columns still line up — they just stop looking like a terminal. *This changes the look of every price in the app; it's a one-word revert if you disagree.*
- **Added `decimals="auto"`**, which drops a meaningless `.00` on whole rupees. Default is unchanged (`always`), so nothing moves until you opt in per call site.

### Returns page — the stepper was lying

It rendered a 4-step indicator (Search → Select → Reason → Confirm) that **never advanced past step 1**. `handleSearch` tried to advance with `if (sale)`, but `sale` is derived from the query result and is still `null` on that tick, so the branch could never fire. The two handlers meant to advance it were never wired to any button.

The page itself is fine — it shows "select items" and "confirm" together on one screen, which is the right design for a returns desk. Only the indicator was wrong. It's now **three stages derived from real state**, so it tracks live as the cashier types quantities:

```
no bill found      → Find Bill
bill, nothing typed→ Select Items
any return qty > 0 → Confirm Return
```

Also replaced `bg-blue-50`, `text-blue-600/700`, `bg-blue-600` on that page with design tokens — none had dark-mode variants.

### Token layer — three tokens were unreachable

`--accent-soft`, `--border-strong` and `--chrome-active` were defined in **both** `:root` and `.dark` in `index.css`, but never registered in `tailwind.config.js`. So `bg-accent-soft` silently produced nothing — Tailwind drops classes it doesn't know, with no error. All three are now wired.

I caught this because my own first patch used `bg-accent-soft` and I checked before trusting it.

### Login page — it was branded as your company, not your client's

The left panel said **"Neuroqaa POS"** with a lightning-bolt icon; the mobile header said the same. That's the first screen your client sees in the demo. Both now show the real shield and **"Speed Tech Solutions"**. The "Powered by Neuroqaa.ai" credit lines are untouched — those belong there.

### Regression tests — `backend/apps/sales/tests/test_credit_and_serials.py`

16 new tests, one per bug that shipped silently:

- credit `Payment` is linked to its sale, tenders 0, creates no orphan rows
- credit sale increases the customer balance by the total
- **the receipt says `credit`, not `cash`**
- credit without a customer → 400, and creates nothing
- cash without a customer still works
- duplicate serial → 400 not 500, with stock and sale count unchanged
- distinct serials accepted
- `daily_summary` has no `None` key in `payment_breakdown`
- audit PDF renders with credit sales in range
- **legacy** credit sales (no `Payment` row at all) still group and export
- all three renderers handle a credit sale

---

## 2. How I verified it

| Check | Result |
|---|---|
| Full backend suite | **108 passed** |
| `npx tsc --noEmit` | **clean** — zero errors |
| Receipt renders | 16 combinations (A4/A5/80mm/58mm × normal/discount/voided/credit) |
| Logo resolution | confirmed through the real Django package path, not a stub |
| End-to-end render | rendered `SALE-20260905-00039` from your actual database |
| Visual inspection | rasterised and looked at the A4, A5, thermal, credit and voided output |

**Mutation test.** All 16 new tests passed on the first run, which is exactly when a test suite is most likely to be vacuous. So I reintroduced the `sale=None` bug on purpose and re-ran: 4 tests failed with `assert 'cash' == 'credit'`. Then I restored the file. The tests genuinely bite.

### What I could NOT verify — please check these

1. **`npm run build`.** The `tsc` half now passes, which is the half that was failing. I couldn't run the `vite build` half: your `node_modules` only contains `@rollup/rollup-win32-*` binaries and my shell is Linux, so rollup can't load. **Run it on your machine to confirm.**
2. **Actual thermal hardware.** The 1-bit logo is correct by construction and looks right rasterised, but I have no printer.
3. **The new SVGs in your browser.** They render correctly through cairosvg here; Chrome should agree, but glance at the sidebar and tab icon.

### Judgement calls you may want to reverse

- **`font-mono` removal from `Money`** — visible everywhere. Revert by re-adding `font-mono` to the `cn()` call in `components/ui/money.tsx`.
- **Deleting the two orphan components** — irreversible, but `tsc` proves nothing imported them.
- **Returns stepper is now 3 stages, not 4.** "Enter Reason" disappeared as a stage because the reason field lives inside the confirm section. If you want a true 4-step wizard that's a bigger change.

---

## 3. Run it

```powershell
# Terminal 1
cd "D:\Neuroqaa Stuff\POS System\pos-system-GT\backend"
.\venv311\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
python manage.py runserver

# Terminal 2
cd "D:\Neuroqaa Stuff\POS System\pos-system-GT\frontend"
npm run dev
```

No migrations were added.

**Confirm the build and the tests on your side:**

```powershell
cd frontend ; npm run build          # should now succeed
cd ..\backend ; pytest -q            # expect 108 passed
```

---

## 4. Test checklist

**Logo**
1. Login screen — real shield, "Speed Tech Solutions", no lightning bolt.
2. Sidebar and browser tab — real shield.
3. Any bill → PDF (A4) — shield top-left of the header.
4. Same bill → thermal — solid black shield, centred, crisp.
5. Check the PDF file size is ~50 KB, not ~430 KB.

**Money formatting**
6. Prices now render in the UI font with aligned digits, not monospace. Check Products, Bills, Dashboard, Checkout.

**Returns**
7. Open Returns — indicator on **Find Bill**.
8. Search a bill — moves to **Select Items**.
9. Type a return quantity — moves to **Confirm Return** as you type.

**The five earlier fixes** (all now covered by tests, but worth eyeballing)
10. Duplicate serial → red toast, cart intact.
11. Credit sale with no customer → "A credit (khata) sale requires a customer."
12. Credit sale → invoice shows **Paid now 0.00** and **BALANCE DUE (Khata)**.
13. Audit Reports → Download → PDF with a credit sale in range → downloads, shows a CREDIT row.
14. Stop the backend, open Khata → error state with Retry, not "All customers are paid up!".

---

## 5. Still open

From `docs/PHASE_9_KHATA_AND_DEMO_FIXES.md`, unchanged and in priority order:

1. **§2.1 — no credit ledger.** Credit sales only mutate a denormalised balance; a wrong number can't be found or repaired.
2. **§2.3 — voids and returns don't reverse the balance.** Void a Rs 50,000 khata sale and the customer still owes it. **The most dangerous open bug.**
3. **§2.2 — lost updates.** `outstanding_paise += x` with no row lock.
4. **§2.5 — any cashier can zero any customer's balance.** No role check on `record_payment`.
5. **§3 B6 — serials aren't globally unique.** I stopped duplicates *within one bill*; across bills the DB still allows the same camera to be sold twice.
6. **§4 C1 — the ESLint palette rule.** Still not added; `KhataPage` and `PaymentModal` still carry raw `text-red-500` / `bg-blue-50` classes with no dark-mode variants. Until the rule exists this keeps coming back.

Items 2 and 5 are the two I'd do next — both are money or warranty correctness, not polish.

---

*All changes applied and verified against the working tree · 108 backend tests, tsc clean, renders visually confirmed*
