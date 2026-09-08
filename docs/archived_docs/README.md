# Archived Documentation

This folder contains historical and deprecated documentation kept for reference but no longer actively used or maintained.

## Archive Contents

### Demo & Store-Specific (Not Reusable)
- **CCTV_DATABASE_SETUP.md** — Database setup for CCTV store demo
- **CCTV_STORE_COMPLETE_GUIDE.md** — Complete guide for CCTV store demo
- **KIDS_POSHAK_THEME_GUIDE.md** — Kids Poshak clothing store theme demo

### Old UI/Dashboard Proposals (Superseded)
- **DASHBOARD_REDESIGN_PROPOSAL.md** — Initial dashboard redesign proposal
- **DASHBOARD_REDESIGN_SUMMARY.md** — Summary of dashboard redesign work
- **DASHBOARD_TESTING_GUIDE.md** — Testing guide for redesigned dashboard

### Completed Implementation Phases (Duplicates)
- **PHASE_8A_COMPLETION_SUMMARY.md** — Phase 8A summary (see PHASE_8_RECEIPTS_AND_UX.md)
- **PHASE_8B_STATUS.md** — Phase 8B status update (see PHASE_8_RECEIPTS_AND_UX.md)

### Old Implementation & Setup Guides (Superseded)
- **FEATURE_SUMMARY.md** — Old feature list (now outdated)
- **IMPLEMENTATION_GUIDE.md** — Old implementation guide (replaced by RUN_AND_TEST.md)
- **USER_GUIDE.md** — Old user manual (superseded)
- **DEVELOPER_CHECKLIST.md** — Old developer checklist (no longer used)
- **PRODUCT_IMAGES_IMPLEMENTATION.md** — Old product image implementation notes

### Old Testing & QA Guides (Superseded)
- **RECEIPT_QA_TESTING_GUIDE.md** — Old QA testing guide
- **RECEIPT_TEMPLATES_GUIDE.md** — Old receipt template documentation
- **RECEIPT_TEMPLATES_UI_TESTING.md** — Old receipt UI testing guide

## Why Archived?

These documents were important during development but became outdated because:
- ✅ **Superseded** by newer, more comprehensive documentation in the parent `/docs` folder
- ✅ **Demo-specific** (CCTV store, Kids Poshak theme) — not generalizable to future deployments
- ✅ **Historical** — documented completed phases; see active PHASE_N docs instead
- ✅ **Replaced** by better guides (e.g., `setup-and-testing.md` → `RUN_AND_TEST.md`)

## If You Need Them

All files are preserved in git history for reference:

```bash
# List what files were archived
git log --oneline --all -- docs/archived_docs/

# Recover a specific file
git show <commit>:docs/archived_docs/<filename>

# Search archived content
git log -p --all -- docs/archived_docs/ | grep "search_term"
```

## Active Documentation

For current, maintained documentation, see:
- `/docs/PROJECT_CONTEXT.md` — Full project overview
- `/docs/PHASE_*.md` — Completed implementation phases
- `/docs/PHASE_13_SECURITY_FIXES.md` — Current security phase
- `/docs/PHASE_14_SUPPLIERS_FEATURE.md` — Current feature work
- `/docs/RUN_AND_TEST.md` — How to run the app
- `/docs/DEPLOYMENT_ARCHITECTURE.md` — Production deployment

---

**Archive created:** 2026-09-08  
**Last reviewed:** 2026-09-08
