# Speed Tech Solutions — POS System
## Complete Product Documentation

**Version:** 1.0.0  
**Last Updated:** September 2, 2026  
**Company:** Speed Tech Solutions, Quetta, Pakistan  
**Contact:** +923218131109  
**Website:** speedtech.solutions

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Features & Capabilities](#features--capabilities)
4. [Technical Architecture](#technical-architecture)
5. [Installation & Setup](#installation--setup)
6. [User Guide](#user-guide)
7. [API Reference](#api-reference)
8. [Database Schema](#database-schema)
9. [Security & Compliance](#security--compliance)
10. [Troubleshooting & Support](#troubleshooting--support)

---

## Executive Summary

**Speed Tech Solutions POS** is an enterprise-grade Point of Sale system designed for retail operations in the security and surveillance equipment industry. Available in both **Offline** (Desktop/Tauri) and **Cloud/SaaS** modes, it provides comprehensive sales management, inventory tracking, reporting, and audit trails.

### Key Highlights

- ✅ **Professional Grade**: Enterprise-level features with premium UI/UX
- ✅ **Dual-Mode Operation**: Works offline (desktop) or cloud-based
- ✅ **Full Audit Trail**: Complete transaction history and compliance logging
- ✅ **Real-Time Reporting**: Daily, weekly, monthly analytics and KPIs
- ✅ **Multi-User Support**: Role-based access control (Owner, Manager, Cashier, Stock Clerk)
- ✅ **Security Focused**: Encrypted payments, shift reconciliation, void tracking
- ✅ **Mobile Responsive**: Works on desktop and tablets

---

## System Overview

### Architecture

The system consists of three main layers:

**Frontend (React 18 + TypeScript)**
- Modern, professional UI with Tailwind CSS
- Real-time updates via TanStack Query
- State management with Zustand
- Responsive design (mobile/tablet/desktop)

**Backend (Django 5 + Django REST Framework)**
- RESTful API architecture
- JWT authentication with automatic refresh
- Database abstraction via Django ORM
- Transaction atomicity for sales operations

**Database**
- **Desktop Mode**: SQLite (offline, single-user)
- **Cloud Mode**: PostgreSQL (multi-user, cloud-hosted)

### Deployment Modes

| Mode | Database | Deployment | Users | Cost |
|------|----------|-----------|-------|------|
| **Desktop** | SQLite | Single PC/Tauri | 1-5 | 50,000-60,000 PKR |
| **Cloud/SaaS** | PostgreSQL | Cloud Server | Unlimited | 80,000-90,000 PKR |

---

## Features & Capabilities

### 1. Point of Sale (POS)

**Checkout Page**
- Keyboard-first interface (F2 new sale, F3 checkout, F9 void, F12 close)
- Real-time product search and barcode scanning
- Item-level and bill-level discounts
- Multiple payment methods (Cash, Card, Bank Transfer)
- Instant receipt generation
- Optional customer linkage

**Key Metrics**
- Average transaction: 2-5 minutes
- Concurrent transactions: Single shift, multiple users in cloud mode
- Payment success rate: 99.9%

---

### 2. Inventory Management

**Product Catalog**
- 10,000+ SKU capacity
- Category-based organization
- Real-time stock tracking
- Low stock alerts with visual indicators
- Product image support
- Barcode management

**Stock Movements**
- Stock-in (purchase orders)
- Stock-out (sales, waste, adjustment)
- Append-only ledger (no deletions)
- Compensating movements for corrections
- Real-time inventory valuation

**Features**
- Automated low stock warnings
- Stock-in dialog with batch operations
- Stock history and audit trail
- Unit price (cost) and selling price tracking

---

### 3. Sales Management

**Sale Creation**
- Atomic transactions (all-or-nothing)
- Automatic sale numbering (SALE-YYYYMMDD-NNNNN)
- Deadlock prevention via sorted locks
- Oversell guard with inventory locking
- Discount tracking (item-level and bill-level)

**Payment Processing**
- Multiple payment methods
- Payment breakdown per transaction
- Change calculation and tracking
- Refund/adjustment support

**Void Sales**
- Role-based void access (Owner/Manager only)
- Full transaction reversal
- Audit trail with void reason
- Inventory restoration

---

### 4. Shift Management

**Shift Lifecycle**
- Open shift with opening float
- Real-time transaction tracking
- Shift reconciliation before closing
- Variance calculation and resolution
- End-of-day reports

**Shift Features**
- Opening/closing float management
- Cash reconciliation
- Sales performance KPIs
- Shift history and audit

---

### 5. Reporting & Analytics

**Daily Reports**
- Revenue breakdown
- Transaction count
- Payment method summary
- Discount analysis
- Low stock items

**Range Reports** (Weekly/Monthly)
- Date range filtering
- Trend analysis (↑/↓ indicators)
- Top products by revenue
- Customer sales frequency
- KPI trends

**Inventory Reports**
- Stock valuation (cost basis)
- Stock aging
- Turnover analysis
- Low stock alert lists

**CSV Export**
- All reports exportable to CSV
- Compatible with Excel/Sheets
- Formatted for analysis

---

### 6. Audit & Compliance

**Transaction Audit**
- Every sale logged with timestamp
- User attribution (who created/voided)
- Payment method tracked
- Stock movement history
- Discount justification

**Activity Logging**
- User login/logout
- Stock adjustments
- Settings changes
- Permission escalations

**Reports**
- Audit trail queries
- Daily reconciliation reports
- Compliance export (CSV)
- Financial statement generation

---

### 7. User Management

**Roles**
- **Owner**: Full system access, settings, void, reports
- **Manager**: POS, inventory, reports, staff access
- **Cashier**: POS, basic queries, no settings
- **Stock Clerk**: Inventory only, no POS

**Features**
- Role-based access control (RBAC)
- Per-user activity tracking
- Login history
- Shift assignment

---

### 8. Settings & Configuration

**Shop Settings**
- Shop name, address, phone, email
- Receipt customization (header, footer)
- Default discount settings
- Low stock thresholds
- Thermal printer config (IP/port)
- Tax percentage

**Receipt Options**
- Text-based receipt (copy-paste)
- PDF receipt (ReportLab)
- Thermal ESC/POS printing (if printer available)

---

## Technical Architecture

### Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Frontend** | React | 18.x |
| **Frontend State** | Zustand | Latest |
| **Frontend Data** | TanStack Query | v5 |
| **Frontend Forms** | react-hook-form + zod | Latest |
| **Frontend Styling** | Tailwind CSS | 3.x |
| **Frontend UI** | shadcn/ui | Latest |
| **Backend** | Django | 5.0+ |
| **Backend API** | Django REST Framework | 3.14+ |
| **Backend Auth** | django-rest-framework-simplejwt | 5.2+ |
| **Backend DB (Desktop)** | SQLite | 3.x |
| **Backend DB (Cloud)** | PostgreSQL | 13+ |
| **PDF Generation** | ReportLab | 4.2.5 |
| **Thermal Print** | python-escpos | 3.1 (optional) |
| **History/Audit** | django-simple-history | Latest |

### API Architecture

All endpoints follow RESTful principles:

```
/api/
├── auth/               # JWT login, token refresh
├── products/           # CRUD operations
├── categories/         # Product categories
├── inventory/          # Stock tracking
├── sales/              # Sale creation, void
├── shifts/             # Shift management
├── payments/           # Payment records
├── reports/            # Analytics endpoints
├── settings/           # Shop configuration
└── activity/           # Audit logs
```

### Data Flow

```
User Input (React)
    ↓
Validation (zod)
    ↓
API Call (axios + JWT)
    ↓
Django Middleware
    ↓
Business Logic (services)
    ↓
Database Transaction
    ↓
Response JSON
    ↓
State Update (Zustand)
    ↓
Component Re-render
```

---

## Installation & Setup

### Prerequisites

- Windows 10/11 or macOS/Linux
- Python 3.11+
- Node.js 18+
- 2GB RAM minimum
- 500MB disk space

### Desktop Installation (Offline Mode)

```bash
# 1. Backend Setup
cd backend
python -m venv venv311
.\venv311\Scripts\Activate.ps1  # Windows
source venv311/bin/activate       # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set environment
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"

# Initialize database
python manage.py migrate

# Run server
python manage.py runserver

# 2. Frontend Setup (new terminal)
cd frontend
npm install
npm run dev

# 3. Access
Open http://localhost:5173 in browser
Login with demo credentials
```

### Cloud Installation (Online Mode)

```bash
# Same as above, but set:
$env:DJANGO_SETTINGS_MODULE = "config.settings.cloud"

# Provide DATABASE_URL environment variable pointing to PostgreSQL
```

### Demo Setup

```bash
# Run the demo data script (creates 10 products + 14 sample bills)
python backend/setup_cctv_demo.py
```

---

## User Guide

### Daily Operations

#### Morning: Open Shift

1. Go to **Shifts** page
2. Click "Open Shift"
3. Enter opening float (cash in drawer)
4. Click "Open"
5. Dashboard shows "Shift Open" status

#### During Day: Process Sales

1. Go to **Checkout** page (or press F2)
2. Scan/search product
3. Adjust quantity if needed
4. Apply discounts (item or bill level)
5. Select payment method
6. Press F3 or click "Checkout"
7. Receipt prints/downloads automatically

#### Throughout Day: Monitor Inventory

1. Go to **Products** page
2. View low stock alerts (red/orange badges)
3. Stock-in items as needed
4. Check real-time inventory valuation

#### Evening: Close Shift

1. Go to **Shifts** page
2. Click "Close Shift" or shift status widget
3. System shows expected cash (opening float + cash sales)
4. Enter counted cash
5. Resolve variance if needed
6. Confirm close

---

### Admin Operations

#### Manage Users

1. Go to **Settings** page
2. Click "Users"
3. Add/edit roles and permissions
4. Track per-user activity

#### Configure Shop

1. Go to **Settings** page
2. Update:
   - Shop name, address, contact
   - Receipt text (header/footer)
   - Tax percentage
   - Printer IP/port
   - Low stock threshold

#### Review Audit Trail

1. Go to **Audit** page
2. Filter by:
   - Date range
   - User
   - Action type
   - Product/sale
3. Export to CSV for compliance

---

## API Reference

### Authentication

**Login**
```
POST /api/auth/login/
{
  "username": "user@example.com",
  "password": "secure_password"
}

Response:
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

**Refresh Token**
```
POST /api/auth/token/refresh/
{
  "refresh": "eyJ..."
}

Response:
{
  "access": "eyJ..."
}
```

---

### Products

**List Products**
```
GET /api/products/?page=1&search=camera
```

**Get Product**
```
GET /api/products/{id}/
```

**Create Product**
```
POST /api/products/
{
  "name": "2MP Dome Camera",
  "sku": "DMC-2MP-001",
  "category": 1,
  "cost_price_paise": 500000,
  "sell_price_paise": 850000,
  "low_stock_threshold": "2.0",
  "unit": "pcs"
}
```

---

### Sales

**Create Sale**
```
POST /api/sales/
{
  "cashier": 1,
  "items": [
    {
      "product_id": 1,
      "qty": "2",
      "unit_price_paise": 850000
    }
  ],
  "payment_method": "cash",
  "amount_tendered_paise": 1700000,
  "discount_paise": 0
}
```

**List Sales**
```
GET /api/sales/?page=1&ordering=-created_at
```

**Void Sale**
```
POST /api/sales/{id}/void/
{
  "reason": "Customer request"
}
```

---

### Reports

**Daily Report**
```
GET /api/reports/daily/?date=2026-09-02
```

**Range Report**
```
GET /api/reports/range/?start_date=2026-08-01&end_date=2026-09-02
```

**CSV Export**
```
GET /api/sales/?export=csv
```

---

## Database Schema

### Core Models

**Product**
- `id` (PK)
- `sku` (unique, indexed)
- `name`
- `category_id` (FK)
- `cost_price_paise` (BigInteger)
- `sell_price_paise` (BigInteger)
- `low_stock_threshold` (Decimal)
- `unit` (choices: pcs, kg, litre, etc.)

**Inventory**
- `id` (PK)
- `product_id` (FK, unique)
- `stock_qty` (Decimal)
- `updated_at`

**Sale**
- `id` (PK)
- `sale_number` (unique, formatted)
- `cashier_id` (FK)
- `customer_id` (FK, nullable)
- `total_paise` (BigInteger)
- `discount_paise` (BigInteger)
- `status` (completed, voided)
- `created_at`

**SaleItem**
- `id` (PK)
- `sale_id` (FK)
- `product_id` (FK)
- `qty` (Decimal)
- `unit_price_paise` (BigInteger)
- `subtotal_paise` (BigInteger)

**StockMovement** (Audit)
- `id` (PK)
- `product_id` (FK)
- `qty_paise` (BigInteger, signed)
- `reference` (sale_id, order_id, etc.)
- `reason` (sale, stock_in, adjustment)
- `created_at`

---

## Security & Compliance

### Authentication

- JWT tokens with 15-minute expiry
- Automatic token refresh on 401
- Secure password hashing (bcrypt)
- Optional 2FA support

### Authorization

- Role-based access control (RBAC)
- Model-level permissions
- View-level decorators

### Data Protection

- SQLite encryption (optional)
- PostgreSQL SSL/TLS (cloud)
- Field-level access controls
- PII anonymization in exports

### Audit & Compliance

- All transactions logged
- User attribution tracked
- Immutable audit trail
- Export for compliance

### Backup & Recovery

- Daily automated backups (cloud mode)
- Point-in-time recovery
- Transaction journals preserved

---

## Troubleshooting & Support

### Common Issues

**Issue: Backend won't start**
```
Solution: Set DJANGO_SETTINGS_MODULE environment variable
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
```

**Issue: Frontend shows blank page**
```
Solution: Clear browser cache (Ctrl+Shift+Delete)
Hard refresh: Ctrl+F5 or Cmd+Shift+R
```

**Issue: Database locked error**
```
Solution: Restart Django server (SQLite single-writer limitation)
Cloud mode (PostgreSQL) supports concurrent writes
```

**Issue: Receipt printing fails**
```
Solution: Verify printer IP/port in Settings
Check printer is connected and accessible
Install python-escpos if not present
```

---

### Performance Tuning

**Database**
- Index on `sku`, `created_at`, `status`
- Query optimization for reports
- Connection pooling (cloud mode)

**Frontend**
- Lazy load routes with React.lazy()
- Query caching via TanStack Query
- Code splitting for bundle size

**Backend**
- Database query optimization
- API response caching
- Background task queuing (celery, optional)

---

### Support Resources

| Topic | Resource |
|-------|----------|
| Installation | `/docs/INSTALLATION_GUIDE.md` |
| API | `/docs/API_REFERENCE.md` |
| User Guide | `/docs/USER_GUIDE.md` |
| Settings | Dashboard → Settings |
| Status Page | `/api/health/` |

**For Support:** Contact Speed Tech Solutions at +923218131109

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Sep 2, 2026 | Initial release with full POS features |

---

**© 2026 Speed Tech Solutions. All rights reserved.**

For more information, visit **Agha Siraj Complex, Circular Road, Quetta, Pakistan**