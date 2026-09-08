# Phase 13 — the nine fixes from the security audit

**Backend: JWT moved to an httpOnly cookie + blacklist, Django 5.2, simplejwt 5.5.1, receipt throttle, image validation, CORS fail-fast, login lockout. Frontend: refresh token removed from `localStorage` entirely. Git: the live database untracked. CI: dependency scanning added.**

This closes every item from `docs/SECURITY_AUDIT.md`'s priority table except #3 (the *history* rewrite — see below, that one needs your go-ahead, not just code) and #11 (CI dependency hygiene, which is now wired up but its first real signal only arrives on the next push).

---

## Run it

Two things need to happen on your machine before any of this runs, because this session had no network access to install packages or run `manage.py` itself — everything below was written and reviewed carefully, but **has not been executed**. Treat this section as the acceptance test, not a formality.

```powershell
cd "D:\Neuroqaa Stuff\POS System\pos-system-GT\backend"
.\venv311\Scripts\Activate.ps1
pip install -r requirements\dev.txt
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
python manage.py makemigrations --check --dry-run   # see "About the two migrations" below
python manage.py migrate
ruff check .
black --check .
pytest -q                                            # expect 328 passed, same as before
python manage.py runserver
```

```powershell
cd "D:\Neuroqaa Stuff\POS System\pos-system-GT\frontend"
npm run type-check
npm run lint
npm run test                                         # expect 28 passed, same as before
npm run dev
```

Then walk the actual login → use the app → sign out flow once in a browser with devtools open on the Application/Storage tab — confirm `localStorage` no longer has a `refresh` value under the `pos-auth` key (only `user`/`isAuthenticated` should be there), and confirm a `refresh_token` cookie appears, marked `HttpOnly`, after login.

---

## 1–2. The refresh token: out of `localStorage`, into an httpOnly cookie, and now revocable

This was the two-part finding — where the token lived, and that nothing could kill one once issued — and both needed backend and frontend changes together, so they're one piece of work.

**Backend** (`apps/accounts/views.py`, `config/settings/base.py`, `apps/accounts/urls.py`):

- `LoginView` now strips `refresh` out of the JSON body and sets it as an httpOnly, `SameSite=Lax` cookie scoped to `/api/auth/` — it never reaches JavaScript, so an XSS anywhere in the app can read the 30-minute access token (already in memory, low value) but not a token that used to be valid for 7–30 days.
- `CookieTokenRefreshView` replaces the stock `TokenRefreshView` — it reads the cookie instead of the body, and re-sets the (rotated) cookie on the way out, following the same pattern.
- `LogoutView` is new (`POST /api/auth/logout/`) — it blacklists the refresh token via `rest_framework_simplejwt.token_blacklist` (now installed) and clears the cookie. `BLACKLIST_AFTER_ROTATION` is now `True`, so a token that's been rotated — or stolen and used to sign out by whoever has it — stops working immediately rather than staying valid for its full lifetime.
- `rest_framework_simplejwt.token_blacklist` ships its own migrations; `python manage.py migrate` picks them up automatically once `pip install` has run — no migration was hand-written for this part.

**Frontend** (`store/authStore.ts`, `lib/axios.ts`, `lib/users.ts`, `layouts/components/AppSidebar.tsx`, `types/auth.ts`):

- `refreshToken` is gone from the store and from what gets persisted — `accessToken` lives in memory only and is excluded from `partialize`. `user`/`isAuthenticated` are still persisted so a reload doesn't flash a logged-out screen while the silent refresh runs.
- The refresh call in the 401 interceptor no longer sends a body — it relies on `withCredentials: true` (now set on `apiClient` and on that call) to carry the cookie.
- The sidebar's sign-out button now calls the new `/auth/logout/` endpoint (`logoutApi()` in `lib/users.ts`) before clearing local state, so signing out actually revokes the token server-side instead of just forgetting it client-side.

**What I did not do:** touch the desktop (Tauri) build's cookie behaviour specifically. `tauri://localhost` calling an `http(s)://` API host is a genuinely different cookie situation than a normal browser origin, and since the client's live system is the web (cloud) build, I focused the actual verification there. If the desktop app is still being distributed, sign-in on it needs its own test pass before you'd trust this — it may just work (same-site behaviour across custom schemes varies by webview), but I'm not claiming it does.

## 3. Django 5.0.6 → 5.2.15

One line in `requirements/base.txt`. Django 5.2 is the current LTS (security support to April 2028); 5.0 stopped receiving patches in April 2025.

**This is the one change on this list with real, if unlikely, blast radius**, and it's the one I most want you to run the full test suite against before anything else. Two minor versions is not usually eventful for a codebase that doesn't lean on deprecated APIs, and nothing in this codebase's use of the ORM, forms, or `django.utils.timezone` jumped out as deprecated in 5.1/5.2 while reading through it — but "I read the code and it looks fine" is not the same as "328 tests passed against it," and only you can run that part right now. If `pytest` throws anything after the upgrade, it'll almost certainly be in `simple_history`, `django-import-export`, or `drf-spectacular` — those are the three third-party packages most likely to have version-specific assumptions about Django internals, and none of their pins were touched, so worth checking their changelogs first if something breaks there specifically.

**If it doesn't pass:** revert just the one line (`django==5.0.6`) and tell me what broke — do not ship the other eight fixes blocked behind this one; they're independent.

## 4. `djangorestframework-simplejwt` 5.3.1 → 5.5.1

One line, same file. Fixes CVE-2024-22513. Bundled with the cookie work above since they touch the same views anyway.

## 5. Public receipt endpoint — rate-limited

`apps/sales/public_views.py`'s `public_receipt` is now a DRF-throttled view (`@api_view` + a dedicated `PublicReceiptThrottle` scope, `20/min` per IP — see `DEFAULT_THROTTLE_RATES` in `base.py`) instead of a plain Django view with no throttling at all. Behaviour for a real customer opening their bill link is unchanged; a script hammering the endpoint now gets 429s.

## 6. Product image upload — a real ceiling, not a narrow one

`Product.image` now has a `validate_product_image` validator (`apps/catalog/models.py`): **10 MB** ceiling, and JPEG/PNG/WEBP/HEIC/HEIF all accepted — deliberately generous, per your note, rather than a tight single-format rule that would reject a normal phone photo. Pillow's own decode check (already run by DRF's `ImageField`) still catches anything that isn't a genuine image regardless of what it claims to be.

## 7. `CORS_ALLOWED_ORIGINS` — fails loudly instead of failing silently

`config/settings/cloud.py` now raises `ImproperlyConfigured` at startup if `CORS_ALLOWED_ORIGINS` is empty, the same way a missing `SECRET_KEY` already does. An empty list used to mean "the API silently refuses every browser" — now it means "the service won't start until you set it," which is a much shorter path to noticing the problem. **Action needed from you at deploy time:** set `CORS_ALLOWED_ORIGINS` in the server's `.env` to the exact origin the frontend is served from before the first `gunicorn` start — see the deployment doc for the specific value once the hosting decision below is settled.

## 8. Login lockout beyond the rate limit

`LoginView` now checks the existing `login_failed` activity-log entries for the attempted email in the last 15 minutes before even trying to authenticate; five failures locks that specific account out (429, with a plain-language message) regardless of which IP the attempts come from. No new table, no cache backend, no new dependency — it reads the audit trail that was already being written, which means it works correctly across every gunicorn worker without any extra configuration (a `LocMemCache`-based approach would not, since each worker has its own memory). A new `login_locked` activity-log action was added for this.

## 9. CI dependency scanning

`.github/workflows/ci.yml` has a new `dependency-audit` job: `pip-audit` against both requirements files, `npm audit --audit-level=high` against the frontend. It's `continue-on-error: true` deliberately — a freshly-published CVE in some transitive dependency shouldn't block an unrelated PR, but it will show up in the run's annotations the same week it's disclosed instead of waiting for the next manual audit.

---

## About the two hand-written migrations

`apps/accounts/migrations/0007_alter_activitylog_action.py` and `apps/catalog/migrations/0006_alter_product_image_validators.py` were **written by hand, not by `makemigrations`** — this session had no route to install Django anywhere to run it (both this environment's and your linked machine's Linux shells returned a flat 403 from PyPI; that's an infrastructure restriction, not a decision). Both are metadata-only changes (a `choices` addition, a `validators` addition — neither touches a column or a type), which is about as low-risk as a hand-written migration gets, but **the check to actually run is `python manage.py makemigrations --check --dry-run`** after `pip install`, which will tell you in one line whether Django agrees these fully describe the model state or wants one more migration to reconcile a detail I got slightly wrong. If it does want more, that's an additive follow-up migration, not a sign anything here is broken.

---

## What I deliberately did not do

**The git history rewrite.** The audit's finding #3 was two problems: the live database is *currently* tracked (fixed — `.gitignore` now matches the actual filename, and it's been `git rm --cached`), and it's *already in every past commit*, recoverable from history even after that. Untracking it going forward was safe to just do. Rewriting history to strip it out for good (`git filter-repo` or equivalent) is a different kind of operation — every commit hash on this branch changes, every existing clone (including whatever `origin/POS_cctv_shop_branch`, `ikram_branch`, and the others already have checked out) breaks and needs to be re-cloned or force-reset, and it cannot be undone once pushed. That's not something to do as a side effect of a fixes pass — it's a decision, and if anyone else has a clone of this repo, a heads-up to them before it happens. Tell me if you want to go ahead with it and I'll walk it through carefully; otherwise, the practical mitigation is what's already true after this pass — no *new* data joins history, and rotating staff passwords (mentioned in the audit) is the move for what's already exposed.

**Anything Tauri/desktop-specific**, per the note under fix #1–2 above.

**Building the actual production deployment** (Dockerfiles, nginx config, a deploy script) — that depends on the hosting decision this reply also covers, so it comes after that's settled, not before.

---

*Written and reviewed statically — full test suite run pending on your machine, per "Run it" above.*
