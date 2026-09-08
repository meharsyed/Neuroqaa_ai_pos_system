# Documentation Audit & Cleanup Plan

**Date:** 2026-09-08  
**Purpose:** Identify old, duplicate, and unused documentation for archival

---

## Summary

- **Total markdown files:** 41 (23 in `/docs`, 18 in root)
- **Files to keep in /docs:** 16 (active, current)
- **Files to move to archive:** 21 (old, superseded, demo-specific)
- **Files to keep in root:** 2 (CLAUDE.md, README.md)

---

## Active Documentation (Keep in /docs)

### Current Implementation
| File | Last Updated | Purpose | Keep? |
|---|---|---|---|
| PHASE_13_IMPLEMENTATION_SUMMARY.md | 2026-09-08 | Security fixes implementation & test results | ✅ KEEP |
| PHASE_13_SECURITY_FIXES.md | 2026-09-08 | Security audit findings & fixes | ✅ KEEP |
| PHASE_14_SUPPLIERS_FEATURE.md | 2026-09-08 | Suppliers feature implementation | ✅ KEEP |
| DEPLOYMENT_ARCHITECTURE.md | 2026-09-08 | Production deployment strategy | ✅ KEEP |
| SECURITY_AUDIT.md | 2026-09-07 | Initial security audit findings | ✅ KEEP |

### Project Reference
| File | Last Updated | Purpose | Keep? |
|---|---|---|---|
| PROJECT_CONTEXT.md | 2026-05-26 | Full project overview, tech stack, architecture | ✅ KEEP |
| PRODUCT_DOCUMENTATION.md | 2026-09-02 | Product catalog, SKU, pricing, inventory | ✅ KEEP |
| ROADMAP_AUDIT.md | 2026-09-06 | Current roadmap and planned phases | ✅ KEEP |
| RUN_AND_TEST.md | 2026-09-05 | How to run and test the app | ✅ KEEP |

### Completed Phases (Historical Reference)
| File | Last Updated | Purpose | Keep? |
|---|---|---|---|
| PHASE_12_PDF_AUTH_I18N_TESTS.md | 2026-09-06 | PDF receipts, auth, localization completion | ✅ KEEP (historical) |
| PHASE_11_QUOTATIONS_AND_POLISH.md | 2026-09-06 | Quotations feature completion | ✅ KEEP (historical) |
| PHASE_10_ROLES_TAX_WARRANTY.md | 2026-09-06 | Roles, taxes, warranty notes | ✅ KEEP (historical) |
| PHASE_9_KHATA_AND_DEMO_FIXES.md | 2026-09-05 | Khata (credit tracking) feature | ✅ KEEP (historical) |
| PHASE_8_RECEIPTS_AND_UX.md | 2026-09-04 | Receipt templates and UX polish | ✅ KEEP (historical) |
| PHASE_7_REMEDIATION.md | 2026-09-03 | Bug fixes and stability improvements | ✅ KEEP (historical) |

### Feature Documentation
| File | Last Updated | Purpose | Keep? |
|---|---|---|---|
| CREDIT_LIMITS_AND_SHARING.md | 2026-09-05 | Customer credit limits & shared accounts | ✅ KEEP |
| KHATA_LEDGER.md | 2026-09-05 | Customer credit journal (Khata) implementation | ✅ KEEP |
| SPLIT_PAYMENTS.md | 2026-09-05 | Split payment modes (cash + credit) | ✅ KEEP |
| FEATURE_DESIGN_SUPPLIERS.md | 2026-09-08 | Suppliers module design & implementation | ✅ KEEP |

### Infrastructure & Planning
| File | Last Updated | Purpose | Keep? |
|---|---|---|---|
| CLIENT_REQUESTS_PLAN.md | 2026-09-06 | Client feature requests & prioritization | ✅ KEEP |

---

## Deprecated Documentation (Archive to /archived_docs)

### Outdated Proposals & Specs (Superseded)
| File | Last Updated | Reason | Archive? |
|---|---|---|---|
| setup-and-testing.md | 2026-05-23 | Replaced by newer RUN_AND_TEST.md | 📦 ARCHIVE |
| UI_UX_REVAMP_SPEC.md | 2026-09-02 | Old UI spec; implementation complete | 📦 ARCHIVE |
| DASHBOARD_REDESIGN_PROPOSAL.md | 2026-08-27 | Old proposal; implemented and superseded | 📦 ARCHIVE |
| DASHBOARD_REDESIGN_SUMMARY.md | 2026-08-27 | Summary of old dashboard work | 📦 ARCHIVE |
| DASHBOARD_TESTING_GUIDE.md | 2026-08-27 | Testing guide for old dashboard | 📦 ARCHIVE |

### Demo/Store-Specific (Not Generalizable)
| File | Last Updated | Reason | Archive? |
|---|---|---|---|
| CCTV_DATABASE_SETUP.md | 2026-08-31 | CCTV store demo only; not reusable | 📦 ARCHIVE |
| CCTV_STORE_COMPLETE_GUIDE.md | 2026-08-31 | CCTV store demo only; not reusable | 📦 ARCHIVE |
| KIDS_POSHAK_THEME_GUIDE.md | 2026-08-29 | Kids Poshak demo theme; not current | 📦 ARCHIVE |

### Old Implementation Guides (Superseded)
| File | Last Updated | Reason | Archive? |
|---|---|---|---|
| PHASE_8A_COMPLETION_SUMMARY.md | 2026-09-04 | Old phase summary; in docs/ already | 📦 ARCHIVE |
| PHASE_8B_STATUS.md | 2026-09-04 | Old phase status; in docs/ already | 📦 ARCHIVE |
| FEATURE_SUMMARY.md | 2026-08-25 | Old feature list; now outdated | 📦 ARCHIVE |
| IMPLEMENTATION_GUIDE.md | 2026-08-25 | Old setup guide; replaced by RUN_AND_TEST.md | 📦 ARCHIVE |
| USER_GUIDE.md | 2026-08-25 | Old user manual; outdated | 📦 ARCHIVE |
| DEVELOPER_CHECKLIST.md | 2026-06-14 | Old dev checklist; no longer used | 📦 ARCHIVE |
| PRODUCT_IMAGES_IMPLEMENTATION.md | 2026-08-25 | Old implementation notes; now integrated | 📦 ARCHIVE |

### Outdated Testing Guides
| File | Last Updated | Reason | Archive? |
|---|---|---|---|
| RECEIPT_QA_TESTING_GUIDE.md | 2026-06-28 | Old QA testing; superseded by phase docs | 📦 ARCHIVE |
| RECEIPT_TEMPLATES_GUIDE.md | 2026-06-28 | Old receipt templates; implementation complete | 📦 ARCHIVE |
| RECEIPT_TEMPLATES_UI_TESTING.md | 2026-06-28 | Old testing guide; superseded | 📦 ARCHIVE |

### Potentially Useful (Keep as Reference)
| File | Last Updated | Status | Archive? |
|---|---|---|---|
| THEME_COLOR_REFERENCE.md | 2026-08-29 | Still referenced in UI; might be useful | ⚠️ REVIEW |

---

## Files to Keep in Root

| File | Reason | Action |
|---|---|---|
| CLAUDE.md | Project instructions & context; must stay in root | ✅ KEEP |
| README.md | Repository readme for GitHub; must stay in root | ✅ KEEP |

---

## Action Plan

### Step 1: Create Archive Directory
```powershell
mkdir "D:\Neuroqaa Stuff\POS System\pos-system-GT\docs\archived_docs"
```

### Step 2: Move Deprecated Files
```powershell
# Demo/store-specific docs (not reusable)
mv "CCTV_DATABASE_SETUP.md" "docs\archived_docs\"
mv "CCTV_STORE_COMPLETE_GUIDE.md" "docs\archived_docs\"
mv "KIDS_POSHAK_THEME_GUIDE.md" "docs\archived_docs\"

# Old proposals (superseded)
mv "DASHBOARD_REDESIGN_PROPOSAL.md" "docs\archived_docs\"
mv "DASHBOARD_REDESIGN_SUMMARY.md" "docs\archived_docs\"
mv "DASHBOARD_TESTING_GUIDE.md" "docs\archived_docs\"
mv "UI_UX_REVAMP_SPEC.md" "docs\archived_docs\"

# Old phase summaries (duplicates in /docs)
mv "PHASE_8A_COMPLETION_SUMMARY.md" "docs\archived_docs\"
mv "PHASE_8B_STATUS.md" "docs\archived_docs\"

# Old setup & guides
mv "setup-and-testing.md" "docs\archived_docs\"
mv "FEATURE_SUMMARY.md" "docs\archived_docs\"
mv "IMPLEMENTATION_GUIDE.md" "docs\archived_docs\"
mv "USER_GUIDE.md" "docs\archived_docs\"
mv "DEVELOPER_CHECKLIST.md" "docs\archived_docs\"
mv "PRODUCT_IMAGES_IMPLEMENTATION.md" "docs\archived_docs\"

# Old testing guides
mv "RECEIPT_QA_TESTING_GUIDE.md" "docs\archived_docs\"
mv "RECEIPT_TEMPLATES_GUIDE.md" "docs\archived_docs\"
mv "RECEIPT_TEMPLATES_UI_TESTING.md" "docs\archived_docs\"
```

### Step 3: Create Archive Index
Add `docs/archived_docs/README.md` with a list of archived documents and their purpose (for historical reference).

### Step 4: Update References
- Update CLAUDE.md to reference only `/docs` folder for active documentation
- Remove any old setup instructions pointing to outdated files

---

## Organization Result

### After Cleanup

**Root directory:**
```
✅ CLAUDE.md (project instructions)
✅ README.md (repo readme)
```

**docs/ folder (Active):**
```
📄 PROJECT_CONTEXT.md (reference)
📄 DEPLOYMENT_ARCHITECTURE.md (current)
📄 SECURITY_AUDIT.md (current)
📄 ROADMAP_AUDIT.md (current)
📄 PHASE_13_SECURITY_FIXES.md (current)
📄 PHASE_13_IMPLEMENTATION_SUMMARY.md (current)
📄 PHASE_14_SUPPLIERS_FEATURE.md (current)
📄 RUN_AND_TEST.md (how-to)
📄 PRODUCT_DOCUMENTATION.md (reference)
📄 [PHASE_7-12 historical docs]
📄 [Feature docs: Khata, Credit Limits, Split Payments, Suppliers]
📄 CLIENT_REQUESTS_PLAN.md (planning)
└─ archived_docs/ (historical reference)
   └─ [17 archived files]
```

---

## Benefits

✅ **Cleaner navigation** — docs/ contains only active, relevant documentation  
✅ **Clear history** — archived_docs/ preserves historical context  
✅ **Easier onboarding** — new team members see current docs first  
✅ **No deletions** — nothing is lost, just organized  
✅ **Git history** — archived files remain in git if needed later  

---

## Recommendation

**Proceed with archival** — the old docs are preserved but won't clutter active documentation. This makes onboarding clearer and navigation easier.
