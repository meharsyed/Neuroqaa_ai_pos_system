# Two-business isolation: feasibility, options, and a recommendation

**Nothing in this document has been implemented.** No code, settings, or infrastructure has been touched for this — this is analysis only, as asked. Deployment work from Phases 15–16 is untouched and unaffected by this pause.

---

## Restating what the client asked for

One client (Speed Tech Solutions), two separate businesses — the Quetta retail shop and a separate wholesale security-tech distribution business — and he wants each business's records, stock, bills, audit trail, khata, and customers **completely separate**, each with its own owner/staff accounts and its own login, while it all runs as one deployed system on one domain/server. The open question you're asking: is "completely separate data" and "one combined deployment" actually compatible, and if so, which way of building it is genuinely the right one — not just the first one that technically works.

## What the codebase already has — and doesn't

Before comparing options, it's worth being precise about where the current system actually stands, because it changes how much work each option really is.

Nearly every model in the system — `Product`, `Category`, `Inventory`, `StockMovement`, `Supplier`, `Customer`, `Sale`, `SaleItem`, `Quotation`, `BusinessProfile`, `ActivityLog` — already carries a `tenant_id` field. That looks, at first glance, like the multi-tenancy groundwork is half-done. It isn't, and it's important to be clear-eyed about that rather than assume it: I checked, and `tenant_id` is hardcoded `default=1` everywhere, is never read by a single `get_queryset()`, a permission check, or a filter anywhere in the codebase, and there is no `Tenant`/`Business`/`Store` model, no middleware that resolves "which business is this request for," and no per-user, per-business role assignment — a `User` has exactly one global `role` (owner/manager/cashier/stock clerk), full stop. The `Setting` model (tax rate, receipt template, and similar shop-wide config) is a single global table keyed uniquely by setting name — there is no per-tenant version of it at all. In short: `tenant_id` is a column that was added speculatively at some point and never wired to anything. It buys you nothing today. Any option that leans on it needs to build the entire enforcement layer from nothing, not extend something that half-exists.

That finding is the single biggest factor in the recommendation below.

## Three ways to actually build this

### Option A — two independent copies of the same system, sharing only the physical box

Run the exact same POS codebase twice, as two completely separate applications: two Docker containers, two Postgres databases (both under the one Postgres server already running on your KVM1 — the same "one server, separate databases" pattern already planned for isolating the POS from your company website), two `.env` files, two nginx server blocks, and either two subdomains (`retail.yourdomain.com` / `wholesale.yourdomain.com`) or two separate domains if each business has or wants its own brand identity. Each is, as far as the software is concerned, a totally ordinary single-business POS — because that's exactly what it already is today, unmodified. Two logins because there are literally two separate websites; the client holds two separate sets of credentials and goes to whichever URL he needs.

**What this costs**: essentially nothing beyond what's already planned. It reuses `Dockerfile.prod`, the `docker-compose.prod.yml` pattern, and the whole CI/CD pipeline from Phase 16 as-is — the only real addition is running that same pipeline against a second `.env.prod` and a second nginx block, and the GitHub Actions deploy step would push to two directories on the server instead of one. No application code changes, no data model changes, no new risk introduced into the app itself.

**What it isolates**: everything, completely, by construction. Two different databases cannot leak into each other no matter what query anyone writes, today or in a feature added two years from now — the isolation is physical, not a rule someone has to remember to follow. This matches "stocks, bills, audits, khata, customers, and everything" exactly, with zero exceptions to reason about.

**The real cost is operational, not technical**: it's two things to patch, two things to back up, two things to monitor, two sets of migrations to run on every deploy. On a 1-vCPU box this is genuinely fine resource-wise — the box is using 390 MB of 3.8 GB right now, and two lightweight internal-staff-only Django apps are not going to change that meaningfully — but it is more moving parts than one, and worth being honest with the client (and yourself) that this is closer to "build and run two POS systems" than "add a feature to one."

### Option B — one shared system, real multi-tenant data model

Build actual multi-tenancy into the application: a real `Business` model, a `Membership` table linking users to businesses with a role each, a piece of middleware that resolves which business a request belongs to (from the logged-in user's selected business, or from subdomain), and then — critically — retrofitting every single existing query in the system to filter by that business. Every `ViewSet.get_queryset()`, every report aggregation, every serializer that does a lookup, the sales-numbering sequence, and the currently-global `Setting`/`BusinessProfile` tables would all need to change from "the one and only shop" to "this specific business, and never any other." Given the finding above — `tenant_id` exists but enforces nothing today — this is not a light retrofit. It's designing and building the entire multi-tenancy layer from scratch, then auditing the whole existing codebase against it.

**What this buys you**: one deployment, one database, one thing to patch and monitor and back up — genuinely more efficient at scale, and the right architecture if the goal were eventually to sell this same POS to many unrelated customers on shared infrastructure (a real SaaS product).

**What it costs**: meaningfully more engineering time than Option A, and — this is the part that matters most given what the client explicitly asked for — the isolation becomes a *code-correctness property* instead of a structural guarantee. It's real and it's enforceable, but it depends on every current query and every future feature, forever, remembering to filter by business. One missed `.filter()` in a report, an admin page, or a new endpoint six months from now is a leak between two commercially separate businesses — potentially one business's sales figures or customer list becoming visible to staff of the other. For two businesses that the client has explicitly asked to be kept completely apart, that's a materially scarier failure mode than "a server got misconfigured," and there's no automated safety net today (no test suite that specifically tries to prove cross-tenant isolation) to catch a regression before it reaches production.

### Option C — one process, dynamic per-request database routing

A middle path: one Django container, but a database router that picks which of two databases to use per-request based on the domain/subdomain in the request. This gets Option A's real, physical data separation (two databases, genuinely un-leakable into each other) while running fewer containers than Option A. I'd steer away from this one: it takes on real implementation complexity (a custom router, careful handling everywhere a management command or background task runs outside a normal request/response cycle) to save "one more Docker container" on a box that currently has 3.1 GB of headroom sitting idle. It captures some of Option B's fragility (a subtle bug in the routing logic misroutes a request) without saving meaningfully more than Option A does. Mentioning it for completeness, not recommending it.

## The recommendation

**Option A.** Two independent instances of the system you already have, sitting on the same server, each with its own database and its own subdomain (or domain), reusing the deployment pipeline you're already building in Phase 16 almost unchanged. This is less work, ships faster, and gives the client a stronger, structural version of exactly what he asked for — "completely separate" data that is *actually* completely separate, not separate-by-convention. It also keeps the codebase itself exactly as simple as it is today, which matters if you ever deploy this same POS for a future, unrelated client: you'd do the same thing again (a third independent instance), rather than that future client's data sharing a codebase-level tenancy mechanism with this one.

Option B is the right call only if the actual goal is different from what's described here — building this POS into a real multi-tenant product you sell to many unconnected customers on shared infrastructure. That's a legitimate, valuable direction for Neuroqaa as a product, but it's a different, larger investment than "give one existing client two isolated instances of their system," and I wouldn't bundle that scope into this request.

## How this actually looks, concretely, once you decide to proceed

Nothing below is built yet — this is what "yes, go with Option A" turns into:

- Two Postgres databases and roles on the already-running Postgres 14 server (`pos_retail_db` / `pos_wholesale_db`, or whatever names fit), exactly the same additive step already planned in `deploy/server-setup.md` for the one POS database — just done twice.
- Two `.env.prod` files, two `docker-compose.prod.yml`-style service definitions (or two entries in one compose file — either works), each pointed at its own database, its own `ALLOWED_HOSTS`, and its own `CORS_ALLOWED_ORIGINS`.
- Two nginx server blocks — one per subdomain/domain, each proxying to its own backend container on its own local port (e.g. `127.0.0.1:8001` and `127.0.0.1:8002`).
- Two Let's Encrypt certificates (Certbot handles this exactly as it already will for the first instance — no new tooling).
- The GitHub Actions deploy workflow already being built in Phase 16 extends to push to both, rather than being rebuilt — same image, deployed twice, to two directories with two env files.
- No changes at all to the Django/React application code itself.

## One thing worth raising with the client, not just with the server

The original 80,000 PKR engagement was scoped around delivering one POS for the retail shop. Standing up a second, fully isolated system for a second business — even though the *marginal infrastructure cost* on your existing KVM1 is close to zero — is genuinely more delivery and more ongoing support surface than that scope covered: a second thing to test, monitor, back up, and support going forward. That's worth a short, plain conversation with the client about scope or timeline, separate from the technical feasibility question, which is a clear yes.

## What I need from you to move forward, once you decide

Nothing yet — this was deliberately scoped as analysis only, per your instruction. When you're ready to proceed, the natural next steps are: confirm Option A is the direction, decide on the domain/subdomain structure for the second business, and then this becomes a straightforward extension of the Phase 15/16 deployment work already in progress rather than a new design effort.
