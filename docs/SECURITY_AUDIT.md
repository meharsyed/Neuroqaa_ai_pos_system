# Security & Production-Readiness Audit

**Scope:** static review of the full repo (Django/DRF backend, React/Vite frontend) against the codebase as it stands on the `POS_cctv_shop_branch` working tree, 7 Sept 2026. No dynamic/penetration testing was performed this pass — see *What this audit did not cover* at the end.

**Bottom line:** the code that's here shows real security thinking — role checks with comments explaining the fraud they close, throttled login, signed/expiring receipt links, activity logging, a production settings file with HSTS and secure cookies already wired up. That makes the three critical gaps below more worth fixing, not less: they're the kind of thing that hides behind otherwise-careful code, and every one of them is a direct line to money or to an account.

---

## Priority order

| # | Finding | Severity | Effort to fix |
|---|---|---|---|
| 1 | Sale price and discount are fully client-controlled | Critical | Small–Medium |
| 2 | Auth tokens sit in `localStorage`, and nothing can revoke one | Critical | Small |
| 3 | The live database file is committed to git | Critical (data exposure) | Small (fix), can't undo the past |
| 4 | Django 5.0 is past end-of-life | High | Medium |
| 5 | `simplejwt` pinned to a version with a known CVE | High | Small |
| 6 | No commit discipline — months of work live only in one uncommitted working tree | High (operational) | Small (habit change) |
| 7 | Public receipt endpoint has no rate limit | Medium | Small |
| 8 | Product image upload has no explicit size/type ceiling | Medium | Small |
| 9 | `CORS_ALLOWED_ORIGINS` defaults to empty in the cloud settings | Medium (go-live blocker, not a vuln per se) | Small |
| 10 | Login has no lockout/backoff beyond the rate limit | Low | Small |
| 11 | Dependency hygiene — no `npm audit`/`pip-audit` run in CI | Low | Small |

---

## Critical

### 1. A sale's price and discount are whatever the client sends — nothing checks them against the catalogue

`CreateSaleSerializer` (`backend/apps/sales/serializers.py`) accepts `unit_price_paise` and `discount_paise` per line, and a bill-level `discount_paise`, with only `min_value=0` as a floor:

```python
class SaleItemInputSerializer(serializers.Serializer):
    unit_price_paise = serializers.IntegerField(min_value=0)
    discount_paise = serializers.IntegerField(min_value=0, default=0)
```

`create_sale()` in `services.py` then uses those numbers directly — it never reads `Product.sell_price_paise` to check them:

```python
line_total = int(qty * item["unit_price_paise"]) - item.get("discount_paise", 0)
...
total_paise = subtotal_paise - discount_paise + tax_paise
```

**What this means in practice:** any authenticated user — cashier included, no role check at all — can complete a sale at any price they choose. Ring up a Rs 60,000 camera at Rs 1, pocket the cash difference, and the system records a perfectly normal-looking Rs 1 sale. There's no ceiling on the discount either, so a bill-level discount larger than the subtotal is accepted and produces a negative total. Compare this to `void()` and `process_return()` in the same file, which both gate anything beyond a small ceiling behind an owner/manager check — and to the tax-rate override, which the team already made a deliberate, *logged* exception (`_log_tax_override`). Price and discount got neither the gate nor the log.

This is the single most exploitable gap in the system for a shop like this — till fraud is the everyday risk a POS exists to prevent, and right now the interface's price fields are the only thing enforcing them.

**Recommend:**
- Look up `Product.sell_price_paise` server-side and either reject a submitted `unit_price_paise` that doesn't match it, or accept a deviation only from `owner`/`manager` roles (mirroring the existing `IsOwnerOrManager` pattern).
- Cap bill-level and line-level discounts — a percentage ceiling the owner sets in `Setting` (the same mechanism already used for `cashier_return_limit_paise`) is the natural fit.
- Log any price override or above-ceiling discount the same way tax overrides are logged today, so it shows up in the activity log and the daily audit report.

### 2. Access and refresh tokens live in `localStorage`, and there's no way to revoke a stolen one

`frontend/src/store/authStore.ts` wraps the auth store in zustand's `persist` middleware with no custom `storage` option:

```ts
persist(
  (set) => ({ ...accessToken, refreshToken... }),
  { name: "pos-auth", partialize: (state) => ({ user, accessToken, refreshToken, isAuthenticated: state.isAuthenticated }) }
)
```

Zustand's `persist` defaults to `localStorage`. That's worth flagging on its own, because `docs/PHASE_12_PDF_AUTH_I18N_TESTS.md` states the opposite as the reason a bug happened: *"The access token lives in memory... a browser navigation is not an axios request."* That was true of how the token is **used** (an axios interceptor), but not of where it's **stored** — it and the refresh token both sit in `localStorage` under the key `pos-auth`, fully readable by any JavaScript that runs on the page.

That matters more than it would on a typical app because of the second half of this finding: there is no `rest_framework_simplejwt.token_blacklist` app installed, `BLACKLIST_AFTER_ROTATION` is `False`, and there is no logout endpoint on the backend at all — `frontend/src/lib/axios.ts`'s `logout()` only clears local state. A refresh token is valid for 7 days on the cloud build and **30 days** on the desktop build (`config/settings/desktop.py`). Put together: a single XSS anywhere in the app (a vulnerable dependency, a future feature that renders unsanitised content) reads a token straight out of `localStorage`, and once it's out, "signing out" the legitimate user does nothing to stop it being used — there is no server-side switch to flip. `ChangeOwnPasswordView` already says as much in its own comment: *"The old tokens still work — they are signed, not stored."*

**Recommend:**
- Install `rest_framework_simplejwt.token_blacklist`, turn on `BLACKLIST_AFTER_ROTATION`, and add a `/api/auth/logout/` endpoint that blacklists the refresh token — then have the frontend call it.
- Move the refresh token out of `localStorage`. The cleanest fix for a JWT-bearer setup like this is an `httpOnly` cookie for the refresh token (not reachable by JS at all) with the access token kept in memory only (drop it from `partialize`). If a full cookie migration is too big a change right now, at minimum stop persisting `refreshToken` in `localStorage` and re-authenticate on app reload instead.
- Shorten the desktop refresh-token lifetime from 30 days, or compensate with the blacklist above — 30 days is a long window for a token that currently can't be revoked.

### 3. The live database file is committed to git

`.gitignore` excludes `db.sqlite3`, but the desktop settings (`config/settings/desktop.py`) name the file `pos.db`, which doesn't match that pattern. `git ls-files` and `git status` both confirm it: `backend/data/pos.db` is tracked, and it shows up as **modified** in the current working tree — meaning real transactional data (sales, customers, khata balances, and hashed staff passwords) has been committed, more than once, into this repository's history.

Even if the file is removed from the working tree today, it stays recoverable from every commit that included it, for as long as the repository or any clone/fork of it exists — including the `origin/POS_cctv_shop_branch` copy already pushed to the remote. This is the one finding on this list where "fix it going forward" and "fix the exposure" are two different jobs.

**Recommend:**
- Add `backend/data/*.db` (or the exact filename) to `.gitignore` immediately, and `git rm --cached` it so future commits stop tracking it.
- Treat any data currently in that file as already exposed to anyone with repo access (which currently includes at least the four branches under `meharsyed`'s remote). If the repo has ever been shared more widely than the two people working on it, rotating customer-facing identifiers isn't really practical, but staff passwords should be reset regardless, since a hash committed to history should be treated as compromised.
- Rewriting git history (`git filter-repo`) to strip the file is possible but rewrites every commit hash and breaks any existing clone — worth doing once, deliberately, rather than repeatedly; decide this alongside the Postgres migration since that move naturally retires the SQLite file anyway.

---

## High

### 4. Django 5.0.6 is past end of life

Django 5.0 was not an LTS release: its security support window closed **2 April 2025**. This project pins `django==5.0.6`, meaning it has been outside the security-patch window for over a year, and any CVE found in Django since then — several have been, across the 6.0.x/5.2.x/4.2.x branches — simply won't be backported to 5.0. For a system about to go on a public server, this is worth fixing before launch rather than after: upgrade to **Django 5.2** (LTS, supported to April 2028).

### 5. `djangorestframework-simplejwt==5.3.1` has a known CVE

CVE-2024-22513 affects `simplejwt` versions through 5.5.0 (fixed in 5.5.1): the `for_user` token-issuance path doesn't check `is_active`, so a deactivated account's tokens can outlive the deactivation in some code paths. Combined with finding #2 (no blacklist, no logout endpoint), this closes a gap that matters concretely here — an owner firing a cashier for suspected till fraud expects that person locked out immediately, not merely unable to log in again. Upgrade to `>=5.5.1`.

*(Checked and not an issue: `reportlab==4.2.5` is well past the version that fixed CVE-2023-33733 (RCE via `rl_safe_eval`, fixed in 3.6.13), so no action needed there.)*

### 6. Months of work exist only as an uncommitted working tree

`git log` on this branch stops at 5 Sept; everything from Phase 10 onward — roles, tax, quotations, the PDF-auth fix, i18n — sits as staged-but-uncommitted or entirely untracked changes (`git status` shows dozens of modified and untracked files, including the whole `quotation_*.py` backend module and `QuotationsPage.tsx`). Nothing has gone through a pull request or CI on this branch since. That's not a vulnerability in the traditional sense, but it's a genuine risk to the business: one bad `git checkout`, one disk failure, or one confused `git reset` on this machine loses weeks of work with no remote copy. It also means the "328 backend tests / lint clean" claims in the phase docs have never actually been verified by CI against what's on the remote.

**Recommend:** commit and push in small, reviewed chunks going forward — even to a working branch — before starting the next phase of work. It doesn't need to be perfect history, just off this one machine.

---

## Medium

### 7. The public receipt-sharing endpoint has no rate limit

`apps/sales/public_views.py`'s `public_receipt` view is a plain Django view (not a DRF `APIView`), so none of the `DEFAULT_THROTTLE_CLASSES` configured in `REST_FRAMEWORK` apply to it. The signing itself is sound — a token can't be forged or enumerated without the server's `SECRET_KEY` — but the endpoint does a database query and renders HTML for anyone who requests it, unauthenticated, with no cap. It's a small, cheap-to-close gap: apply a scoped throttle (e.g. `django-ratelimit` on the view, or move it behind a lightweight DRF `APIView` so the existing `anon` throttle applies).

### 8. Product image upload has no explicit size or type ceiling

`Product.image` is a plain `ImageField` (`upload_to="products/"`) with no `validators=[...]` and no serializer-level size check. Pillow will reject a non-image file, but there's no configured ceiling on file size beyond Django's own defaults, which aren't tuned here. Add an explicit max-size validator (a few MB is plenty for a product photo) so a large upload can't fill disk or memory.

### 9. `CORS_ALLOWED_ORIGINS` defaults to an empty list in `cloud.py`

Not a vulnerability by itself — an empty allow-list is the safe default — but it means the production settings file will simply reject the real frontend's requests until `CORS_ALLOWED_ORIGINS` is set in the server's `.env`. Worth calling out now so it's a checklist item for launch day, not a fire to put out after the client is already looking at a broken app: set it to the exact production origin(s), never `*`.

---

## Low / hardening

- **10.** Login is throttled at 10/min per the `login` scope, which is reasonable, but there's no per-account lockout or backoff after repeated failures from different IPs. Low priority for a shop-floor system, worth a line item for later.
- **11.** No `npm audit` / `pip-audit` (or equivalent) step exists in CI (`.github/` was checked). Once this repo has real CI running against the remote branch, wiring in a dependency-vulnerability check is cheap insurance for the next CVE like #5.

---

## What was verified as already solid

Worth stating plainly, since an audit that only lists problems undersells the good decisions already made:

- Role checks (`IsOwner`, `IsOwnerOrManager`) are centralised in `apps/accounts/permissions.py` with comments explaining the exact fraud each one closes (a manager can't promote himself; a cashier can't see cost prices; the last owner can't be demoted or deactivated).
- `void()` and `process_return()` correctly gate anything beyond a small, owner-configurable ceiling behind a role check — this is exactly the pattern finding #1 needs applied to price/discount.
- Login failures are logged (`log_activity("login_failed", ...)`) without ever storing the attempted password — deliberate and correct.
- The signed receipt-share link (`apps/sales/sharing.py`) is well-designed: time-limited, revocable via a setting, `X-Robots-Tag: noindex`, `Referrer-Policy: no-referrer`. Finding #7 is a small gap in an otherwise sound design.
- `backend/.env` is correctly excluded from git (only `.env.example` is tracked); `cloud.py` already has `SECURE_SSL_REDIRECT`, HSTS, and secure cookies switched on.
- No `dangerouslySetInnerHTML` or `eval`/`new Function` usage anywhere in the frontend.
- `AuditPage.tsx`'s conditional-hooks bug (flagged in an earlier session) is fixed and explained in a comment — verified by reading the current code, not just the changelog.

---

## Dev items completed this session

- **i18n table headers** — the gap flagged in `docs/PHASE_12_PDF_AUTH_I18N_TESTS.md` ("table headers inside those pages are still English") is closed for the counter-facing pages: Products (both the catalogue and inventory-value tables), Bills (the bill list and the per-sale line-items table), Customers (the customer list and purchase-history dialog), Shifts, and Quotations. ~15 new translation keys were added to both the English and Urdu dictionaries in `frontend/src/lib/translations.ts` (reusing the existing `common.*` keys — `total`, `status`, `date`, `qty`, `customer`, `phone` — wherever a header already matched one, to avoid duplicate strings). Three of these headers live inside sub-components (`SaleDetailModal`, `CustomerHistoryModal`, `QuotationForm`) that didn't have `useTranslation()` called locally — exactly the trap the phase-12 write-up described running into before; each now has its own `const { t } = useTranslation()`.
- Verified clean: `tsc --noEmit` and `eslint` both pass on every file touched. The project's own `npm run test` suite could not be run this session — this machine's `node_modules` holds a Windows-only `@rollup/rollup-linux-x64-gnu` binary mismatch (the same issue the prior agent's write-up flagged and worked around by testing elsewhere); a `npm run test` on your normal Windows dev machine, or after `npm install` is re-run there, will confirm none of the 28 existing frontend tests regressed.

**Still open, unchanged from Phase 12's own list** (not attempted this session, since they need product decisions or a person, not code): backups/Postgres sequencing (your call, noted below), the brand-ramp dark-mode check, a native Urdu speaker's review of the ~200 translated strings, and broader frontend test coverage beyond `PaymentModal`.

On backups: sequencing them with the Postgres move is reasonable — just don't let "backups shortly" become the plan you launch with, per the prior agent's own note. The SQLite-in-git issue above (#3) is a reason to make that move sooner rather than later, since Postgres retires the file this finding is about.

---

## What this audit did not cover

This was a **static code review**, by your choice, not a live penetration test: no requests were sent to a running instance, no attempt was made to actually exploit finding #1 or #2 against real data, and no browser-based XSS/CSRF probing was done. It also didn't cover the `desktop/` Tauri wrapper's own configuration (allowlisted commands, CSP) or the `CCTV_DATABASE_SETUP.md`/CCTV-related surfaces in depth. If you want a follow-up pass that actually exercises the running app — creating a test sale at a manipulated price, attempting a token-replay after logout, etc. — that's a natural next step once the fixes above are in, and worth doing in a disposable test database rather than the live one.
