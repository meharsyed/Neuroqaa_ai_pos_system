# Neuroqaa POS — Claude Code Project Instructions

> Read this file at the start of every session. It contains all the context, commands, and rules needed to work effectively on this codebase.

---

## Project Overview

**Neuroqaa POS** — a dual-mode Point of Sale system built by Neuroqaa.ai.

- **Owner/founder:** Mehar Syed (Neuroqaa.ai startup)
- **Target market:** Retail shops in Quetta, Balochistan, Pakistan (sanitary & tiles shops initially)
- **Deployment modes:** Desktop (Tauri + SQLite, offline) and Cloud/SaaS (Django + PostgreSQL)
- **Current state: Phase 4 complete** — full POS cycle operational

For full context see [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5 + DRF + simplejwt |
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui |
| Desktop DB | SQLite (`config.settings.desktop`) |
| Cloud DB | PostgreSQL (`config.settings.dev` / `cloud`) |
| Server state | TanStack Query |
| UI state | Zustand (persisted to localStorage) |
| Forms | react-hook-form + zod |
| PDF receipts | ReportLab 4.2.5 |
| Thermal printing | python-escpos 3.1 (optional import) |

---

## Start Commands

### Backend (run every session — env var resets on new terminal)
```powershell
cd "d:\Neuroqaa Stuff\POS System\pos-system-GT\backend"
.\venv311\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
python manage.py migrate
python manage.py runserver
```

### Frontend
```powershell
cd "d:\Neuroqaa Stuff\POS System\pos-system-GT\frontend"
npm run dev
```

App runs at **http://localhost:5173**. Backend at **http://localhost:8000**.

### Run Tests
```powershell
# Backend (venv active, DJANGO_SETTINGS_MODULE set)
pytest -v

# Frontend type check
cd frontend && npm run type-check
```

---

## Critical Rules — Never Break These

### 1. Money is always integer paise
- `1 Rs = 100 paise`
- All DB columns: `BigIntegerField`, never `FloatField` or `DecimalField`
- Backend display: `Money(paise)` from `apps.catalog.money`
- Frontend display: `paiseToRupees(paise)` from `@/lib/catalog`
- User input in Rs → multiply by 100 before API: `Math.round(parseFloat(val) * 100)`

### 2. StockMovement is append-only
- `save()` raises `ValueError` if pk exists (updates forbidden)
- `delete()` always raises `ValueError`
- To correct: create a compensating movement (opposite sign qty)

### 3. `create_sale()` is the only way to create a Sale
- In `backend/apps/sales/services.py`
- Sorts product_ids → deadlock prevention
- `SELECT FOR UPDATE` → oversell guard
- `transaction.atomic()` → all-or-nothing
- Never use `Sale.objects.create()` directly

### 4. Always set `DJANGO_SETTINGS_MODULE` explicitly
- `config.settings.desktop` → SQLite (local dev, offline, tests)
- `config.settings.dev` → PostgreSQL (cloud dev)
- `config.settings.cloud` → PostgreSQL from `DATABASE_URL` env var (production)
- Never import `config.settings.base` directly

### 5. CSV export uses `?export=csv`, not `?format=csv`
- DRF intercepts `?format=` for content negotiation → 404 before view runs
- Backend: `request.query_params.get("export") == "csv"`
- Frontend: `&export=csv` in URL, never `&format=csv`

### 6. `SettingViewSet` has `pagination_class = None`
- Settings are a small fixed dataset; always returns flat array, not paginated
- Frontend `configApi.settings.list()` expects `Setting[]`, not `PaginatedResponse<Setting>`

### 7. `shiftsApi.list()` returns paginated response
- `ShiftViewSet` uses default pagination
- Frontend unwraps `.results` from the paginated response

### 8. `GET /api/shifts/current/` returns 404 when no shift is open
- This is expected behavior, not an error
- Frontend uses `retry: false` on this query

---

## Django Apps

| App | Path | Purpose |
|---|---|---|
| `accounts` | `backend/apps/accounts/` | Custom User model, JWT auth views |
| `catalog` | `backend/apps/catalog/` | Product, Category, Inventory, StockMovement |
| `sales` | `backend/apps/sales/` | Sale, SaleItem, Payment, Shift + services + reports + receipts |
| `config` | `backend/apps/config/` | DB-backed shop settings (key/value) |

All apps registered in `LOCAL_APPS` in `backend/config/settings/base.py`.

---

## API Base URLs

All API endpoints are under `/api/`. Backend runs on `http://localhost:8000`.

| Resource | URL prefix |
|---|---|
| Auth | `/api/auth/` |
| Products, Categories, Inventory | `/api/` (catalog app router) |
| Sales, Shifts, Reports | `/api/` (sales app router + manual paths) |
| Settings | `/api/settings/` |
| Admin | `/admin/` |
| Swagger | `/api/docs/` |

---

## Frontend Pages & Routes

| Route | Page | Purpose |
|---|---|---|
| `/dashboard` | `DashboardPage.tsx` | Stats, quick actions, recent sales, shift widget |
| `/checkout` | `CheckoutPage.tsx` | Keyboard-first POS (F2/F3/F9/F12) |
| `/products` | `ProductsPage.tsx` | Catalogue + stock-in dialog |
| `/reports` | `ReportsPage.tsx` | Daily/range/inventory reports + CSV export |
| `/shifts` | `ShiftsPage.tsx` | Open/close shifts, variance summary |
| `/settings` | `SettingsPage.tsx` | Shop settings (role-gated) |
| `/login` | `LoginPage.tsx` | JWT login, split animated layout |

All protected routes are under `ProtectedLayout` which handles the sidebar nav and auth redirect.

---

## Frontend Key Files

| File | Purpose |
|---|---|
| `src/lib/axios.ts` | Axios instance + JWT interceptor (silent refresh on 401) |
| `src/lib/catalog.ts` | `catalogApi`, `paiseToRupees`, `rupeesToPaise` |
| `src/lib/sales.ts` | `salesApi` (list, create, void) |
| `src/lib/shifts.ts` | `shiftsApi` (list paginated, current, open, close) |
| `src/lib/reports.ts` | `reportsApi`, `downloadCsv()`, `openReceiptPdf()`, `printReceipt()` |
| `src/lib/config.ts` | `configApi` (flat settings list, update by key) |
| `src/store/authStore.ts` | Zustand: `{ user, access, refresh, isAuthenticated, setAuth, logout }` |
| `src/types/sales.ts` | `CartItem` (has `discount_pct` + `discount_paise`), `Sale`, `Shift` |
| `src/types/catalog.ts` | `Product` (stock_qty/low_stock_threshold are strings from API) |
| `src/index.css` | HSL CSS variables, `bg-dot-grid`, `glass`, `btn-shimmer` utilities |
| `tailwind.config.js` | Custom animations: `float`, `glow-pulse`, `fade-up`, `fade-in-scale` |

---

## Checkout Page — Cart Discount Logic

The checkout has two levels of discount, both in percent:

**Per-item discount (`discount_pct`):**
```typescript
discount_paise = Math.round(qty × unit_price_paise × discount_pct / 100)
line_total = qty × unit_price_paise - discount_paise
```

**Bill-level discount (`saleDiscountPct`):**
```typescript
bill_discount_paise = Math.round(net_subtotal × bill_pct / 100)
total = net_subtotal - bill_discount_paise
```

`CartItem.discount_pct` drives `CartItem.discount_paise`. Whenever qty changes, `discount_paise` must be recomputed from `discount_pct`. Never update `discount_paise` directly without also updating `discount_pct`.

---

## Receipts

- **Text:** `/api/sales/{id}/receipt/text/` → plain-text string
- **PDF:** `/api/sales/{id}/receipt/pdf/` → 80mm ReportLab PDF (authenticated Blob URL, not direct `<a href>`)
- **Thermal print:** `/api/sales/{id}/receipt/print/` → ESC/POS via network; returns 503 if `python-escpos` not installed
- Printer IP/port come from `get_setting("thermal_printer_ip")` and `get_setting("thermal_printer_port")`

---

## Settings (DB-backed)

Default settings seeded in migration `0002_default_settings`:
`shop_name`, `shop_address`, `shop_phone`, `shop_email`, `receipt_header`, `receipt_footer`, `receipt_width`, `thermal_printer_ip`, `thermal_printer_port`, `tax_pct`, `low_stock_threshold`

Access in backend: `get_setting("key", default="")` from `apps.config.utils`.

---

## Multi-Tenancy (Future)

Every business model has `tenant_id = models.IntegerField(default=1)`. Currently all data is tenant 1. Do not remove this field.

---

## User Roles

`owner` | `manager` | `cashier` | `stock_clerk`

- Void sales, update settings: owner/manager only
- Create sales, manage shifts: cashier and above
- Stock-in: stock_clerk and above

---

## Phases Completed

| Phase | What was built |
|---|---|
| 1 | Django + DRF skeleton, User model, JWT, React SPA + route guards |
| 2 | Products, Categories, Inventory, StockMovement, barcode lookup, CSV import/export |
| 3 | Cart UI, keyboard-first checkout (F2/F3/F9/F12), atomic sale creation, payment modal, void sales |
| 4 | ESC/POS + PDF receipts, daily/range/inventory reports, CSV export, shift management, shop settings |

---

## Branding & UI Guidelines

- **Company:** Neuroqaa.ai — branding must appear in sidebar footer, login page, dashboard footer
- **Tagline:** "Modern POS for Modern Businesses"
- **Design:** Professional, clean, non-technical users; avoid overly complex UI that slows billing
- **Primary color:** `hsl(231 70% 55%)` (blue-indigo)
- **Sidebar:** Dark gradient (`from-slate-900 via-blue-950 to-indigo-900`) with dot-grid overlay
- **Animations:** Use `animate-fade-up`, `animate-fade-in-scale` for page entrance; `animate-float` for decorative blobs

---

## Common Pitfalls

1. **Backend fails to start with PostgreSQL error** → `$env:DJANGO_SETTINGS_MODULE` not set. Set it to `config.settings.desktop`.
2. **CSV export 404** → Using `?format=csv` instead of `?export=csv`. DRF intercepts `?format=`.
3. **Settings endpoint returns paginated shape** → `SettingViewSet` must have `pagination_class = None`.
4. **Shift current 404 in console** → Expected; means no shift is open. Not an error.
5. **`CartItem.discount_paise` stale after qty change** → Always recompute: `computeItemDiscountPaise(newQty, unit_price_paise, discount_pct)`.
6. **`product.stock_qty` and `product.low_stock_threshold` are strings** in the `Product` type (API returns them as strings). Parse with `parseInt()` or `parseFloat()` before numeric comparisons.
7. **New app not loading** → Must add to `LOCAL_APPS` in `base.py` AND add `path("api/", include(...))` in `config/urls.py`.
8. **Migrations not run** → Run `python manage.py migrate` after any new app or model change.
