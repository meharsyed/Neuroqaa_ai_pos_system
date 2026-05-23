# Setup and Testing Guide — Phase 1

Complete step-by-step instructions to run and verify the Neuroqaa POS Phase 1 foundation locally on Windows + VS Code.

---

## Prerequisites

| Tool | Required version | How to check |
|---|---|---|
| Python | 3.11 (venv311 is already created) | `python --version` |
| Node.js | 20+ | `node --version` |
| npm | 8+ | `npm --version` |
| Docker Desktop | Any recent version (Option A only) | `docker --version` |

> You do **not** need Docker for Option B (the no-Docker path).

---

## Where things live

| File / Folder | Purpose |
|---|---|
| `backend/` | Django REST API |
| `backend/.env` | Local environment variables (SECRET_KEY, DB creds) — **stays here, do not move** |
| `backend/venv311/` | Python 3.11 virtual environment (already created, packages installed) |
| `backend/data/pos.db` | SQLite database file (created on first migrate, Option B only) |
| `frontend/` | React + Vite SPA |
| `frontend/node_modules/` | npm packages (created on first `npm install`) |
| `docker-compose.yml` | Spins up Postgres + Django + Vite in containers (Option A) |

---

## Why there are two Options

| | Option A — Docker | Option B — Local / No Docker |
|---|---|---|
| Database | PostgreSQL 16 (identical to CI and production) | SQLite (offline-first, same as Tauri desktop mode) |
| Requires Docker Desktop | Yes | No |
| Setup effort | Lower — one command starts everything | Slightly more manual — two terminals |
| Best for | CI parity, testing Postgres-specific behaviour | Quick local dev, offline use |

---

## Option B — Local without Docker (recommended for getting started)

Run the backend and frontend in **two separate VS Code terminals**.

### Opening two terminals in VS Code

1. Press `` Ctrl+` `` to open the integrated terminal panel
2. Click the **+** button (top-right of the terminal panel) to open a second terminal
3. Use the dropdown list to switch between Terminal 1 and Terminal 2

---

### TERMINAL 1 — Django Backend

#### Step 1 — Navigate to the backend folder

```powershell
cd "d:\Neuroqaa Stuff\POS System\pos-system-GT\backend"
```

#### Step 2 — Activate the Python virtual environment

```powershell
.\venv311\Scripts\Activate.ps1
```

**Expected:** Your prompt prefix changes to `(venv311)`:
```
(venv311) PS D:\Neuroqaa Stuff\POS System\pos-system-GT\backend>
```

**If you get an execution policy error**, run this once and then retry Step 2:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Step 3 — Point Django at the desktop (SQLite) settings

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
```

No output. This env var tells Django to use `config/settings/desktop.py` — which reads `backend/.env` and uses SQLite instead of PostgreSQL. **You must do this in every new terminal session before running any Django command.**

> **Why the .env stays in `backend/`:** Django's `BASE_DIR` is set to the `backend/` folder. The `.env` file is always read from `BASE_DIR / ".env"`, so moving it anywhere else would break the lookup.

#### Step 4 — Run database migrations

```powershell
python manage.py migrate
```

**Expected output** — a list of migrations applied, ending like:
```
Operations to perform:
  Apply all migrations: accounts, admin, auth, contenttypes, sessions, simple_history
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying accounts.0001_initial... OK
  Applying simple_history.0001_initial... OK
  ...
```

This creates `backend\data\pos.db` — your local SQLite database file.

**If you see `Set the SECRET_KEY environment variable`:**  
You forgot Step 3. Re-run `$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"` in the same terminal, then re-run `migrate`.

#### Step 5 — Create a superuser

```powershell
python manage.py createsuperuser
```

You will be prompted interactively. Type each value and press **Enter**:

```
Email address:  admin@neuroqaa.com
Username:       admin
First name:     Admin
Last name:      User
Password:       StrongPass123!
Password (again): StrongPass123!
```

**Expected:**
```
Superuser created successfully.
```

> This project uses **email** as the login field (not username). You will use `admin@neuroqaa.com` + `StrongPass123!` everywhere.

#### Step 6 — Start the Django development server

```powershell
python manage.py runserver
```

**Expected output:**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
Django version 5.0.6, using settings 'config.settings.desktop'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

**Leave Terminal 1 open and running.** Django will print a new line for each incoming HTTP request as you use the app.

---

### TERMINAL 2 — React Frontend

#### Step 7 — Navigate to the frontend folder

```powershell
cd "d:\Neuroqaa Stuff\POS System\pos-system-GT\frontend"
```

#### Step 8 — Install npm packages (first time only)

```powershell
npm install
```

**Expected output** (takes 30–60 seconds on first run):
```
added 312 packages, and audited 313 packages in 45s
found 0 vulnerabilities
```

You only need to run `npm install` once. On subsequent runs, skip straight to Step 9.

#### Step 9 — Start the Vite dev server

```powershell
npm run dev
```

**Expected output:**
```
  VITE v5.x.x  ready in 450 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

**Leave Terminal 2 open and running.**

---

### Verify the running system

Both terminals must be running before you test in the browser.

#### Step 10 — Check the React login page

Open: **http://localhost:5173**

**Expected:** You are immediately redirected to `/login`. This confirms the route guard (`ProtectedLayout`) is working — unauthenticated users cannot reach `/dashboard`.

You should see:
- Heading: "Neuroqaa POS"
- Subheading: "Sign in to your account"
- Email and Password fields
- "Sign in" button

#### Step 11 — Log in

- **Email:** `admin@neuroqaa.com`
- **Password:** `StrongPass123!`
- Click **Sign in**

**Expected:** Redirected to `/dashboard` (a placeholder page for now — business features come in Phase 2+).

**In Terminal 1** (Django), you should see:
```
[23/May/2026 12:00:00] "POST /api/auth/login/ HTTP/1.1" 200 ...
```
The `200` confirms the login API call succeeded.

#### Step 12 — Verify JWT tokens are stored

In the browser, open **DevTools** (`F12`) → **Application** tab → **Local Storage** → `http://localhost:5173`.

Look for the key `pos-auth`. Its value should be a JSON object containing:
```json
{
  "state": {
    "user": {
      "email": "admin@neuroqaa.com",
      "role": "owner",
      "first_name": "Admin",
      "last_name": "User"
    },
    "accessToken": "eyJhbGci...",
    "refreshToken": "eyJhbGci...",
    "isAuthenticated": true
  }
}
```

Now **refresh the page** (`F5`). You should stay on `/dashboard` without being kicked back to login — Zustand is persisting auth state to localStorage.

#### Step 13 — Check the API docs (Swagger)

Open: **http://localhost:8000/api/docs/**

**Expected:** Swagger UI showing three endpoints:
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`

#### Step 14 — Check the Django admin

Open: **http://localhost:8000/admin/**

Log in with `admin@neuroqaa.com` / `StrongPass123!`.

**Expected:** Django admin panel with the header "Neuroqaa POS Admin" (not the generic "Django Administration").

You should see a **Users** section under Accounts. Click it — your superuser should be listed.

#### Step 15 — Test the /me/ endpoint directly

You can test the API from PowerShell without the browser:

```powershell
# Login and capture the token
$login = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/api/auth/login/" `
  -ContentType "application/json" `
  -Body '{"email":"admin@neuroqaa.com","password":"StrongPass123!"}'

# See what came back
$login.user      # user object
$login.access    # JWT access token (long string starting with eyJ...)

# Call /me/ with the token
Invoke-RestMethod -Method Get `
  -Uri "http://localhost:8000/api/auth/me/" `
  -Headers @{ Authorization = "Bearer $($login.access)" }
```

**Expected from `/me/`:**
```
id         : 1
email      : admin@neuroqaa.com
username   : admin
first_name : Admin
last_name  : User
full_name  : Admin User
role       : owner
phone      :
is_active  : True
```

---

### Running the test suite

#### Backend tests (pytest)

Stop the Django server (`Ctrl+C`) in Terminal 1, or open a **third terminal**.  
Make sure `(venv311)` is active and `$env:DJANGO_SETTINGS_MODULE` is set.

```powershell
cd "d:\Neuroqaa Stuff\POS System\pos-system-GT\backend"
.\venv311\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
pytest --override-ini="DJANGO_SETTINGS_MODULE=config.settings.desktop" -v
```

**Expected output — all 5 tests green:**
```
PASSED apps/accounts/tests/test_auth.py::TestLoginEndpoint::test_login_returns_tokens_and_user
PASSED apps/accounts/tests/test_auth.py::TestLoginEndpoint::test_login_bad_credentials
PASSED apps/accounts/tests/test_auth.py::TestMeEndpoint::test_me_requires_auth
PASSED apps/accounts/tests/test_auth.py::TestMeEndpoint::test_me_returns_user_data
PASSED apps/accounts/tests/test_auth.py::TestMeEndpoint::test_refresh_token_works

5 passed in X.XXs
```

#### Frontend checks

Stop `npm run dev` (`Ctrl+C`) in Terminal 2, or open a third terminal:

```powershell
cd "d:\Neuroqaa Stuff\POS System\pos-system-GT\frontend"

npm run type-check    # TypeScript compiler — expects 0 errors
npm run lint          # ESLint — expects 0 warnings
npm test              # Vitest unit tests
```

---

## Option A — Docker Compose (PostgreSQL, full-stack)

Use this when you want Postgres (CI parity) or want everything in one command.

**Prerequisite:** Docker Desktop must be open and running (check the system tray icon).

### Step 1 — Verify Docker is up

```powershell
docker info
```

You should see engine details. If you see "Cannot connect to the Docker daemon" — start Docker Desktop first and wait ~30 seconds.

### Step 2 — Start all services

From the **project root** (not inside `backend/`):

```powershell
cd "d:\Neuroqaa Stuff\POS System\pos-system-GT"
docker-compose up --build
```

**First run takes 2–5 minutes.** Docker:
1. Downloads `postgres:16-alpine` image
2. Builds the backend Python image (installs all pip packages)
3. Starts Postgres, waits for it to be healthy
4. Runs `python manage.py migrate` automatically
5. Starts the Django server
6. Starts the Vite frontend server

**Watch for these two lines** — they mean everything is ready:
```
backend_1   | Starting development server at http://0.0.0.0:8000/
frontend_1  | ➜  Local:   http://localhost:5173/
```

Subsequent starts (after the image is built) take ~10 seconds.

### Step 3 — Create a superuser inside the container

Open a **second terminal** (keep docker-compose running in the first):

```powershell
cd "d:\Neuroqaa Stuff\POS System\pos-system-GT"
docker-compose exec backend python manage.py createsuperuser
```

Same prompts as Option B. Use the same credentials.

### Step 4 — Test the system

Same URLs and checklist as Option B Steps 10–14. The app is identical from the browser's perspective.

### Step 5 — Run tests inside Docker

```powershell
docker-compose exec backend pytest -v
```

### Step 6 — Stop everything

```powershell
# Ctrl+C in the docker-compose terminal, then:
docker-compose down

# To also wipe the Postgres volume (fresh database on next start):
docker-compose down -v
```

---

## Phase 1 exit criteria checklist

Run through this list after completing either Option A or Option B:

- [ ] http://localhost:5173 → redirected to `/login` (route guard works)
- [ ] Log in with superuser credentials → land on `/dashboard`
- [ ] Refresh page → stay logged in (Zustand + localStorage persistence works)
- [ ] http://localhost:8000/api/docs/ → Swagger UI with 3 endpoints visible
- [ ] http://localhost:8000/admin/ → "Neuroqaa POS Admin" branding (not default Django branding)
- [ ] `/api/auth/me/` with Bearer token → returns user JSON with correct email and role
- [ ] Backend pytest → 5 tests pass, 0 failures
- [ ] `npm run type-check` → 0 TypeScript errors
- [ ] `npm run lint` → 0 ESLint warnings

All 9 items passing = Phase 1 complete.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Set the SECRET_KEY environment variable` | `$env:DJANGO_SETTINGS_MODULE` not set in this terminal session | Re-run `$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"` then retry |
| `Activate.ps1 cannot be loaded` | PowerShell execution policy blocks scripts | Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` once |
| Login returns 401 in browser | Wrong credentials typed | Double-check you used the exact email + password from `createsuperuser` |
| "Network Error" on login | Django server not running | Check Terminal 1 still shows `Starting development server` |
| `npm install` takes very long | First install downloads ~300 packages | Normal on first run, subsequent runs are instant |
| Port 8000 already in use | Another process is bound to 8000 | Run `netstat -ano \| findstr :8000` to find the PID, then `Stop-Process -Id <PID>` |
| Port 5173 already in use | Another Vite instance running | Close the other terminal or run `npm run dev -- --port 5174` |
| `docker-compose up` — Postgres unhealthy | Docker Desktop not fully started | Wait 30 s, run `docker-compose down` then `up` again |