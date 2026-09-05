# Phase 8B Frontend Carry-Over — Status & Completion Guide

**Current Status:** 2/8 steps started; foundation in place  
**Date:** 2026-09-04  

---

## ✅ Completed

### Step 1: ESLint Rule + Clear Palette Violations
- ✅ Added `no-restricted-syntax` rule to `.eslintrc.cjs` to prevent slate/purple/pink usage
- ✅ Fixed 37 violations:
  - 30 × `slate-*` → `n-*` (neutral tokens)
  - 6 × `purple-*` / `pink-*` → `teal-*`
  - Files updated: LanguageToggle.tsx, SettingsPage.tsx, CustomersPage.tsx, ReceiptTemplateSelector.tsx
- ✅ Verified: 0 violations remain

### Step 2a: Money/DateTime Components Foundation
- ✅ Components already exist at `src/components/ui/`:
  - `money.tsx` — Money component with compact mode
  - `date-display.tsx` — DateTime component with short/long/relative formats, plus Time helper
- ✅ Both properly exported and imported in DashboardPage

---

## 🔄 In Progress

### Step 2b: Replace 88 `paiseToRupees` + 21 `toLocale` calls

**Files & counts (highest priority first):**
1. AuditPage.tsx — 23 calls
2. ShiftsPage.tsx — 18 calls
3. CheckoutPage.tsx — 13 calls
4. BillsPage.tsx — 12 calls
5. ProductsPage.tsx — 8 calls
6. ReturnsPage.tsx — 8 calls
7. Others — 8 calls total

**Pattern to follow:**

```tsx
// BEFORE
import { paiseToRupees } from "@/lib/catalog";
...
<span>{paiseToRupees(paise)}</span>

// AFTER
import { Money } from "@/components/ui/money";
...
<Money paise={paise} />
```

**Money usage options:**
```tsx
<Money paise={1000} />              // "Rs 10.00"
<Money paise={1000} compact />      // "Rs 10"  
<Money paise={5000} sign />         // "+ Rs 50.00"
<Money paise={-2000} sign />        // "− Rs 20.00"
```

**DateTime usage options:**
```tsx
import { DateTime, Time } from "@/components/ui/date-display";

<DateTime value="2026-09-04" />           // "04 Sep 2026"
<DateTime value="2026-09-04" format="long" /> // "04 September 2026"
<DateTime value="2026-09-04" format="relative" /> // "2 hours ago"
<Time value="2026-09-04T15:02:00" />     // "15:02"
```

---

## 📋 Step 2b: Detailed Replacement Instructions

### AuditPage.tsx (23 calls)
Priority: **HIGH** — most calls, heavy data display
- Remove: `import { paiseToRupees } from "@/lib/catalog"`
- Add: `import { Money } from "@/components/ui/money"`
- Replace patterns:
  - `{paiseToRupees(row.total_paise)}` → `<Money paise={row.total_paise} />`
  - `{paiseToRupees(summary.sales_paise)}` → `<Money paise={summary.sales_paise} />`
  - Apply to all monetary fields in tables and summaries

### ShiftsPage.tsx (18 calls)
Priority: **HIGH** — reconciliation display critical
- Add Money for: opening_float, closing_cash, expected, variance, cash_in, cash_out
- Add DateTime for: opened_at, closed_at
- Replace variance display to use `<Money sign />` for ±

### CheckoutPage.tsx (13 calls)
Priority: **CRITICAL** — user-facing checkout
- Add Money for: subtotal, discount, tax, total, tendered, change
- Ensure compact mode doesn't apply (full precision needed)
- All must show `.00` decimals

### BillsPage.tsx (12 calls)
Priority: **HIGH** — sales history
- Add Money for table: sale amount, discount, total
- Add DateTime for: created_at column
- Use format="relative" for created_at to show "2 hours ago"

### ProductsPage.tsx (8 calls)
Priority: **MEDIUM** — inventory management
- Add Money for: price_paise, cost display
- Replace stock-value calculations

### ReturnsPage.tsx (8 calls)
Priority: **MEDIUM** — return management
- Add Money for return amounts
- Add DateTime for original sale date

---

## 📌 Steps 3-8 (Not Yet Started)

3. **Toasts on Every Mutation** (15-20 call sites)
   - Success toast when: settings save, void, stock-in, shift open/close, return create, customer add
   - Use existing `useToast()` from shadcn/ui
   - Pattern: `toast({ title: "Success", description: "..." })`

4. **Date-Range Picker**
   - Replace 4 native `<input type="date">` in AuditPage, CheckoutPage
   - Use Shadcn calendar component or DatePicker
   - Ensure Pakistan date format (DD/MMM/YYYY)

5. **P2-1 Products: Low vs Out Badge**
   - Distinguish: Out (stock = 0) danger red vs Low (stock < threshold) warning orange
   - Update ProductsPage badge logic

6. **P2-3 Dashboard: Sparkline + Low-Stock Panel**
   - Add revenue trend chart (7-day sparkline)
   - Add low-stock products list with inline "+Stock" button
   - Layout: side-by-side cards below totals

7. **P2-4 Checkout: Held Carts + Shortcut Legend**
   - Move F2/F3/F9/F12 legend to empty-cart state
   - Add "held carts" UI to save/restore partial checkouts
   - Requires new store/state logic

8. **P2-5 Bills: Detail Slide-Over + Summary Strip**
   - Replace modal with slide-over (right-side panel)
   - Add summary strip above table with total customers, total revenue
   - Add Pagination for large lists

9. **P2-6 Returns Stepper + Settings Layout**
   - Returns: multi-step wizard (select items → qty → reason → confirm)
   - Settings: two-column layout with live receipt preview on right

10. **P2-8 Font Files**
    - Ship `.woff2` files or remove font names from Tailwind config
    - Currently: Inter var font referenced but not bundled

---

## 🎯 Next Actions

1. **Complete Step 2b:** Replace all 88 + 21 calls in 6 pages using patterns above
2. **Test:** Verify Money/DateTime display in all 6 pages
3. **Commit Step 2**
4. Continue Steps 3-10 in order

---

## 🔗 Reference Files

- Components: `frontend/src/components/ui/{money.tsx, date-display.tsx}`
- ESLint: `frontend/.eslintrc.cjs`
- Pages to update: See "AuditPage.tsx" section above

---

## ⏱️ Estimated Effort

- Step 2b (88 + 21 replacements): **2-3 hours** (mostly search/replace)
- Steps 3-4 (toasts, date picker): **1 hour**
- Steps 5-6 (badges, dashboard): **2 hours**
- Steps 7-10 (complex UI): **4-6 hours**
- **Total Phase 8B: 9-12 hours**

---

**Next:** Begin Step 2b replacements, starting with AuditPage.tsx (23 calls).