# Django Configuration & Security Keys Setup Guide

**Date:** 2026-09-08  
**Purpose:** Complete guide to setting up Django environment variables and security keys

---

## Part 1: Django SECRET_KEY & Security Configuration

### What is SECRET_KEY?

Django's `SECRET_KEY` is a cryptographic secret used for:
- **Session encryption** — secure session cookies
- **CSRF tokens** — cross-site request forgery protection
- **Password reset links** — time-limited, single-use tokens
- **Signing serialized objects** — cache, sessions, etc.

### Why It Matters

- ✅ **Must be random** — use cryptographic randomness, not guesses
- ✅ **Must be unique** — different keys for dev, staging, production
- ✅ **Must be kept secret** — never commit to git, never share
- ✅ **Must be 50+ characters** — longer = harder to crack

### Current Configuration

Your `.env` file has been updated with a secure key:

```bash
SECRET_KEY=Wc!6e1Q49j-!x9J(=!Evn8n=SW_cGG7P%F-_hbjcXS^$G9!3oj
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,backend,127.0.0.1:8000
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### How Keys Were Generated

A script at `scripts/generate_django_keys.py` creates cryptographically secure keys:

```powershell
cd backend
.\venv311\Scripts\Activate.ps1
python ..\scripts\generate_django_keys.py
```

This outputs:
1. **SECRET_KEY** (50 chars) — for Django
2. **JWT_SECRET** (64 chars) — optional, for JWT signing (uses SECRET_KEY by default)
3. **Database password** (20 chars) — for PostgreSQL production

### Environment Variables Explained

| Variable | Value | Purpose | Dev? | Prod? |
|---|---|---|---|---|
| `SECRET_KEY` | Random 50+ chars | Django session/CSRF/etc | ✅ Required | ✅ Required |
| `DEBUG` | True/False | Show error details | ✅ True | ❌ False |
| `ALLOWED_HOSTS` | Domain list | Prevent Host header attacks | ✅ localhost | ✅ yourdomain.com |
| `CORS_ALLOWED_ORIGINS` | URL list | XSS prevention | ✅ http://localhost:5173 | ✅ https://yourdomain.com |
| `POSTGRES_*` | DB credentials | Database connection | Dev: SQLite | ✅ Required |

### For Production Deployment

**Important:** Before deploying to production, generate NEW keys:

```powershell
python ..\scripts\generate_django_keys.py
```

Then create a `.env.production` file with:

```bash
# ────────────────────────────────────────────────────────────────────────────────
# PRODUCTION ENVIRONMENT (.env.production)
# ────────────────────────────────────────────────────────────────────────────────

# SECURITY - Generate new keys, never reuse dev keys
SECRET_KEY=<generate-new-key-with-script>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# CORS - Set to exact frontend domain
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# DATABASE - PostgreSQL in production
POSTGRES_DB=pos_production
POSTGRES_USER=pos_user
POSTGRES_PASSWORD=<generate-new-20-char-password>
POSTGRES_HOST=your-rds-endpoint.amazonaws.com
POSTGRES_PORT=5432

# THERMAL PRINTER (if used)
THERMAL_PRINTER_IP=192.168.1.100
THERMAL_PRINTER_PORT=9100
```

Store this in a **secrets manager** (AWS Secrets Manager, HashiCorp Vault, etc.), NOT in git.

### Django Settings Files

The app uses environment-based settings:

```
backend/config/settings/
├── base.py          # Shared settings
├── desktop.py       # SQLite (local dev, offline)
├── dev.py           # PostgreSQL (cloud development)
└── cloud.py         # PostgreSQL (production, strict checks)
```

**To use desktop (local SQLite):**
```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
python manage.py runserver
```

**To use cloud (PostgreSQL):**
```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.cloud"
python manage.py runserver
```

---

## Part 2: Documentation Cleanup & Organization

### What Was Done

Organized 41 markdown files across the repository:

**Before:**
```
repo/
├── docs/               (23 files - mixed active and historical)
├── CCTV_*.md          (old demo docs in root)
├── DASHBOARD_*.md     (old proposal docs in root)
├── PHASE_8*.md        (old phase summaries in root)
├── RECEIPT_*.md       (old testing guides in root)
└── ... (18 total in root)
```

**After:**
```
repo/
├── docs/
│   ├── PHASE_13_SECURITY_FIXES.md      (current)
│   ├── PHASE_13_IMPLEMENTATION_SUMMARY.md (current)
│   ├── PHASE_14_SUPPLIERS_FEATURE.md   (current)
│   ├── DEPLOYMENT_ARCHITECTURE.md      (current)
│   ├── SECURITY_AUDIT.md               (current)
│   ├── PROJECT_CONTEXT.md              (reference)
│   ├── RUN_AND_TEST.md                 (how-to)
│   ├── PHASE_7-12_*.md                 (historical)
│   ├── [Feature docs]                  (reference)
│   └── archived_docs/                  (historical, preserved)
│       ├── README.md
│       ├── CCTV_*.md
│       ├── DASHBOARD_*.md
│       └── ... (16 archived files)
├── CLAUDE.md          (root - project instructions)
└── README.md          (root - repo readme)
```

### Files Archived (16 Total)

**Demo-Specific:**
- CCTV_DATABASE_SETUP.md
- CCTV_STORE_COMPLETE_GUIDE.md
- KIDS_POSHAK_THEME_GUIDE.md

**Old Proposals (Superseded):**
- DASHBOARD_REDESIGN_PROPOSAL.md
- DASHBOARD_REDESIGN_SUMMARY.md
- DASHBOARD_TESTING_GUIDE.md

**Old Phase Summaries (Duplicates):**
- PHASE_8A_COMPLETION_SUMMARY.md
- PHASE_8B_STATUS.md

**Old Guides (Replaced):**
- FEATURE_SUMMARY.md
- IMPLEMENTATION_GUIDE.md
- USER_GUIDE.md
- DEVELOPER_CHECKLIST.md
- PRODUCT_IMAGES_IMPLEMENTATION.md

**Old Testing Guides:**
- RECEIPT_QA_TESTING_GUIDE.md
- RECEIPT_TEMPLATES_GUIDE.md
- RECEIPT_TEMPLATES_UI_TESTING.md

### How to Run Cleanup

A script automates the archival:

```powershell
cd "D:\Neuroqaa Stuff\POS System\pos-system-GT"

# Dry run (see what would be moved)
.\scripts\cleanup_docs.ps1 -DryRun

# Execute cleanup
.\scripts\cleanup_docs.ps1
```

### Benefits

✅ **Cleaner navigation** — docs/ shows only active, relevant files  
✅ **Clear history** — archived_docs/ preserves historical context  
✅ **Easier onboarding** — new team members find current docs first  
✅ **No data loss** — everything is preserved in git history  
✅ **Future-proof** — easy to move more docs as they age

---

## Part 3: Active Documentation Structure

### Must-Read Documents

1. **CLAUDE.md** (root)
   - Project instructions, tech stack, critical rules
   - Read this first on every session

2. **PROJECT_CONTEXT.md** (/docs)
   - Full project overview, phases completed, architecture
   - Reference for understanding the app

3. **DEPLOYMENT_ARCHITECTURE.md** (/docs)
   - How to deploy to production
   - Hosting options, docker, environment setup

### Current Phase Documentation

4. **PHASE_13_SECURITY_FIXES.md** (/docs)
   - Security audit findings and fixes implemented
   - JWT cookies, token blacklist, Django upgrade

5. **PHASE_13_IMPLEMENTATION_SUMMARY.md** (/docs)
   - Test results (328 backend ✅, 28 frontend ✅)
   - Verification steps for security fixes

6. **PHASE_14_SUPPLIERS_FEATURE.md** (/docs)
   - Suppliers module implementation
   - Current feature in development

### Feature Documentation

- **KHATA_LEDGER.md** — Customer credit tracking
- **CREDIT_LIMITS_AND_SHARING.md** — Credit features
- **SPLIT_PAYMENTS.md** — Payment modes
- **FEATURE_DESIGN_SUPPLIERS.md** — Suppliers design

### How-To Guides

- **RUN_AND_TEST.md** — Running the app locally, testing
- **SECURITY_AUDIT.md** — Security findings from audit
- **ROADMAP_AUDIT.md** — Current roadmap and priorities

### Historical Reference

- **PHASE_7-12_*.md** — Completed phases (for understanding how we got here)

---

## Checklist: Setup for New Team Members

When onboarding a new developer:

- [ ] Read CLAUDE.md (project instructions)
- [ ] Read PROJECT_CONTEXT.md (project overview)
- [ ] Read DEPLOYMENT_ARCHITECTURE.md (how it's deployed)
- [ ] Read PHASE_13_SECURITY_FIXES.md (current security posture)
- [ ] Read PHASE_14_SUPPLIERS_FEATURE.md (current work)
- [ ] Run: `python scripts/generate_django_keys.py` (understand key generation)
- [ ] Run: `.\scripts\cleanup_docs.ps1 -DryRun` (see documentation organization)
- [ ] Follow RUN_AND_TEST.md (get it running locally)

---

## Quick Reference: Environment Variables

### For Local Development
```bash
SECRET_KEY=<any-50-char-random-key>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,backend
CORS_ALLOWED_ORIGINS=http://localhost:5173
POSTGRES_DB=pos_dev
POSTGRES_USER=pos_user
POSTGRES_PASSWORD=pos_password
```

### For Staging
```bash
SECRET_KEY=<generate-new-key>
DEBUG=False
ALLOWED_HOSTS=staging.yourdomain.com
CORS_ALLOWED_ORIGINS=https://staging.yourdomain.com
POSTGRES_DB=pos_staging
POSTGRES_USER=pos_user
POSTGRES_PASSWORD=<secure-20-char-password>
```

### For Production
```bash
SECRET_KEY=<generate-new-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
POSTGRES_DB=pos_production
POSTGRES_USER=pos_user
POSTGRES_PASSWORD=<secure-20-char-password>
POSTGRES_HOST=<production-rds-endpoint>
```

---

## Next Steps

1. ✅ **Security keys configured** — Updated `.env` with secure key
2. ✅ **Documentation organized** — Moved 16 old files to archived_docs/
3. ⏭️ **Commit changes** — Stage and commit these updates
4. ⏭️ **Test app** — Verify everything still works
5. ⏭️ **Plan deployment** — Use DEPLOYMENT_ARCHITECTURE.md to plan

---

## Files Created/Modified

| File | Status | Purpose |
|---|---|---|
| `backend/.env` | Modified | Updated with secure SECRET_KEY |
| `scripts/generate_django_keys.py` | Created | Key generation script |
| `scripts/cleanup_docs.ps1` | Created | Automation for documentation cleanup |
| `docs/DOCUMENTATION_AUDIT.md` | Created | Audit of all .md files |
| `docs/archived_docs/` | Created | Folder for historical docs (16 files) |
| `docs/archived_docs/README.md` | Created | Archive index and reference |
| `docs/SETUP_AND_CONFIG_GUIDE.md` | Created | This guide |

---

**Last updated:** 2026-09-08  
**Status:** ✅ Complete and documented
