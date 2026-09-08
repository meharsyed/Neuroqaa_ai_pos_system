# Deployment architecture: shared Hostinger KVM1 vs. a dedicated server

**Question on the table:** deploy this POS on the Hostinger KVM1 (1 vCPU, 4 GB RAM, 50 GB disk, 4 TB bandwidth, Ubuntu 22.04) that already runs Neuroqaa.ai's own website, or buy a separate VPS (~25–30k PKR/yr) dedicated to this client.

**Short answer: put it on the KVM1 you already have, done properly — not as a shortcut, but because it's genuinely the better call at this traffic level and this budget, with a specific, written trigger for when to split it out.** The rest of this doc is the reasoning, so it's a decision you're making with full information rather than one made *for* you by the budget.

---

## The budget context, stated plainly

You committed to 80,000 PKR **all-in** — server, hosting, and the deployed working system — to a client for what turned out to be more system than that price assumed. That's not a reason to go back to the client; it's a reason to be deliberate about where the remaining margin goes. A new dedicated VPS at 25–30k/year is 31–38% of the *entire* engagement's budget spent on infrastructure the traffic profile doesn't actually require yet. Spending it there because it's the "textbook correct" architecture, when a well-isolated shared box serves the same client outcome, is optimizing for a diagram instead of for the business relationship you're explicitly trying to build. The right amount of infrastructure is the amount the actual load justifies — not the maximum available, and not the minimum that technically boots.

---

## What the traffic profile actually is

You said it yourself: the website has low traffic, and the POS is used only by the client's internal staff — no public-facing load on the POS at all. This matters more than the raw spec numbers, because "1 vCPU, 4 GB RAM" sounds small in the abstract but is not small for this actual workload:

- A handful of staff terminals hitting a Django+DRF API for POS operations (create a sale, look up a product, print a receipt) is a light, bursty load — seconds of activity around each transaction, then idle. This is nothing like a public storefront absorbing concurrent anonymous traffic.
- The company website, by your own description, isn't heavily trafficked either.

Two light, uncorrelated workloads sharing one box is exactly the case shared hosting is good for. The risk profile changes completely if either workload becomes public-facing and high-traffic — that's the trigger condition below, not the current state.

---

## Answering the specific technical question: do I need two Postgres databases?

**One Postgres *server* process, two separate *databases*, two separate *roles* — not two Postgres installations.**

```sql
CREATE DATABASE pos_db;
CREATE DATABASE website_db;   -- or whatever the site already uses

CREATE USER pos_app WITH PASSWORD '...';
GRANT ALL PRIVILEGES ON DATABASE pos_db TO pos_app;
-- pos_app has no grants on website_db at all — it cannot see it, connect to it,
-- or query it, even if the POS app itself were fully compromised.
```

This is the standard, correct way to run two unrelated applications' data on one Postgres instance: the isolation that actually matters — one compromised app can't read or write the other's data — comes from database-level permissions, not from running two separate `postgresql` processes. Running two full instances would cost you meaningfully more RAM (each instance reserves its own `shared_buffers`, connection overhead, background workers) for no real security gain over correctly-scoped roles. One instance, two databases, is both the more efficient and the more standard choice here.

---

## Pros and cons, stated straight

### Shared KVM1 (existing box)

**Pros**
- Zero marginal hosting cost — the box is already paid for.
- One server to patch, monitor, and reboot for your own maintenance windows, instead of two.
- Faster to stand up — DNS/subdomain and SSL are the only new pieces; the box, OS, and your own familiarity with it already exist.
- Keeps 25–30k/year of margin in an engagement that's already tighter than it should be.

**Cons — and these are real, not hypothetical**
- **Shared fate.** A runaway process, a full disk, or a bad `apt upgrade` on this box now risks your own company's website *and* a live client system going down together, possibly during the client's business hours. This is the one argument that actually matters here, and it's why "done properly" below isn't optional.
- **Coupled maintenance windows.** You can no longer patch or reboot the website on your own schedule without it being a POS maintenance window too, and vice versa.
- **CPU contention under 1 vCPU.** If the website ever gets an unexpected traffic spike (a shared link goes around, a bot crawl, a bad plugin loop), it can starve CPU from the POS's gunicorn/Postgres processes during that window. Tolerable for an internal tool where "a page took 3 seconds instead of 300ms for ten minutes" is an inconvenience, not a disaster — worth knowing, not worth panicking about.
- **A perception cost, not a technical one.** If the client (or their more technical staff) ever asks where their system lives, "on the same box as your marketing site" is a slightly awkward sentence to say out loud, even when it's completely safe in practice. A clean subdomain and the client never needing to know the underlying box is shared makes this a non-issue — but it's worth being aware of the optics, especially given you're trying to build a referral-generating relationship here.

### Dedicated new VPS

**Pros**
- True fault isolation — nothing about your website can ever affect this client's uptime, and nothing about a future client's system can affect this one.
- A cleaner story if this client (or the next one) ever wants to know exactly what their system runs on, with nothing shared.
- One less thing to reason about when debugging — resource contention between two unrelated workloads is eliminated as a variable entirely.

**Cons**
- 25–30k/year against an 80k *total* budget is a lot of margin gone to a risk (resource contention on a low-traffic internal tool) that's real but currently small.
- It's still just one box — you haven't bought redundancy, you've bought separation. A dedicated VPS can still go down; it just won't take your website with it.
- More infrastructure to patch and monitor from day one, for a client relationship that's just starting and where you don't yet know if there will be a second or third system to justify the operational overhead.

---

## The recommendation, and how to do it properly

**Deploy on the existing KVM1**, with these specific measures — this is the difference between "cutting a corner" and "making a sound, defensible engineering call," and it's worth actually doing all of it, not treating it as optional polish:

1. **Containerize the POS stack with Docker Compose** — gunicorn + the Django app in one container, Postgres either as a second container or the box's existing native Postgres (see above) with a dedicated database/role. This is what makes the eventual migration to a dedicated box, if it ever happens, a `docker compose down` + copy the compose file and a `pg_dump` — not a re-architecture.
2. **Set memory limits on the POS containers** (`mem_limit` / `deploy.resources.limits` in the compose file) so a leak or a bad request pattern in the POS can hard-cap at, say, 1–1.5 GB rather than being free to pressure the website's processes into swapping or OOM-killing.
3. **Add a 2 GB swapfile** to the box if it doesn't already have meaningful swap. On 4 GB RAM running two workloads, this is cheap insurance against an OOM crash — a small performance cost under real pressure, which you're unlikely to hit often at this traffic level, in exchange for "briefly slow" instead of "crashed" as the failure mode.
4. **Put nginx in front of both**, each on its own server block / subdomain, proxying to its own backend port locally (e.g. the website however it's already served, the POS's gunicorn on `127.0.0.1:8001`). Get the POS its own subdomain (`pos.speedtechsolutions.pk` or similar, on whichever domain fits) and its own free Let's Encrypt certificate — this is also where `CORS_ALLOWED_ORIGINS` for `config/settings/cloud.py` gets its value.
5. **Never expose Postgres externally** — bind it to `localhost` only, as should already be the default; worth confirming explicitly on this specific box.
6. **Basic monitoring from day one.** Even a free tier of UptimeRobot pinging the POS's health endpoint, plus a simple daily cron that emails you disk usage (`df -h`) and memory headroom, is enough to catch "the disk is filling up" or "one workload is starving the other" before the client notices anything. With two things sharing one box, this stops being optional.
7. **Check real free disk headroom before committing** — I don't have visibility into how much of the 50 GB the website already uses. Product images (now capped at 10 MB each, realistically averaging much less), the Postgres data, and receipt PDFs will add up slower than you'd expect for a shop this size, but confirm `df -h` shows comfortable room before go-live, not after.
8. **Back up both databases independently** — a `pg_dump` cron for `pos_db` separate from whatever backs up the website's database, ideally shipped off-box (even just to a cheap object-storage bucket or emailed compressed dump) rather than relying solely on whatever snapshot policy Hostinger's KVM plan includes. This was already flagged as the audit's other open item (git-tracked database, now fixed going forward) — this is the production-side equivalent of the same discipline.

## Write down the trigger for when this stops being the right call

Revisit dedicated hosting for this client specifically when **any one** of these happens — put this in writing to yourself now, so it's a plan rather than a reaction later:

- The POS's own transaction volume or staff headcount grows enough that its resource use stops being "light and bursty."
- The client adds a second location/terminal set that meaningfully increases load.
- You sign a second POS client — at that point, decide per-client dedicated boxes vs. a slightly larger shared box on its own merits, with real usage data from this first deployment informing the call instead of a guess.
- The relationship and budget mature past the first renewal, and 25–30k/year stops being 30%+ of the engagement.

None of this is a technical limitation you're working around — it's a staged rollout of infrastructure spend that matches actual demonstrated need, which is the same instinct that makes a startup's first year run lean on purpose.
