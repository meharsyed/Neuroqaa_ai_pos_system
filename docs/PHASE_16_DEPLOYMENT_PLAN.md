# Phase 16 — Deployment plan: yes, deploy on the KVM1, and here's exactly how

**Short answer to your question: yes, it's feasible and it's the wise call.** Everything the Phase 15 checklist needed to confirm came back clean — there's nothing about this specific server that changes the recommendation in `docs/DEPLOYMENT_ARCHITECTURE.md`. Go ahead and buy the domain. Below is the reasoning, the concrete architecture your server's actual setup dictated, and the full step-by-step to get there.

---

## What your checklist output actually told us

| Question | What we found | What it means for the POS |
|---|---|---|
| CPU | 1 vCPU (`nproc` = 1) | The real constraint on this box. Nothing here is unworkable, but every design choice below is made to avoid making that one core do unnecessary work. |
| RAM | 3.8 GB total, only 390 MB actually in use, 3.1 GB available | Plenty of headroom. The 2.6 GB shown as "buff/cache" is reclaimable disk cache, not memory anything is holding onto. |
| Disk | 49 GB total, 4 GB used, 45 GB free | No concern at all. |
| Swap | **0 B configured** | Missing safety net — added in the setup steps below (a 2 GB swapfile), exactly as `DEPLOYMENT_ARCHITECTURE.md` recommended. |
| How the website is served | `nginx` (native, not containerized) reverse-proxying to a **Django app run as a systemd service** (`neuroqaa.service`) | The website isn't in Docker at all. Good news, not bad — it means Docker is free for the POS to use without touching how the website runs. |
| Database | **Native PostgreSQL 14**, bound to `127.0.0.1`/`::1` only (never exposed) | Confirms the plan from `DEPLOYMENT_ARCHITECTURE.md`: one Postgres *server*, a second *database* and *role* for the POS, not a second Postgres process. Already correctly locked down to localhost — nothing to change there. |
| Docker | **Installed and running** (`docker.service` active), but nothing currently running in it (`docker ps -a` empty) | Docker is available and unused — exactly the situation you want. The POS gets to use it with zero risk of colliding with anything already containerized, because nothing is. |
| SSL | Certbot/Let's Encrypt already manages the website's cert (`neuroqaa-ai.tech`) | Same tool, same process, gets the POS its own certificate for its own domain — nothing about the existing cert is touched. |
| OS firewall | `ufw` inactive; raw `iptables` has only Docker's own (empty) chains | Nothing is blocking anything right now. No new firewall rule is required for this deployment — the POS traffic all goes over 80/443, which are already open. |
| Cron/backups | No user crontab; only stock system entries (certbot renewal, docker image/build pruning, log rotation) | No existing backup job to coordinate with or avoid disturbing. The POS's own `pg_dump` backup job (from `DEPLOYMENT_ARCHITECTURE.md`) is a clean addition. |

Nothing here changes the recommendation — if anything, it strengthens it: the website isn't even using Docker, so there's zero shared-runtime surface between the two apps. The only thing genuinely shared is the Postgres *server process* and the *nginx* process, and both are designed from the ground up to safely host multiple independent things.

---

## The one thing I changed, and why

While confirming the production settings file (`backend/config/settings/cloud.py`) matched this plan, I found it was written to always store product images and static files in **Amazon S3** — which needs an AWS account and a bucket, neither of which fits "deploy on the box you already have and keep the budget intact." I changed it to default to **local disk storage** (served directly by nginx, same as the media/static setup most single-VPS Django deployments use) when no S3 bucket is configured, while leaving S3 fully available as a drop-in option later — just set `AWS_STORAGE_BUCKET_NAME` in the environment file and it switches back, no code change needed. This is a small, backward-compatible change (`git diff backend/config/settings/cloud.py` to see exactly what moved) — flagging it clearly since it's a settings file, not something I'd change silently.

---

## What's now in your repo (not yet committed — review and commit when ready)

I did **not** run `git add`/`git commit` — these are new, untracked files plus the one settings edit above; `git status` on your machine will show them alongside the pre-existing unrelated line-ending changes noted in earlier phases. Review with `git diff` / `git status` and commit whenever you're comfortable:

- **`backend/Dockerfile.prod`** — the production image: Python 3.12, installs `requirements/prod.txt`, runs migrations + `collectstatic` + gunicorn on container start (never at build time, since those need real secrets that only exist on the server, never baked into an image).
- **`backend/.dockerignore`** — keeps the image lean (skips your venv, caches, local `.env`, media).
- **`docker-compose.prod.yml`** (repo root) — the one production service: the backend container, run with `network_mode: host` (explained below), a 1 GB memory cap, and volumes so static/media files land on the server's own disk where nginx can serve them directly. Deliberately **no Postgres service** (reuses the native one already on the box) and **no frontend service** (the built frontend is static files nginx serves directly — no Node process needs to run in production).
- **`deploy/nginx-pos.conf.template`** — the new nginx server block for the POS's domain. A sibling to the website's existing block, not a replacement — the website's `/etc/nginx/sites-available/neuroqaa` is never touched.
- **`deploy/server-setup.md`** — the one-time manual runbook: swapfile, the new Postgres database/role, a dedicated `posdeploy` system user (so the CI/CD deploy key never needs root or touches the website's files), first manual deploy, nginx + Certbot. Read it top to bottom before running anything — every command is annotated with what it does.
- **`.github/workflows/deploy.yml`** — the CI/CD pipeline (details below).

**Why `network_mode: host`** on the backend container, specifically: it's what lets the container reach the server's existing Postgres at `127.0.0.1:5432` *without changing Postgres's configuration at all* (no edits to `listen_addresses` or `pg_hba.conf` — both of which the website's own database access depends on). The tradeoff is the container skips Docker's usual network isolation, which is a non-issue for one trusted container on a server you control — and `Dockerfile.prod` binds gunicorn to `127.0.0.1` specifically, so the container is still never reachable directly from the internet; only nginx (on the same host) can reach it, exactly as if it weren't containerized at all.

---

## The CI/CD pipeline, concretely

`.github/workflows/deploy.yml` is a separate file from your existing `ci.yml` on purpose — it triggers only after `ci.yml` finishes successfully on `main` (via a `workflow_run` trigger), so this new, unproven pipeline can never affect your existing, working test workflow even if something in it needs fixing later.

What it does, in order, every time you push to `main` (after tests pass):

1. **Builds the backend Docker image on GitHub's own runner** (not your VPS) and pushes it to GitHub Container Registry (`ghcr.io`) — this is the deliberate fix for the 1-vCPU constraint: the CPU-heavy work of building the image never happens on the server, so a deploy never competes with the live website for CPU.
2. **Builds the frontend** (`npm run build`) on the same runner, and `rsync`s the built `dist/` folder straight to `/opt/pos-system/frontend/dist/` on your server.
3. **SSHes in** (using a dedicated deploy key — see `deploy/server-setup.md` step 3, not your own root key) and runs `docker compose pull && docker compose up -d` — it only ever *pulls* the already-built image, never rebuilds on the server. This touches only the POS's own compose project and container; it has no command that can reach nginx's config, the website's files, or the website's systemd service.
4. **Health-checks** the live POS URL at the end, so a broken deploy shows up as a failed GitHub Actions run immediately.

### GitHub repo secrets you'll need to add (Settings → Secrets and variables → Actions)

| Secret | Value |
|---|---|
| `SSH_HOST` | `187.127.204.34` |
| `SSH_USER` | `posdeploy` (the dedicated user from `deploy/server-setup.md` step 3 — not `root`) |
| `SSH_PRIVATE_KEY` | the private half of the deploy keypair generated in that same step |
| `POS_DOMAIN` | the domain once you've bought and pointed it (e.g. `pos.yourdomain.com`) |
| `GHCR_USERNAME` | your GitHub username |
| `GHCR_TOKEN` | a Personal Access Token with `read:packages` scope, so the *server* can pull the image (separate from the token GitHub Actions itself uses to *push* it, which is automatic) |

---

## The actual order to do this in

1. **Buy the domain.** Point an A record at `187.127.204.34` (root domain or a `pos.` subdomain — either works with the nginx template as-is, just substitute whichever you land on for `POS_DOMAIN` everywhere).
2. **Work through `deploy/server-setup.md` top to bottom** on the live server — swapfile, the new Postgres role/database, the `posdeploy` user and its SSH key, cloning the repo to `/opt/pos-system`, writing `backend/.env.prod`, the first manual `docker compose up -d --build`, then the nginx block and Certbot. Each step includes a way to confirm the website is still fine before moving to the next.
3. **Confirm from outside the server**: the POS domain loads, `/api/` responds through nginx, and the company website is unaffected — three `curl`s, all in step 7 of that file.
4. **Add the six GitHub secrets** above.
5. **Push a small, low-risk change to `main`** (or just re-run the workflow manually from the Actions tab) to prove the automated pipeline end-to-end before relying on it for real changes.

From that point on, merging to `main` is the deploy.

---

## What's still deliberately manual / not automated

- **Database migrations for genuinely destructive schema changes** (renaming or dropping a column, say) still deserve a manual look before a push, even though `migrate` runs automatically on every deploy — the pipeline runs whatever migration exists, it doesn't judge whether one is safe.
- **The independent `pos_db` backup job** from `DEPLOYMENT_ARCHITECTURE.md` (a `pg_dump` cron, shipped off-box) — not set up yet; worth doing right after the first successful deploy, not deferred indefinitely.
- **Basic uptime monitoring** (a free UptimeRobot check on the POS's URL) — same as above, cheap and worth doing on day one rather than after the first incident.
- **Rollback**: if a deploy goes bad, the fastest recovery today is re-running the workflow against the previous commit's SHA, or manually running `docker compose -f docker-compose.prod.yml up -d` on the server with `POS_BACKEND_IMAGE` pointed at the previous image tag (every image is tagged with its commit SHA, not just `latest`, specifically so this is possible).

None of this blocks going live — they're the natural next hardening steps once the pipeline itself is proven, the same "additive, not urgent" spirit as everything else in this plan.
