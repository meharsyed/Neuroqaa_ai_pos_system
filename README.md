# Neuroqaa POS System

A dual-mode Point of Sale system built by **[Neuroqaa.ai](https://neuroqaa.ai)** — runs as a native desktop app (Tauri/SQLite) and as a cloud SaaS (PostgreSQL).

> **Current state: Phase 4 complete.** Full POS cycle operational — product catalogue, checkout, receipts, shift management, reports, and settings.

---

## What this system is

Neuroqaa POS is a Point of Sale platform for retail shops, initially targeting sanitary and tiles shops in Quetta, Balochistan, Pakistan. It is designed for two deployment modes:

- **Desktop mode** — bundled as a Tauri native app with SQLite, works fully offline. Ideal for shops without reliable internet.
- **Cloud/SaaS mode** — the same Django backend on a cloud host using PostgreSQL. Multi-tenant-ready (`tenant_id` on every business model).

---

## Phases completed

| Phase | What was built |
|---|---|
| 1 — Foundation | Django + DRF skeleton, custom User model, JWT auth, React SPA + route guards, CI/CD |
| 2 — Catalogue | Products, Categories, Inventory, Stock Movements, barcode lookup, import/export CSV |
| 3 — Checkout | Cart UI, keyboard-first checkout (F2/F3/F9/F12), atomic sale creation, payment modal, void sales |
| 4 — Operations | ESC/POS + PDF receipts, daily/range/inventory reports, CSV export, shift open/close + cash reconciliation, shop settings |

---

## Stack

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
| PDF receipts | ReportLab |
| Thermal printing | python-escpos (network mode) |
| CI | GitHub Actions |

---

## Project structure

```
pos-system-GT/
├── backend/
│   ├── apps/
│   │   ├── accounts/          Custom User model, JWT auth views
│   │   ├── catalog/           Product, Category, Inventory, StockMovement
│   │   ├── sales/             Sale, SaleItem, Payment, Shift + services
│   │   └── config/            Setting model (shop config key/value store)
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py        Shared settings (never import directly)
│   │   │   ├── dev.py         PostgreSQL + debug toolbar
│   │   │   ├── desktop.py     SQLite (offline / Tauri mode)
│   │   │   └── cloud.py       PostgreSQL from DATABASE_URL (production)
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── requirements/
│   │   ├── base.txt           Core packages including reportlab + python-escpos
│   │   ├── dev.txt
│   │   └── prod.txt
│   ├── manage.py
│   └── pytest.ini
├── frontend/
│   └── src/
│       ├── pages/             LoginPage, DashboardPage, ProductsPage,
│       │                      CheckoutPage, ReportsPage, ShiftsPage, SettingsPage
│       ├── layouts/           ProtectedLayout (sidebar), CheckoutLayout (fullscreen)
│       ├── components/
│       │   ├── ui/            Button, Input, Label, Badge, Select (shadcn-style)
│       │   └── checkout/      PaymentModal
│       ├── lib/               axios.ts, catalog.ts, sales.ts, config.ts,
│       │                      reports.ts, shifts.ts
│       ├── store/             authStore.ts (Zustand)
│       ├── types/             auth.ts, catalog.ts, sales.ts, config.ts
│       └── router/            index.tsx
├── docs/
│   ├── PROJECT_CONTEXT.md     ← Full system context for AI assistants & developers
│   ├── setup-and-testing.md   Phase 1 detailed setup guide
│   └── adr/
│       └── 0001-stack-selection.md
└── docker-compose.yml
```

---

## Quick start (local — no Docker)

### Terminal 1 — Django backend

```powershell
cd "d:\Neuroqaa Stuff\POS System\pos-system-GT\backend"
.\venv311\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
python manage.py migrate
python manage.py createsuperuser   # use email + password you'll remember
python manage.py runserver
```

### Terminal 2 — React frontend

```powershell
cd "d:\Neuroqaa Stuff\POS System\pos-system-GT\frontend"
npm install   # first time only
npm run dev
```

Open **http://localhost:5173** and sign in with the superuser credentials.

> **First-time setup only:** After starting, go to `/admin/` and add at least one Category and one Product with stock before testing checkout.

---

## Running tests

```powershell
# Backend (with venv active, DJANGO_SETTINGS_MODULE set)
pytest -v

# Frontend type check
cd frontend && npm run type-check
```

---

## API endpoints (Phase 4)

### Auth
| Method | URL | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/login/` | — | Returns `{ access, refresh, user }` |
| POST | `/api/auth/refresh/` | — | Rotate refresh token |
| GET | `/api/auth/me/` | Bearer | Current user |

### Catalogue
| Method | URL | Auth | Description |
|---|---|---|---|
| GET/POST | `/api/products/` | Bearer | List / create products |
| GET/PATCH | `/api/products/{id}/` | Bearer | Retrieve / update |
| GET | `/api/products/low-stock/` | Bearer | Products below threshold |
| GET | `/api/products/barcode/{barcode}/` | Bearer | Barcode lookup |
| POST | `/api/products/import/` | Bearer | Bulk CSV import |
| GET/POST | `/api/categories/` | Bearer | Categories |
| GET | `/api/inventory/` | Bearer | Inventory levels |
| POST | `/api/inventory/stock-in/` | Bearer | Add stock |

### Sales
| Method | URL | Auth | Description |
|---|---|---|---|
| POST | `/api/sales/` | Bearer | Create atomic sale |
| GET | `/api/sales/` | Bearer | List sales |
| GET | `/api/sales/{id}/` | Bearer | Sale detail |
| POST | `/api/sales/{id}/void/` | Bearer (owner/mgr) | Void sale |
| GET | `/api/sales/{id}/receipt/text/` | Bearer | Plain-text receipt |
| GET | `/api/sales/{id}/receipt/pdf/` | Bearer | PDF receipt (ReportLab) |
| POST | `/api/sales/{id}/receipt/print/` | Bearer | Send to thermal printer |

### Shifts
| Method | URL | Auth | Description |
|---|---|---|---|
| POST | `/api/shifts/` | Bearer | Open shift |
| GET | `/api/shifts/` | Bearer | List shifts |
| GET | `/api/shifts/current/` | Bearer | Current open shift (404 if none) |
| POST | `/api/shifts/{id}/close/` | Bearer | Close shift → variance summary |

### Reports
| Method | URL | Auth | Description |
|---|---|---|---|
| GET | `/api/reports/daily/?date=YYYY-MM-DD` | Bearer | Daily summary JSON |
| GET | `/api/reports/daily/?date=...&export=csv` | Bearer | Daily summary CSV download |
| GET | `/api/reports/date-range/?start=...&end=...` | Bearer | Multi-day summary |
| GET | `/api/reports/inventory/` | Bearer | Inventory valuation JSON |
| GET | `/api/reports/inventory/?export=csv` | Bearer | Inventory valuation CSV |

### Settings
| Method | URL | Auth | Description |
|---|---|---|---|
| GET | `/api/settings/` | Bearer | All shop settings |
| GET | `/api/settings/{key}/` | Bearer | Single setting |
| PATCH | `/api/settings/{key}/` | Bearer (owner/mgr) | Update setting value |

### Admin & docs
| URL | Description |
|---|---|
| `/admin/` | Django admin (session auth) |
| `/api/docs/` | Swagger UI |
| `/api/schema/` | OpenAPI 3.1 JSON |

---

## Key architectural rules (do not break these)

1. **Money is always stored as integer paise.** `1 Rs = 100 paise`. Never use FloatField for money. Use `Money(paise)` from `apps.catalog.money` to format for display.
2. **`StockMovement` is append-only.** Its `save()` raises `ValueError` if the record already has a PK. Never call `delete()` on one.
3. **`create_sale()` is the only way to create a Sale.** It sorts product_ids before locking (deadlock prevention), aggregates qty per product (oversell guard), and wraps everything in `transaction.atomic()`.
4. **Settings module is never imported directly.** Always use a concrete settings file (`dev`, `desktop`, or `cloud`). Set `DJANGO_SETTINGS_MODULE` explicitly.
5. **CSV export uses `?export=csv` (not `?format=csv`).** DRF intercepts `?format=` for its own content negotiation — using `format` as a parameter name causes a 404.

---

## Architecture decisions

See [docs/adr/](docs/adr/) for full Architecture Decision Records.

- [ADR 0001 — Stack Selection](docs/adr/0001-stack-selection.md)

For complete system context (all phases, every file, patterns, gotchas) see [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md).

---

*Built by [Neuroqaa.ai](https://neuroqaa.ai) — Modern POS for Modern Businesses.*