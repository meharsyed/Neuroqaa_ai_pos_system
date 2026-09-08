# Feature design: Suppliers

**Client request, relayed:** record who products/stock are bought from, pick a supplier when stocking a product, and see a per-supplier history of what was bought and at what price.

**Status: design only — nothing built yet.** This is the recommendation to confirm before I touch any code, per how the last two rounds went (audit → your go-ahead → fixes; hosting analysis → your call → deployment scripts next).

---

## The one decision that matters: attach the supplier to the *purchase event*, not to the *product*

The tempting shortcut is a `supplier` field directly on `Product` — "this product's supplier is X." Don't do that here: a shop like this restocks the same SKU from different suppliers over time as prices and availability shift, and the client's own ask — *"which supplier, which product, **at what price**"* — is asking for a history, not a single current fact. A field on `Product` can only ever hold one answer per product; it would be wrong the first time you bought the same item from two different suppliers, and it can't answer "what did we pay Supplier A for this in March vs. Supplier B in June."

The good news: this system already has exactly the right place to hang this off. `apps/catalog/models.py` has a `StockMovement` model — an **append-only ledger of every inventory change** — with a `STOCK_IN` movement type that already snapshots `cost_price_paise` per event, plus a free-text `reference` field whose own placeholder text in the UI today literally says *"Purchase order / supplier ref."* That's the tell: the system already wanted this and was using a text field as a stand-in. The fix is to give it a real one.

## What actually changes

**One new table, one new column. Nothing else moves.**

1. **A new `Supplier` model**, in `apps/catalog/models.py` right alongside `StockMovement` — not a new Django app. It's the same shape as `Customer` (`apps/customers/models.py`), minus the khata-specific fields:

   ```python
   class Supplier(models.Model):
       tenant_id = models.IntegerField(default=1, db_index=True)
       name = models.CharField(max_length=200)
       contact_person = models.CharField(max_length=200, blank=True)
       phone = models.CharField(max_length=20, blank=True)
       email = models.EmailField(blank=True)
       address = models.TextField(blank=True)
       notes = models.TextField(blank=True)
       is_active = models.BooleanField(default=True)
       created_at = models.DateTimeField(auto_now_add=True)
       updated_at = models.DateTimeField(auto_now=True)
   ```

   *"Supplier" over "Vendor"* — both are correct English for this; I'd use Supplier because it's the term this industry and this app's own UI (that placeholder text) already reach for, and it pairs naturally with the existing "Customer" concept: Customers are who you sell to, Suppliers are who you buy from.

   Keeping it inside `apps.catalog` rather than a new `apps.suppliers` app is the deliberate small choice here — a new Django app means a new entry in `INSTALLED_APPS`, its own migrations root, its own `urls.py`, and more surface for something to be wired up wrong. A supplier is fundamentally about *restocking inventory*, which is what `catalog` already owns. If this ever grows into a full accounts-payable module (see "What I'd leave for later" below), splitting it into its own app at that point is a clean, mechanical move — not a reason to over-build today.

2. **One new nullable field on `StockMovement`:**

   ```python
   supplier = models.ForeignKey(
       Supplier, on_delete=models.PROTECT, null=True, blank=True, related_name="stock_movements"
   )
   ```

   `PROTECT`, matching how `StockMovement.product` already behaves — you can deactivate a supplier (`is_active=False`, exactly how products are archived rather than deleted) but not delete one with purchase history under it, for the same reason you can't delete a product that's been sold: it would silently rewrite the past.

   It's only ever set for `STOCK_IN` movements; every other movement type (`sale`, `return`, `adjustment`, `damage`, `opening`) simply leaves it null, the same way `cost_price_paise` on that model is already "optional — used for stock-in valuation" with no database rule forcing the connection. That's an application-level convention already established on this exact model — this follows it rather than inventing a new one.

That's the entire schema change. **Sale, Payment, Checkout, Quotations, Khata — none of them are touched, referenced, or at any risk.** This is as close to zero-disturbance as a new feature gets, because it's genuinely additive to one corner of one existing table.

## API surface

- `SupplierViewSet` — plain CRUD, `IsOwnerOrManagerOrReadOnly` (the same permission class already used for `Product`/`Category`). Suppliers are business data a cashier has no reason to edit.
- `StockInSerializer` gets one new optional field: `supplier` (a `PrimaryKeyRelatedField`, same pattern as `product` on that same serializer). Nothing required — anyone who ignores the new field keeps working exactly as before.
- `StockMovementSerializer` gains `supplier` / `supplier_name` as read fields, mirroring how it already resolves `product_sku`/`product_name`.
- **The "which supplier supplied which product at what price" view doesn't need a new endpoint.** `StockMovementViewSet` already exists and is filterable — add `supplier` to its filter fields, and a supplier's purchase history is just `GET /api/movements/?supplier=<id>&movement_type=stock_in`, already carrying product, qty, cost price, and date per row. Reusing what's there instead of building a parallel "purchase history" endpoint is the efficient version of this ask.

## Frontend

- **A new "Suppliers" page**, in the sidebar near Products/Customers, owner/manager only (matching who's already allowed to record stock-in). Structurally a near-copy of `CustomersPage.tsx`: a searchable list, a create/edit modal, and a detail dialog that's really just the `StockMovementViewSet` query above rendered as a table — the same "history dialog" shape already built for `CustomerHistoryModal`.
- **`StockInModal.tsx`** (the existing "+Stock" dialog) gets one new optional field: a supplier picker, using the same `<Select options={suppliers.map(...)} />` component already used for the category picker in `ProductModal.tsx` — not a new UI pattern, the one that's already there. The `reference` field stays exactly as it is today (a PO number is still a useful thing to record alongside *who* the supplier was, not instead of it).
- i18n keys added to both `en`/`ur` in `translations.ts`, following the pattern from the last round of work.

## What I'd deliberately leave for later

- **Backfilling supplier data onto historical `StockMovement` rows** from the existing free-text `reference` field — that's error-prone text-guessing, not a real migration, and I wouldn't trust an automated pass at it. Old rows simply have `supplier = null`, which is the honest answer ("we didn't record this before"), not a wrong one.
- **Accounts payable** — a supplier-side mirror of the Khata/credit-ledger system (tracking money *you* owe *them* on stock bought on credit). It's a very natural v2 once Suppliers exist, and the model above doesn't foreclose it. But it's real additional scope the client didn't ask for, and building it speculatively now is exactly the kind of thing worth not doing on a budget this tight.

## One thing worth saying out loud, founder to founder

This request came in *after* the 80k engagement was already scoped and committed. It's a good, reasonable ask — the kind that makes the system genuinely more useful, and worth delivering well since the client raising it themselves is a sign they're engaged and thinking about how they'll actually run the shop on this. Whether it's a quick goodwill add-on inside the existing number or a small, clearly-scoped extra is entirely your call to make with him — I'd just make it a conscious decision rather than something that quietly expands the original commitment. The design above is sized to be a short, contained piece of work either way: one model, one column, one page, one modal field.

---

**Estimated shape of the work**, if you'd like me to build it: one migration, the four backend touch-points above, one new page + one modal edit on the frontend, translations, and a short test pass covering the new model and the extended `stock_in` flow — all following the exact patterns already in this codebase, so it should read like it was always part of it rather than bolted on.
