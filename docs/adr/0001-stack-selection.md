# ADR-0001: Stack Selection — Django + DRF + React + Tauri

**Date:** 2026-05-14
**Status:** Accepted

## Context

We are building a POS system that must run:
1. As a native desktop application (Windows, macOS, Linux) for shops with unreliable internet
2. As a cloud-hosted SaaS for multi-branch chains

The system handles financial transactions, requires role-based access control, offline data sync, receipt printing, barcode scanning, and reporting.

## Decision

### Backend: Django 5 + Django REST Framework

**Why Django over FastAPI, Node, or Rails:**
- Django admin provides a fully functional back-office immediately (product, user, and order management) without building a separate admin UI — this is critical for a 2-person team
- `django-simple-history` gives us automatic audit logs on every model, which is a legal requirement in retail
- `django-import-export` enables CSV/Excel bulk imports that our non-technical clients need
- The ORM handles both SQLite (desktop) and PostgreSQL (cloud) with the same query code
- Mature ecosystem for auth, permissions, and background tasks (Celery)
- DRF + drf-spectacular generates OpenAPI 3.1 docs automatically — Tauri frontend consumes these

**Trade-off accepted:** Django is heavier than FastAPI for pure API throughput. For a POS system where the bottleneck is the cashier's typing speed, not HTTP throughput, this is irrelevant.

### Frontend: React 18 + Vite + TypeScript + Tailwind + shadcn/ui

**Why React over Vue or Svelte:**
- Largest ecosystem for desktop (Tauri) integrations
- TanStack Query solves the server-state/cache problem that would otherwise require custom code in every component
- shadcn/ui gives us unstyled, accessible components we own rather than a dependency we can't fork

**Why Vite over CRA/Webpack:**
- Sub-second HMR for a fast development loop
- First-class TypeScript support without config

### Desktop Shell: Tauri (not Electron)

**Why Tauri over Electron:**
- Tauri bundles are 3–10 MB vs Electron's 80–150 MB — matters for distribution to shops with slow connections
- Uses the OS WebView (WebKit/Edge) rather than shipping Chromium
- Rust backend gives us system-level access for receipt printer and barcode scanner drivers without a subprocess hack
- **Trade-off:** Tauri's ecosystem is younger; some Electron-native libraries don't exist yet

### Database Strategy: SQLite (desktop) + PostgreSQL (cloud)

- Both supported by the same Django ORM
- Desktop ships with a bundled SQLite file — zero infrastructure dependency for the shop owner
- Cloud uses Postgres for concurrent access, JSON columns, and read replicas

### Auth: JWT (djangorestframework-simplejwt)

- Stateless — works for both SPA and Tauri WebView without session cookie complexity
- Access token (30 min) + refresh token (7 days) with rotation
- Desktop extends to 8 hr access / 30 day refresh (device is local, no shared session risk)

## Consequences

- We must maintain the `config/settings/` split and test both SQLite and Postgres paths in CI
- Desktop offline sync (Phase 4) will require a sync engine — this architecture doesn't solve that yet, but it doesn't block it either
- We accept the Tauri ecosystem risk; if a critical driver doesn't exist, we can shell out to a small Rust CLI
