# Phase 14 — Suppliers built as designed

**Status: built, statically validated, awaiting your test run.** Design in `docs/FEATURE_DESIGN_SUPPLIERS.md`; this is the implementation of that plan, unchanged in shape — one new model, one new nullable column, nothing else in the system touched.

---

## Run it

Same situation as Phase 13: this session has no network access to install packages or run `manage.py` itself, so nothing below has actually been executed here. What *was* done: every backend file was checked with `py_compile` and a full AST parse (both clean), every frontend file was checked with `tsc --noEmit` and `eslint --max-warnings 0` (both clean, zero errors), and the new Urdu translations were run through the exact same four checks `lib/__tests__/translations.test.ts` performs (key parity, no blanks, matching `{placeholders}`) — all four pass. That's the strongest verification available without a working Django/npm install in this environment. Treat the steps below as the real acceptance test.

```powershell
cd "D:\Neuroqaa Stuff\POS System\pos-system-GT\backend"
.\venv311\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
python manage.py makemigrations --check --dry-run   # see "About the migration" below
python manage.py migrate
ruff check .
black --check .
pytest -q                                            # expect 342 passed (328 + 14 new)
python manage.py runserver
```

```powershell
cd "D:\Neuroqaa Stuff\POS System\pos-system-GT\frontend"
npm run type-check
npm run lint
npm run test                                         # expect 28 passed, unchanged — no new frontend tests added
npm run dev
```

---

## What was built

**Backend** (`apps/catalog/`):

- `models.py` — new `Supplier` model (name, contact person, phone, email, address, notes, `is_active`), and one new nullable `supplier` FK on `StockMovement` (`on_delete=PROTECT`).
- `migrations/0008_supplier.py` — hand-written (see below), two additive operations: `CreateModel Supplier`, `AddField StockMovement.supplier`.
- `serializers.py` — `SupplierSerializer` (plain CRUD shape); `StockInSerializer` gains an optional `supplier` field (a product/is-active-filtered `PrimaryKeyRelatedField`, same pattern as the existing `product` field); `StockMovementSerializer` gains `supplier`/`supplier_name`.
- `services.py` — `apply_stock_movement()` takes an optional `supplier` keyword and stores it on the movement row. Every existing caller that doesn't pass it is unaffected.
- `views.py` — new `SupplierViewSet` (`IsOwnerOrManagerOrReadOnly`, same bar as the catalogue): list/create/update normally, plus a `destroy()` override that **deactivates** a supplier with purchase history instead of hard-deleting it (StockMovement.supplier is `PROTECT`, so without this override the first delete attempt on a used supplier would crash with a raw 500 — the same bug class `Product.destroy()` already guards against) and a `restore` action to reactivate one. `stock_in` now threads `supplier` through to the service call and into the activity log. `StockMovementViewSet` gained `supplier` to its filter fields — this is what serves "purchase history for supplier X" with no new endpoint: `GET /api/movements/?supplier=<id>&movement_type=stock_in`.
- `urls.py` — `/api/suppliers/` registered.
- `admin.py` — `SupplierAdmin` registered (list/search by name, contact, phone), matching `CategoryAdmin`'s shape.
- `tests/test_suppliers.py` — 14 new tests: CRUD and the read-for-everyone/write-for-management permission split, the deactivate-vs-delete behaviour (including the exact "supplier already has purchase history" case that would otherwise 500), stock-in with and without a supplier attached, and the movements-endpoint-as-purchase-history filter.

**Frontend** (`frontend/src/`):

- `types/catalog.ts` — `Supplier` interface; `StockMovement` and `StockInFormValues` gained `supplier`/`supplier_name` fields.
- `lib/catalog.ts` — `catalogApi.suppliers` (list/get/create/update/remove/restore), plus `purchaseHistory(supplierId, page)` — it's a thin filter over the existing `/movements/` endpoint, not a new one, per the design doc.
- `lib/permissions.ts` — `can.manageSuppliers` (same bar as `can.editCatalogue`) and a new `/suppliers` entry in `ROUTE_ACCESS` — a cashier who types the URL directly is bounced to the dashboard, same as `/audit` or `/settings`.
- `pages/SuppliersPage.tsx` — new page: searchable list, add/edit modal, a purchase-history modal (reusing the movements filter above), and a deactivate/reactivate control. Built to match `CustomersPage.tsx`'s exact structure, components, and Tailwind theme tokens (`bg-background`, `text-muted-foreground`, the same table/badge/skeleton patterns) — same look and feel as the rest of the app, not a new style.
- `router/index.tsx` — `/suppliers` route registered.
- `layouts/components/AppSidebar.tsx` — new "Suppliers" nav item (Truck icon) in the Management section, gated by `can.manageSuppliers` — a cashier signed in simply won't see the link.
- `components/catalog/StockInModal.tsx` — one new optional Supplier `<Select>`, populated from `catalogApi.suppliers.list()`, using the exact same `<Select>` component and pattern as the category picker in `ProductModal.tsx`. Left un-translated (no `useTranslation()` calls) deliberately — the rest of that file is plain hardcoded English today, and mixing one translated field into an otherwise-untranslated form would be inconsistent, not an improvement; bringing the whole modal into i18n is a separate, larger piece of work outside this feature's scope.
- `lib/translations.ts` — 36 new keys × 2 languages (`nav.suppliers` plus the `suppliers.*` block) for `SuppliersPage.tsx`, which — like `CustomersPage.tsx` — is fully i18n-wired.

---

## About the migration

`apps/catalog/migrations/0008_supplier.py` was hand-written for the same reason as the two migrations in Phase 13 — this session still has no route to install Django (PyPI returns 403 from both this environment's and your machine's shell, confirmed again). It's two purely additive operations (a new table, a new nullable column on an existing one), which is the safest shape a hand-written migration can take. Run `python manage.py makemigrations --check --dry-run` after `pip install` — if Django wants anything more, it'll say so in one line, and it would be an additive follow-up migration, not a sign anything here is broken. (Phase 13's hand-written migrations both matched exactly except for one unrelated historical-model migration Django generated on its own — `0007_alter_historicalproduct_image.py` — which is already in the repo now.)

---

## Manual test walkthrough

Once the migration and both dev servers are up:

1. **Sign in as owner or manager.** You should see a new **Suppliers** link in the sidebar, under the same section as Customers.
2. **Add a supplier** — name is the only required field. Try one with just a name, and one with every field filled in.
3. **Search** the list by name, contact person, or phone.
4. **Edit** a supplier's details and confirm the change sticks.
5. **Go to Products → pick a product → Stock In.** You should see the new **Supplier** dropdown between Cost Price and Reference, listing the suppliers you just added, with a "— Select supplier —" option to leave it blank. Record a stock-in with a supplier picked, and one without — both should succeed identically to before.
6. **Back on the Suppliers page**, click the supplier you picked in step 5 (or its history icon). The purchase-history table should show that stock-in: product, quantity, cost price, date, and your reference note.
7. **Deactivate** a supplier that has no purchase history yet — it should be deleted outright (the toast will say so). Deactivate one that *does* have history — it should be marked inactive instead, disappear from the default list, and reappear if you reactivate it.
8. **Sign in as a cashier** (or any non-owner/manager role) and confirm: no Suppliers link in the sidebar, and navigating to `/suppliers` directly redirects to the dashboard. The Stock In dialog's Supplier field should still work for them if their role can stock-in at all — reading the supplier list is intentionally open to everyone signed in, only adding/editing/removing suppliers is management-only.
9. **Switch the language toggle to Urdu** and revisit the Suppliers page — every label should render in Urdu, not fall back to a raw key like `suppliers.title`.

If all nine hold, this is done. Nothing about Sale, Checkout, Quotations, or Khata was touched by any of this, so there's nothing to regression-test there — but running the full `pytest`/`npm run test` suites in the "Run it" section above is still the real confirmation, the same as last time.

---

## What's still deliberately not built

Unchanged from the design doc: no backfilling suppliers onto historical stock-in records, and no accounts-payable / supplier-credit tracking. Both remain legitimate future scope, not gaps in this delivery.
