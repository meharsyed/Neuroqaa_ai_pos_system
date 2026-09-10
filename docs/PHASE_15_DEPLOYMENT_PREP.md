# Phase 15 — Deployment prep: getting the POS onto your live Hostinger KVM1 safely

**Status: information-gathering stage.** Nothing gets installed, configured, or touched on the server in this phase. This doc is a checklist for *you* to run against the live VPS, plus the reasoning for why each item matters, so that when we do start deploying, every decision is based on what's actually on that machine — not assumptions.

Two decisions are now locked in, based on your answers:

- **Git host:** GitHub
- **Deploy trigger:** auto-deploy on push to `main`

Everything below is written around those two choices.

---

## The one rule that matters more than anything else in this doc

**Your company website is live on this server right now, for real customers. Nothing we do for the POS should touch it.** Every command in the checklist below is read-only — it inspects the server, it doesn't change anything. When we get to the actual install phase later, the entire plan (from `docs/DEPLOYMENT_ARCHITECTURE.md`) is built around addition, not modification: new Docker containers, a new nginx server block for a new subdomain, a separate database — sitting *next to* whatever's running the website, never inside it. This checklist exists to confirm that plan is safe before we act on it, not to change anything yet.

---

## What we already know from your screenshots

No need to re-check these — already visible in the hPanel Overview you shared:

| Item | Value |
|---|---|
| OS | Ubuntu 22.04 LTS |
| Plan | KVM1 |
| Public IP | `187.127.204.34` |
| Disk used | ~4 GB of 50 GB (plenty of headroom) |
| Bandwidth | negligible (confirms this is a low-traffic site — matches the assumption in `DEPLOYMENT_ARCHITECTURE.md`) |
| Docker Manager | listed as a panel feature (doesn't yet tell us if it's *actually installed and in use* — that's item 3 below) |
| Firewall (Hostinger panel) | shows "0" rules |
| Snapshots/backups | "2" existing |
| Malware scanner | active |

Everything else needs an SSH session. Log in as:

```bash
ssh root@187.127.204.34
```

(If you've set up a non-root sudo user instead, use that — just prefix commands with `sudo` where needed.)

---

## The checklist — run these, paste me the output

I've grouped them by what question each one answers. None of these change anything on the server.

### 1. System resources (is there room for the POS alongside the website?)

```bash
free -h
nproc
df -h
uname -a
```

**Why:** KVM1 is usually 1 vCPU / 4 GB RAM (Hostinger's current spec, but confirm your actual allocation). The POS stack (Django + Postgres + a small frontend build, all in Docker) needs to coexist with whatever's already running the website in whatever RAM is left over. This tells us the real ceiling before we set container memory limits.

### 2. What's currently running, and how the website is served

```bash
sudo ss -tulpn
sudo systemctl list-units --type=service --state=running
docker ps -a 2>/dev/null || echo "docker not installed or not running"
```

**Why:** `ss -tulpn` shows every listening port and the process behind it. We need to know what's already bound to ports 80/443 (almost certainly the website's web server) so the POS's nginx config picks different, non-conflicting ports/vhosts, not because the two would literally collide (they won't, if we set it up as a separate server block on the same nginx), but so we know exactly what we're adding a sibling to rather than guessing.

### 3. Is Docker actually installed and in use, or just available as a panel feature?

```bash
docker --version
docker compose version
docker ps -a
```

If the first command says "command not found," Docker isn't installed yet — Hostinger's "Docker Manager" panel entry doesn't necessarily mean it's active on your specific VPS, it can just mean the *feature* is offered.

**Why:** If Docker's already there and the website itself runs some part of its stack in containers, we want to see what those containers are before adding ours (naming, network, port collisions). If Docker isn't installed at all, that's fine too — we install it fresh for the POS, and it plays no role in the existing website at all.

### 4. How is the website actually served — web server and app stack

```bash
which nginx apache2 2>/dev/null
sudo nginx -v 2>/dev/null
sudo apache2 -v 2>/dev/null
ls -la /etc/nginx/sites-enabled/ 2>/dev/null
ls -la /etc/apache2/sites-enabled/ 2>/dev/null
```

If nginx is present:

```bash
sudo nginx -T | less
```

(This dumps the full effective config — every server block, every domain it answers for. Feel free to paste just the `server_name` and `listen` lines rather than the whole thing if it's long or you'd rather not share full config details.)

**Why:** This is the single most important thing to see before touching anything. If the website is nginx-served with its own server block, our plan is simple: add one more `server { }` block for a new POS subdomain (e.g. `pos.yourdomain.com`), reload nginx, done — the website's block is untouched. If it's Apache, or something else (a control-panel-managed vhost system), the approach is the same in spirit but the specific files differ, so I need to know which before writing the actual config.

### 5. What database engine the website uses (and whether Postgres already exists)

```bash
which mysql mariadb psql 2>/dev/null
sudo systemctl status mysql 2>/dev/null
sudo systemctl status mariadb 2>/dev/null
sudo systemctl status postgresql 2>/dev/null
psql --version 2>/dev/null
mysql --version 2>/dev/null
```

**Why:** This determines exactly how isolated the POS's data is by construction. If the website runs on MySQL/MariaDB (very common for PHP sites, which most shared-hosting company sites are) and the POS needs Postgres, then the POS's Postgres instance is a completely separate piece of software from day one — no shared server, no shared credentials, nothing to carefully partition. If Postgres is *already* running for some reason, we'd instead run the POS as a second database + role inside that same instance (the plan `DEPLOYMENT_ARCHITECTURE.md` describes), which is still safe but is a different, more careful setup than "just install Postgres fresh."

### 6. SSL / certificates

```bash
sudo certbot certificates 2>/dev/null
ls -la /etc/letsencrypt/live/ 2>/dev/null
```

**Why:** If the website uses Certbot/Let's Encrypt already, we use the exact same tool to get a certificate for the new POS subdomain — one more line in an existing, working process, not a new system. If Hostinger is managing SSL for the site through its own panel instead (also common), that's fine too, it just means the POS subdomain will get its own cert issued independently and won't interact with the website's at all.

### 7. Firewall — the OS level, not just the Hostinger panel

```bash
sudo ufw status verbose
sudo iptables -L -n -v
```

**Why:** The hPanel firewall showing "0" rules only tells us about Hostinger's *layer* (a feature sitting in front of the VPS). The server's own firewall (`ufw`, or raw `iptables`) is a separate thing and may or may not be active. We need to know this before opening any new ports for the POS (its own subdomain will go through port 443 like everything else, so likely no new ports needed at all — but I want to confirm nothing surprising is locked down first).

### 8. DNS / domain management

Not a server command — just tell me: where is the domain's DNS currently managed (Hostinger's own DNS zone editor, or somewhere else like Cloudflare)? This determines where you'll add the `pos.yourdomain.com` (or whatever subdomain you pick) A record pointing at `187.127.204.34`.

### 9. Existing backups / scheduled jobs

```bash
crontab -l
sudo crontab -l
ls -la /etc/cron.d/
```

**Why:** Good to see if the website already has an automated backup job (database dump, file backup) running via cron, separate from Hostinger's own snapshot feature. If so, the POS gets its own equivalent job added alongside it — same mechanism, new target, nothing shared.

---

## Once you send back the results

I'll turn this into the concrete, file-level plan: an actual `docker-compose.yml` for the POS stack (Django + Postgres + the built frontend, likely served as static files through nginx), the nginx server block for the new subdomain, the Certbot command for its SSL, and memory limits sized to whatever `free -h` actually showed. This is intentionally the *next* step, not this one — writing config against a real, known server is far safer than writing it against assumptions and hoping it fits.

---

## CI/CD plan (conceptual — for when we're ready to build it)

Since the repo is on GitHub and you want auto-deploy on push to `main`, here's the shape this will take. Nothing below needs to be built yet — this is so you know what's coming and why.

**The pipeline has two jobs, and the second only runs if the first passes:**

1. **Test job** (already partially exists — you have a `ci.yml` from the security-fixes phase). This runs on every push and every pull request: backend `pytest`, frontend `npm run test`, plus the linting. This is the gate — if tests fail, nothing gets anywhere near the server.

2. **Deploy job** — runs only on a push to `main`, and only after the test job succeeds. This is what "auto-deploy on push to main" means concretely: merging a PR into `main` (or pushing directly to it) kicks off tests, and if they pass, the pipeline SSHs into your VPS and rolls out the new version.

**How the deploy step itself works, at a high level** — this is the part that has to be careful given the shared server:

- GitHub Actions connects to your VPS over SSH using a deploy key (a dedicated SSH key pair, generated just for this, with its *private* half stored as a GitHub Actions secret — never in the repo, never visible in logs).
- On the server, it pulls the latest code into the POS's own directory (something like `/opt/pos-system/` — again, its own directory, separate from wherever the website's files live) and runs `docker compose up -d --build` for the POS stack only. This rebuilds and restarts *only* the POS's containers. It has no command that touches the website's process, files, or web server config, because it never needs to — the two stacks are siblings under the same nginx, not one thing.
- Database migrations run automatically as part of that same deploy step (`docker compose exec backend python manage.py migrate`) so schema changes ship with the code that needs them.
- A short health check at the end (curl the POS's own health endpoint) confirms the new containers actually came up before the job reports success — if it fails, you get a GitHub Actions notification immediately rather than finding out from a confused cashier.

**What this deliberately does *not* do:** touch nginx's config on every deploy (that only changes when *we* deliberately edit it, not automatically), restart the whole server, or run anything with the reach to affect the website's containers/processes, since the deploy script only ever refers to the POS's own compose project by name.

This is the same "additive, sibling, never inside" principle as the server-side plan above, just automated.

---

## What I need from you to move forward

Run the numbered commands in the checklist above (1 through 9), and let me know the DNS answer for item 8. Paste the output back — trimmed or summarized is fine if any of it feels like more detail than you want to share (e.g. you can just tell me "nginx, and here are the `server_name` lines" rather than the full config dump). Once I have that, I'll write the actual `docker-compose.yml`, nginx config, and the deploy workflow file, all sized and shaped to what's really running on your server.
