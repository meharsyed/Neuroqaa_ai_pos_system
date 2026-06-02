# Neuroqaa POS — Complete Project Context

> **For AI assistants and developers.** This file is the single authoritative context document for the Neuroqaa POS system. Read this before making any changes. It covers every app, every pattern, every gotcha, and the reasoning behind key decisions.

---

## 1. Business Context

**Product:** Neuroqaa POS — a dual-mode Point of Sale system.  
**Company:** Neuroqaa.ai (founder: Mehar Syed). This is a commercial product aimed at retail shops in Quetta, Balochistan, Pakistan, starting with sanitary and tiles shops.  
**Deployment modes:**
- **Desktop (offline):** Tauri native app + SQLite. Works without internet. Ideal for shops with unreliable connectivity.
- **Cloud/SaaS:** Same Django backend on a VPS/cloud host with PostgreSQL. Multi-tenant-ready.

**Current state: Phase 4 complete.** Full POS cycle is operational.

---

## 2. Phases Completed

| Phase | What was built |
|---|---|
| 1 — Foundation | Django + DRF skeleton, custom User model, JWT auth, React SPA, route guards, GitHub Actions CI |
| 2 — Catalogue | Products, Categories, Inventory, StockMovement, barcode lookup, CSV import/export |
| 3 — Checkout | Cart UI, keyboard-first checkout (F2/F3/F9/F12), atomic sale creation, payment modal, void sales |
| 4 — Operations | ESC/POS + PDF receipts, daily/range/inventory reports, CSV export, shift open/close + cash reconciliation, DB-backed shop settings |

---

## 3. Stack

| Layer | Technology |
|---|---|
| Backend API | Django 5 + Django REST Framework + simplejwt |
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui |
| Desktop shell | Tauri (Rust) — future phase |
| Desktop DB | SQLite (`config.settings.desktop`) |
| Cloud DB | PostgreSQL 16 (`config.settings.dev` / `cloud`) |
| Server state | TanStack Query (React Query) |
| UI state | Zustand (persisted to localStorage) |
| Forms | react-hook-form + zod |
| PDF receipts | ReportLab 4.2.5 |
| Thermal printing | python-escpos 3.1 (optional, graceful fallback) |
| CI | GitHub Actions (`.github/workflows/ci.yml`) |

---

## 4. Project Structure

```
pos-system-GT/
├── backend/
│   ├── apps/
│   │   ├── accounts/          Custom User model, JWT auth views
│   │   │   ├── models.py      User(AbstractBaseUser) — email as USERNAME_FIELD
│   │   │   ├── views.py       LoginView, TokenRefreshView, MeView
│   │   │   ├── serializers.py UserSerializer, LoginSerializer
│   │   │   └── urls.py        /auth/login/, /auth/refresh/, /auth/me/
│   │   ├── catalog/           Product, Category, Inventory, StockMovement
│   │   │   ├── models.py      See §6.2 for invariants
│   │   │   ├── money.py       Money(paise) display helper
│   │   │   ├── views.py       ProductViewSet, CategoryViewSet, InventoryViewSet
│   │   │   └── urls.py        /products/, /categories/, /inventory/
│   │   ├── sales/             Sale, SaleItem, Payment, Shift + services
│   │   │   ├── models.py      Sale, SaleItem, Payment, Shift
│   │   │   ├── services.py    create_sale(), open_shift(), close_shift()
│   │   │   ├── reports.py     daily_summary(), date_range_summary(), inventory_valuation(), CSV helpers
│   │   │   ├── receipts.py    render_text_receipt(), render_pdf_receipt(), print_receipt_network()
│   │   │   ├── views.py       SaleViewSet, ShiftViewSet, report_daily, report_date_range, report_inventory
│   │   │   ├── serializers.py SaleSerializer, ShiftSerializer, OpenShiftSerializer, CloseShiftSerializer
│   │   │   └── urls.py        router + manual report paths
│   │   └── config/            DB-backed shop settings (key/value)
│   │       ├── models.py      Setting(key, value, label, description)
│   │       ├── utils.py       get_setting(key, default) helper
│   │       ├── views.py       SettingViewSet — pagination_class = None
│   │       ├── serializers.py SettingSerializer — key/label/description read-only
│   │       └── migrations/    0001_initial + 0002_default_settings (11 defaults seeded)
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py        Shared (never import directly). LOCAL_APPS includes all 4 apps.
│   │   │   ├── dev.py         PostgreSQL + debug toolbar. Use for cloud dev.
│   │   │   ├── desktop.py     SQLite. Use for local / Tauri.
│   │   │   └── cloud.py       PostgreSQL from DATABASE_URL env var. Production only.
│   │   ├── urls.py            Routes: /api/auth/, /api/ (catalog), /api/ (sales), /api/ (config), /admin/, /api/docs/
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── requirements/
│   │   ├── base.txt           djangorestframework, simplejwt, reportlab, python-escpos, drf-spectacular
│   │   ├── dev.txt            debug-toolbar, pytest-django, factory-boy
│   │   └── prod.txt           gunicorn, psycopg2-binary
│   ├── manage.py
│   └── pytest.ini             DJANGO_SETTINGS_MODULE = config.settings.desktop
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── LoginPage.tsx          Split-layout login with animated left panel
│       │   ├── DashboardPage.tsx      Stat cards, quick actions, recent sales, shift widget
│       │   ├── ProductsPage.tsx       Product catalogue with stock-in dialog
│       │   ├── CheckoutPage.tsx       Keyboard-first POS (F2/F3/F9/F12), PDF/print buttons
│       │   ├── ReportsPage.tsx        Daily / Date Range / Inventory tabs + CSV export
│       │   ├── ShiftsPage.tsx         Open/close shifts, variance summary, shift history
│       │   └── SettingsPage.tsx       Grouped settings editor, role-based save buttons
│       ├── layouts/
│       │   ├── ProtectedLayout.tsx    Sidebar nav (grouped), auth guard, branding
│       │   └── CheckoutLayout.tsx     Fullscreen layout for checkout
│       ├── components/
│       │   ├── ui/                    Button, Input, Label, Badge, Select (shadcn-style)
│       │   └── checkout/
│       │       └── PaymentModal.tsx   Payment method + amount modal
│       ├── lib/
│       │   ├── axios.ts               Axios instance (baseURL=/api), JWT interceptor (silent refresh on 401)
│       │   ├── catalog.ts             catalogApi — products, categories, inventory
│       │   ├── sales.ts               salesApi — list, get, void, receipt endpoints
│       │   ├── shifts.ts              shiftsApi — list (paginated), current, open, close
│       │   ├── reports.ts             reportsApi — daily, dateRange, inventory; downloadCsv(); openReceiptPdf(); printReceipt()
│       │   ├── config.ts              configApi — settings list, update
│       │   └── utils.ts               cn() Tailwind class merger
│       ├── store/
│       │   └── authStore.ts           Zustand store: { user, access, refresh, isAuthenticated, setAuth, logout }
│       ├── types/
│       │   ├── auth.ts                User, LoginCredentials, LoginResponse
│       │   ├── catalog.ts             Product, Category, Inventory, StockMovement
│       │   ├── sales.ts               Sale, SaleItem, Payment, Shift, ShiftCloseResult
│       │   └── config.ts              Setting, DailySummary, DateRangeSummary, InventoryValuation
│       ├── router/
│       │   └── index.tsx              Routes: / → /dashboard, /login, /dashboard, /products, /checkout, /reports, /shifts, /settings
│       ├── main.tsx                   React root, QueryClientProvider, BrowserRouter
│       ├── App.tsx                    Root component (renders Router)
│       └── index.css                  CSS variables (HSL palette), dot-grid, glass, btn-shimmer utilities
├── docs/
│   ├── PROJECT_CONTEXT.md     ← This file
│   ├── setup-and-testing.md   Phase 1 detailed setup guide
│   └── adr/
│       └── 0001-stack-selection.md
├── docker-compose.yml         PostgreSQL + Redis (for cloud dev)
└── README.md                  Quick start, API reference, architectural rules
```

---

## 5. Quick Start (No Docker)

### Backend

```powershell
cd "d:\Neuroqaa Stuff\POS System\pos-system-GT\backend"
.\venv311\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
python manage.py migrate
python manage.py createsuperuser   # email + password
python manage.py runserver
```

### Frontend

```powershell
cd "d:\Neuroqaa Stuff\POS System\pos-system-GT\frontend"
npm install   # first time only
npm run dev
```

Open **http://localhost:5173**. Sign in with superuser credentials.

**First time only:** Go to `/admin/` and add at least one Category and one Product with stock before testing checkout.

---

## 6. Critical Architectural Rules

These rules exist for correctness/safety reasons. Breaking them causes silent data corruption or runtime errors.

### 6.1 Money is always integer paise

- `1 Rs = 100 paise`
- All database columns for money use `BigIntegerField`, never `FloatField` or `DecimalField`.
- Backend display: `Money(paise)` from `apps.catalog.money` — returns `"Rs 1,234.50"` formatted string.
- Frontend display: `paiseToRupees(paise)` from `@/lib/catalog` — returns `"Rs 1,234.50"`.
- User input (e.g., opening float, closing cash): user types in Rupees, multiply by 100 before sending to API. Example in ShiftsPage: `rupeesToPaise(value) = Math.round(parseFloat(value) * 100)`.

### 6.2 StockMovement is append-only

- `StockMovement.save()` raises `ValueError` if the record already has a PK (i.e., updates are forbidden).
- `StockMovement.delete()` always raises `ValueError`.
- To correct a movement: create a compensating movement (positive qty to reverse a negative, or vice versa).
- This preserves audit trail integrity.

### 6.3 `create_sale()` is the only way to create a Sale

Located in `backend/apps/sales/services.py`. It:
1. Sorts `product_ids` before locking — prevents deadlocks when concurrent sales lock the same products.
2. Aggregates qty per product — detects oversell before any writes.
3. Wraps everything in `transaction.atomic()` — all-or-nothing.
4. Creates a UUID placeholder sale first, then updates `sale_number` to `SALE-YYYYMMDD-NNNNN` format.

Never call `Sale.objects.create(...)` directly from a view.

### 6.4 Settings module is never imported directly

Always import a concrete settings file. Set `DJANGO_SETTINGS_MODULE` explicitly in every shell session:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"   # local
$env:DJANGO_SETTINGS_MODULE = "config.settings.dev"        # cloud dev
$env:DJANGO_SETTINGS_MODULE = "config.settings.cloud"      # production
```

`config.settings.base` is a shared base — never set `DJANGO_SETTINGS_MODULE` to it.

### 6.5 CSV export uses `?export=csv`, not `?format=csv`

DRF reserves the `?format=` query parameter (`URL_FORMAT_OVERRIDE = 'format'`) for its own content negotiation. When DRF sees `?format=csv` and no CSV renderer is registered, it intercepts the request and returns `{"detail": "Not found."}` (HTTP 404) **before your view code runs**.

**Fix:** Always use `?export=csv`. Both the backend views and frontend call sites use this parameter name.

Backend:
```python
if request.query_params.get("export") == "csv":
    ...
```

Frontend (`reports.ts`):
```typescript
downloadCsv(`/reports/daily/?date=${date}&export=csv`, `daily-${date}.csv`)
```

---

## 7. Authentication

### User model

`apps.accounts.models.User` extends `AbstractBaseUser`:
- `USERNAME_FIELD = "email"` (no username field)
- `role` field: `owner` / `manager` / `cashier` / `stock_clerk`
- `first_name`, `last_name`, `is_active`, `is_staff`, `is_superuser`
- `tenant_id = IntegerField(default=1)` — reserved for future multi-tenancy

### JWT flow

- Login: `POST /api/auth/login/` → `{ access, refresh, user }`
- Access token TTL: 30 minutes
- Refresh token TTL: 7 days
- Silent refresh: Axios response interceptor in `frontend/src/lib/axios.ts` — on 401, tries `POST /api/auth/refresh/`, replaces access token in Zustand store, retries original request. If refresh fails, calls `logout()`.

### Role-based access

| Role | Permissions |
|---|---|
| `owner` | All operations including void, settings update, shift management |
| `manager` | Same as owner except some admin-only operations |
| `cashier` | Create sales, open/close shifts, view reports |
| `stock_clerk` | Catalogue read/write, inventory stock-in; no sales |

In `SettingsPage.tsx`, save buttons are disabled if `user.role !== "owner" && user.role !== "manager"`.

---

## 8. API Reference

### Auth — `/api/auth/`

| Method | URL | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/login/` | — | Returns `{ access, refresh, user }` |
| POST | `/api/auth/refresh/` | — | Rotate refresh token |
| GET | `/api/auth/me/` | Bearer | Current user |

### Catalogue — `/api/`

| Method | URL | Auth | Description |
|---|---|---|---|
| GET/POST | `/api/products/` | Bearer | List / create products |
| GET/PATCH | `/api/products/{id}/` | Bearer | Retrieve / update |
| GET | `/api/products/low-stock/` | Bearer | Products below `low_stock_threshold` |
| GET | `/api/products/barcode/{barcode}/` | Bearer | Barcode lookup |
| POST | `/api/products/import/` | Bearer | Bulk CSV import |
| GET/POST | `/api/categories/` | Bearer | Categories |
| GET | `/api/inventory/` | Bearer | Inventory levels |
| POST | `/api/inventory/stock-in/` | Bearer | Add stock (creates StockMovement) |

### Sales — `/api/`

| Method | URL | Auth | Description |
|---|---|---|---|
| POST | `/api/sales/` | Bearer | Create atomic sale via `create_sale()` |
| GET | `/api/sales/` | Bearer | List sales (paginated) |
| GET | `/api/sales/{id}/` | Bearer | Sale detail |
| POST | `/api/sales/{id}/void/` | Bearer (owner/mgr) | Void sale + reverse stock |
| GET | `/api/sales/{id}/receipt/text/` | Bearer | Plain-text receipt |
| GET | `/api/sales/{id}/receipt/pdf/` | Bearer | PDF receipt (ReportLab, 80mm) |
| POST | `/api/sales/{id}/receipt/print/` | Bearer | Send to ESC/POS thermal printer |

### Shifts — `/api/`

| Method | URL | Auth | Description |
|---|---|---|---|
| POST | `/api/shifts/` | Bearer | Open shift (`open_shift()` service) |
| GET | `/api/shifts/` | Bearer | List shifts (paginated) |
| GET | `/api/shifts/current/` | Bearer | Current open shift — 404 if none |
| POST | `/api/shifts/{id}/close/` | Bearer | Close shift → variance summary |

### Reports — `/api/`

| Method | URL | Auth | Description |
|---|---|---|---|
| GET | `/api/reports/daily/?date=YYYY-MM-DD` | Bearer | Daily summary JSON |
| GET | `/api/reports/daily/?date=...&export=csv` | Bearer | Daily summary CSV download |
| GET | `/api/reports/date-range/?start=...&end=...` | Bearer | Multi-day summary |
| GET | `/api/reports/inventory/` | Bearer | Inventory valuation JSON |
| GET | `/api/reports/inventory/?export=csv` | Bearer | Inventory valuation CSV |

### Settings — `/api/`

| Method | URL | Auth | Description |
|---|---|---|---|
| GET | `/api/settings/` | Bearer | All shop settings (flat array, no pagination) |
| GET | `/api/settings/{key}/` | Bearer | Single setting by key string |
| PATCH | `/api/settings/{key}/` | Bearer (owner/mgr) | Update `value` field only |

### Admin & Docs

| URL | Description |
|---|---|
| `/admin/` | Django admin |
| `/api/docs/` | Swagger UI (drf-spectacular) |
| `/api/schema/` | OpenAPI 3.1 JSON |

---

## 9. Key Models

### Product (`apps.catalog`)
```
id, sku (unique), name, description, category FK,
price_paise (BigInt), cost_paise (BigInt),
barcode (unique nullable), unit (pcs/sqft/meter/kg/liter),
stock_qty (Int), low_stock_threshold (Int, default 5),
is_active (Bool), tenant_id (Int, default 1)
```

### StockMovement (`apps.catalog`)
```
id, product FK, quantity (Int, positive=in, negative=out),
movement_type (stock_in/sale/void/adjustment),
reference (CharField, e.g. sale number),
created_by FK(User), created_at, tenant_id
```
**Append-only.** `save()` and `delete()` raise `ValueError` if pk exists.

### Sale (`apps.sales`)
```
id (UUID), sale_number (SALE-YYYYMMDD-NNNNN),
cashier FK(User), shift FK(Shift, nullable),
subtotal_paise, discount_paise, total_paise (all BigInt),
status (completed/voided), void_reason, voided_by FK,
created_at, tenant_id
```

### SaleItem (`apps.sales`)
```
id, sale FK, product FK, product_name (snapshot),
qty (Int), unit_price_paise, discount_pct (Int 0-100),
line_total_paise (BigInt)
```

### Payment (`apps.sales`)
```
id, sale FK(unique — one payment per sale currently),
method (cash/card/credit/mobile_wallet),
amount_paise (BigInt), received_paise (BigInt), change_paise (BigInt)
```

### Shift (`apps.sales`)
```
id, cashier FK(User),
opened_at (auto), closed_at (nullable),
opening_float_paise (BigInt), closing_cash_paise (BigInt nullable),
notes, closing_notes, tenant_id
```

### Setting (`apps.config`)
```
id, key (unique, max 100), value (TextField),
label (human-readable name), description (help text)
```

Default settings seeded in migration `0002`:
- `shop_name`, `shop_address`, `shop_phone`, `shop_email`
- `receipt_header`, `receipt_footer`, `receipt_width`
- `thermal_printer_ip`, `thermal_printer_port`
- `tax_pct`, `low_stock_threshold`

---

## 10. Frontend Architecture

### State management

- **Server state:** TanStack Query (`useQuery`, `useMutation`). Query keys follow `["resource", filters]` pattern.
- **Auth state:** Zustand store at `src/store/authStore.ts`. Persisted to `localStorage` under key `"pos-auth"`. Contains `{ user, access, refresh, isAuthenticated }`.
- **Form state:** react-hook-form + zodResolver for all forms.

### Axios setup (`src/lib/axios.ts`)

- `baseURL = "http://localhost:8000/api"` (dev). In production: `import.meta.env.VITE_API_URL`.
- Request interceptor: attaches `Authorization: Bearer <access>` from Zustand store.
- Response interceptor: on 401, calls `/auth/refresh/`, updates store, retries original request. On refresh failure, calls `logout()` and redirects to `/login`.

### Routing (`src/router/index.tsx`)

```
/ → redirect to /dashboard
/login → LoginPage (no auth required)
/dashboard → DashboardPage  } all under ProtectedLayout
/products → ProductsPage    } (redirects to /login if not authenticated)
/checkout → CheckoutPage    }
/reports → ReportsPage      }
/shifts → ShiftsPage        }
/settings → SettingsPage    }
```

### Type conventions

- All API response types live in `src/types/`. Match Django serializer field names exactly.
- Paginated responses: `PaginatedResponse<T>` = `{ count, next, previous, results: T[] }`.
- Date/time: ISO strings from API. `new Date(iso).toLocaleString("en-PK", ...)` for display.

### UI conventions

- All money displayed via `paiseToRupees(paise)` from `@/lib/catalog`.
- All user inputs for money: user enters Rupees, convert with `Math.round(parseFloat(val) * 100)` before API call.
- Loading states: TanStack Query's `isLoading` / `isPending`.
- Error states: `onError` in `useMutation`, `serverError` state variable.
- Tables: plain `divide-y` dividers on `div` containers, not `<table>` elements.

---

## 11. CSS / Design System

### Color palette (`src/index.css`)

Primary: `hsl(231 70% 55%)` (blue-indigo). All other colors via CSS HSL variables (`--background`, `--foreground`, `--muted`, `--border`, etc.). Dark mode is supported via `class` strategy but not yet wired up.

### Custom utilities

- **`bg-dot-grid`**: Radial dot pattern background overlay (used in sidebar header and login left panel).
- **`glass`**: Frosted glass effect (`backdrop-blur + bg-white/10 + border-white/15`).
- **`btn-shimmer`**: `::after` pseudo-element sweep animation on hover (used on Login submit button).

### Animations (tailwind.config.js)

| Class | Effect |
|---|---|
| `animate-float` | Vertical bobbing 7s loop |
| `animate-float-slow` | Same, 10s, 2s delay |
| `animate-float-reverse` | Reverse direction, 8s |
| `animate-glow-pulse` | Box-shadow pulse 3s loop |
| `animate-fade-up` | Fade + slide up 0.5s |
| `animate-fade-up-delay-1/2/3/4` | Same with 0.1/0.2/0.3/0.4s delays |
| `animate-fade-in-scale` | Fade + scale-in 0.4s |

Stagger pattern: apply `animate-fade-up` to top element, `animate-fade-up-delay-1` to next, etc. for cascaded entrance animation.

### Component library

shadcn/ui style components in `src/components/ui/`. Currently: `Button`, `Input`, `Label`, `Badge`, `Select`. Badge variants: `default`, `secondary`, `destructive`, `outline`, `success`, `warning`.

---

## 12. Services Deep Dive

### `create_sale(cashier, items, payment_method, payment_amount_paise, received_paise, shift_id, discount_paise)`

1. Extracts `product_ids = [item["product_id"] for item in items]`
2. Sorts product_ids ascending — deterministic lock order prevents deadlocks
3. `transaction.atomic()`:
   - `SELECT ... FOR UPDATE` on all products in sorted id order
   - Validates stock for each product (raises `ValueError` on oversell)
   - Creates `Sale` with UUID placeholder
   - Creates `SaleItem` for each line
   - Creates `StockMovement` (negative qty, type=`sale`) for each product
   - Updates product `stock_qty`
   - Creates `Payment`
   - Updates sale `sale_number` to `SALE-YYYYMMDD-NNNNN` (padded sequential)
4. Returns the `Sale` instance

### `open_shift(cashier, opening_float_paise, notes)`

Simple `Shift.objects.create(...)`. No business logic beyond the model.

### `close_shift(shift, closing_cash_paise, closing_notes)`

1. Raises `ValueError` if `shift.closed_at is not None` (already closed)
2. Queries completed sales on this shift for revenue total and count
3. Queries cash payment totals specifically
4. Computes: `expected_cash = opening_float + cash_sales_total`
5. Computes: `variance = closing_cash - expected_cash`
6. Updates shift fields and saves with `update_fields`
7. Returns variance summary dict

### `daily_summary(date)` → DailySummary

Aggregates completed sales for the given date: total_revenue_paise, total_discount_paise, transaction_count, payment_breakdown (by method), top_products (top 10 by revenue).

### `inventory_valuation()` → list

Returns all active products with: current stock_qty, cost_paise, price_paise, stock_value_paise (qty × cost), retail_value_paise (qty × price).

---

## 13. Receipt System

### Text receipt (`render_text_receipt(sale)`)

Returns a plain-text string with shop header (from `get_setting("shop_name")`, etc.), item lines, totals, payment info, footer. Used for simple display.

### PDF receipt (`render_pdf_receipt(sale)`)

Uses ReportLab. Paper width: 227pt (80mm thermal roll). Returned as `bytes`. Streaming `HttpResponse` with `Content-Type: application/pdf`. The download URL (`/api/sales/{id}/receipt/pdf/`) requires Bearer auth — frontend fetches with `apiClient.get(..., { responseType: "blob" })` then creates a Blob URL for `window.open()`.

### Thermal printing (`print_receipt_network(sale, ip, port)`)

Uses python-escpos `Network` printer. If `python-escpos` is not installed, import fails silently and the view returns a 503 JSON error. Printer IP/port come from `get_setting("thermal_printer_ip")` and `get_setting("thermal_printer_port")`.

---

## 14. Multi-Tenancy

Every business model has `tenant_id = models.IntegerField(default=1)`. Currently all data is tenant 1. When multi-tenancy is implemented:
- Add middleware to extract `tenant_id` from the JWT payload or subdomain.
- Add `.filter(tenant_id=request.tenant_id)` to all querysets.
- The `default=1` means existing data is automatically tenant 1 and nothing breaks during the upgrade.

---

## 15. Running Tests

```powershell
# Backend — from backend/ with venv active and DJANGO_SETTINGS_MODULE set
pytest -v

# Frontend type check
cd frontend && npm run type-check

# Frontend unit tests (Vitest)
cd frontend && npm run test
```

Backend test configuration: `pytest.ini` sets `DJANGO_SETTINGS_MODULE = config.settings.desktop` (SQLite — no external DB needed for tests).

---

## 16. Environment Variables

### Backend

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | Yes | `config.settings.desktop` / `dev` / `cloud` |
| `SECRET_KEY` | In cloud | Django secret key (auto-generated in dev) |
| `DATABASE_URL` | In cloud | PostgreSQL DSN (cloud.py reads this) |
| `ALLOWED_HOSTS` | In cloud | Comma-separated hostnames |

### Frontend

| Variable | Description |
|---|---|
| `VITE_API_URL` | Backend base URL (default: `http://localhost:8000/api`) |

---

## 17. Common Gotchas

1. **`?format=csv` returns 404** — DRF intercepts it. Always use `?export=csv`. See §6.5.

2. **`/api/shifts/current/` returns 404 when no shift is open** — this is intentional behavior, not an error. The frontend handles this with `retry: false` in the query options.

3. **Settings list returns flat array, not paginated** — `SettingViewSet` has `pagination_class = None`. If you add pagination back, update the frontend `configApi.settings.list()` to unwrap `.results`.

4. **Shifts list is paginated** — `shiftsApi.list()` returns `PaginatedResponse<Shift>` and the component accesses `.results`.

5. **python-escpos is an optional dependency** — `receipts.py` catches `ImportError` and the `receipt/print/` view returns HTTP 503 with `{"error": "thermal printing not configured"}` if the library is missing. Don't remove the try/except.

6. **ReportLab is not optional** — it's in `base.txt` and the PDF view will 500 if it's missing. Ensure it's installed.

7. **Migrations must be run on fresh checkout** — both `accounts`, `catalog`, `sales`, and `config` apps have migrations. Run `python manage.py migrate` before first run.

8. **`open_shift` does not prevent multiple open shifts** — the current implementation allows a cashier to open multiple shifts without closing the previous one. The UI warns about this but doesn't enforce it at the API level. If you need enforcement, add a `UniqueConstraint` on `(cashier, closed_at=None)` or check in the service.

9. **Sale `shift` FK is nullable** — sales can be created without an open shift. The checkout page does not require a shift to be open (only recommended).

10. **Superuser role defaults to `owner`** — the `createsuperuser` command creates a User with `is_superuser=True`. Set `role="owner"` manually in admin or migration data if needed for role-based permission checks.

---

## 18. AI Assistant Quick Reference

When working on this codebase, these are the most important things to remember:

**Money:** Always paise (BigInt). Never float. `paiseToRupees()` for display. Multiply by 100 for storage.

**Stock:** Never delete or update StockMovement records. Use compensating entries.

**Sales:** Always use `create_sale()` service. Never direct `Sale.objects.create()`.

**Settings:** Always `$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"` before running backend commands.

**CSV export:** `?export=csv` not `?format=csv`. DRF intercepts `?format=`.

**Settings API:** Returns flat array (no pagination). `SettingViewSet.pagination_class = None`.

**Shifts API:** Returns paginated response. Unwrap `.results` in frontend.

**Shift current:** 404 = no open shift (expected). Not an application error.

**PDF receipts:** Fetched via authenticated Axios call, not direct `<a href>` link.

**New app checklist:**
1. Create `apps/newapp/__init__.py`, `apps.py`, `models.py`, `views.py`, `urls.py`, `serializers.py`, `migrations/`
2. Add to `LOCAL_APPS` in `config/settings/base.py`
3. Add `path("api/", include("apps.newapp.urls"))` in `config/urls.py`
4. Add `tenant_id = models.IntegerField(default=1)` to every business model
5. Run `python manage.py makemigrations newapp && python manage.py migrate`

**New frontend page checklist:**
1. Create `src/pages/NewPage.tsx`
2. Add route in `src/router/index.tsx` under `ProtectedLayout`
3. Add nav item in `src/layouts/ProtectedLayout.tsx` `NAV_SECTIONS`
4. Add API calls to appropriate `src/lib/*.ts` file
5. Add TypeScript types to `src/types/*.ts`

---

*This document is the single source of truth for AI assistants and new developers. Keep it updated when the architecture changes. Last updated: Phase 4 complete.*