# Offline resilience — honest effort scoping

**Analysis only, nothing implemented.** This breaks down the six requirements you were given, against what's actually in the codebase today, so the effort numbers are grounded rather than generic.

---

## The one-paragraph honest answer

Two of these six items are cheap and should basically just be done. The other four are, together, one real project — not a checklist of small features — and the single biggest cost in it isn't the offline storage or the sync logic, it's that **all of your pricing, tax, discount, and stock-check logic lives only in the Python backend today**, and "the POS keeps working while offline" means a meaningful slice of that logic has to be duplicated in the browser, correctly, and kept in sync with the backend forever after. That's the part that makes this a multi-week undertaking rather than a multi-day one, and it's worth having that expectation set correctly before scoping a price or timeline with the client.

---

## Item by item

### 5. Clear offline/online status displayed to staff — **small, and partly already there**

You already have an `OfflineBanner` component wired into the app, and it already does roughly the right thing: pings the API, shows a banner with a retry button when it can't reach the server. Worth knowing before quoting this as "already done" though — I checked, and it currently calls `/api/health/`, and **no such endpoint exists anywhere in the Django URL config**. Today, in production, that means the banner's connectivity check 404s every single time, and its `catch` block treats *any* failure — including a 404 — as "offline." I haven't verified this in a running instance, but reading the code, this looks like it would show "Working in offline mode" permanently, even when the connection is completely fine. That's a live bug worth fixing on its own, separate from everything else here — it's a one-line backend addition (a trivial `health` view) plus confirming the frontend logic behaves once it gets a real 200 back.

Beyond that fix, this item mostly rides on item 2 existing: right now the banner can only say "online" or "offline," but once there's a local pending-transaction queue, it should also say *how many* sales are waiting to sync — which is a small UI addition once the queue itself exists, not new complexity of its own.

### 6. Data backup and disaster recovery — **small-to-medium, and unrelated to the offline work**

This one isn't a frontend feature at all — it's an operational task that's already scoped in `docs/DEPLOYMENT_ARCHITECTURE.md` (an independent `pg_dump` cron for the POS's database, shipped off the box) and was flagged as a "do this right after the first deploy" item in the Phase 16 plan. It needs: a scheduled dump job, somewhere off-server to send it (even a cheap object-storage bucket or an encrypted copy to cloud storage is enough at this scale), and — the part people skip — an actual tested restore, at least once, so "we have backups" isn't a belief nobody's verified. This is genuinely independent of whether you build any offline capability at all, and I'd recommend just doing it as part of finishing the deployment, regardless of what you decide on the other five items. Right now, the honest state is: the whole shop's data lives in one Postgres database with no backup at all — that's a real, current gap.

### 2. Local transaction storage during offline periods — **medium-large, fully new**

I checked the frontend's dependencies: there's no IndexedDB library, no `localForage`/`dexie`, no service worker, no offline-storage infrastructure of any kind today — `zustand` (in-memory state) is the closest thing, and it doesn't persist across a page reload, let alone a browser restart. This needs an actual new subsystem: a durable local store (IndexedDB via a small library like Dexie is the standard, low-risk choice) holding a queue of "things that happened while we couldn't reach the server," and the checkout flow rewired to fall back to writing into that queue instead of just failing when the API call doesn't come back.

The scoping question that matters most here: **which operations get this treatment?** Checkout/sales is the obvious, highest-value one — it's the thing happening at the counter with a customer waiting. Stock-ins, khata payments, customer edits, quotations, and returns are all separate mutation types that would each need their own offline handling if you wanted everything covered. I'd strongly recommend scoping this to **checkout only** for a first version, and having every other action simply say "requires an internet connection" while offline — trying to cover every mutation in the app multiplies this effort by roughly however many mutation types you include, each with its own version of the problem below.

### The hidden cost inside item 2: checkout's numbers are computed on the server, not the browser

This is the part I want to be very direct about, because it's the actual size of this project, more than the storage or sync mechanics. Today, when a cashier checks out a cart, the browser sends the cart to the backend, and the backend — not the browser — computes the price, tax, any discounts, checks real stock levels, and decrements inventory. If the POS is offline, there is no backend to ask. So a *genuinely* offline checkout — one where the cashier can still ring up a sale and hand over a correct receipt with the right total while the internet is down — needs a second copy of that pricing/tax/discount/stock-check logic written in the browser, using whatever product/price/stock data was last synced down. That copy has to stay correct, and has to stay in sync with the backend's version every time a pricing rule, tax rule, or discount rule changes in the future — otherwise the two totals drift apart and you get a genuinely bad failure mode: a receipt handed to a customer with a number that doesn't match what the server thinks happened.

There's a materially cheaper version of "offline capable" worth naming explicitly: the POS **records** what the cashier did (items, quantities, a snapshot of the last-known prices) durably and locally, so nothing is lost, but treats the computed total as provisional/unconfirmed until it syncs — with a visible "pending — will confirm on reconnect" state on the receipt, rather than silently presenting an offline-computed number as final. That's a real, honest, and much smaller version of this requirement, and for a lot of small retail shops it's the right tradeoff — the alternative (a fully correct parallel checkout engine in the browser) is the kind of thing that's worth the investment for a business processing thousands of transactions a day, less obviously so for a shop this size. Worth deciding deliberately rather than defaulting to the harder version because it sounds more complete.

One more thing this surfaces: with multiple staff terminals (your own notes on this deployment mention "a handful of staff terminals"), two terminals both offline at the same time, both selling the last unit of the same product, is a real scenario — there's no way to prevent that without a live connection to check real stock, full stop, no matter how this is built. Every offline POS system handles this the same way: let it happen, flag the resulting negative/oversold stock at sync time for a human to look at, rather than trying to engineer around a problem that fundamentally requires real-time coordination you don't have while offline.

### 3. Automatic synchronization after connectivity is restored — **medium, builds directly on item 2**

Once a local queue exists, this is: detect the connection coming back (the fixed version of the item 5 health check), walk the queue in order, replay each entry against the real API, and handle three outcomes per item — it succeeds cleanly, it succeeds with an adjustment worth telling someone about (e.g., stock ran out in the meantime), or it fails and needs a human to look at it. The mechanics of "loop through a queue and POST each one" are not the hard part; deciding what happens on each of those three outcomes, and showing it to the right person clearly, is.

### 4. Prevention of duplicate transactions during synchronization — **medium, and has to be designed in from the start, not bolted on after**

This needs a change on both ends, not just the frontend: a unique idempotency key generated on the browser the moment an offline sale is created (not when it's synced — if the key were generated at sync time, a sync request that times out but actually succeeded on the server would get retried with a brand-new key and create a real duplicate sale). The backend needs a matching change: a uniqueness constraint on that key on the `Sale` model, and the create endpoint changed so that resubmitting an already-processed key returns the existing sale instead of erroring or creating a second one. This is a real migration and a real serializer/view change, small in isolation but only correct if it's built alongside items 2 and 3 from day one, not added afterward — retrofitting idempotency onto a queue that wasn't designed around it is how duplicate-charge bugs happen in the wild.

### 1. "POS should continue operating during temporary outages" — this is the umbrella, not a separate task

This line is really the sum of 2, 3, and 4, scoped to whichever operations you decide to cover (checkout, recommended as the only one for a first version) and whichever tradeoff you pick on the hidden cost above (recorded-but-provisional vs. fully computed offline). There's no separate work here beyond those — but it's the one that needs a clear, explicit scope decision before any of the others get designed in detail, because "continue operating" can mean anything from "don't lose a sale" (achievable in a couple of weeks) to "the cashier never notices anything's different" (a much bigger, ongoing commitment).

---

## What I'd actually recommend, if asked

Do item 6 now, independent of everything else — it's cheap, it's already half-planned, and the current lack of any backup is a real risk regardless of this conversation. Fix the `/health/` endpoint while you're in there, since it's a live bug and a five-minute one to fix. Then scope items 1-4 as one project, not four: offline support for **checkout only**, using the "recorded-but-provisional" version of the total rather than a full parallel pricing engine, with idempotency keys designed in from the first line of code rather than added later. That's a real, honestly-scoped few weeks of work, not a quick add-on — and it's the version of "keeps working offline" that's actually proportionate to a shop this size, versus building the kind of offline-sync engine a much larger, multi-location retailer would need.

## What I need from you to move forward

Nothing yet — this was scoping only. When you're ready, the decisions that actually shape the design are: which operations beyond checkout (if any) need offline support, whether "recorded-but-provisional" or "fully computed offline" is the right tradeoff for this client, and whether multiple terminals can realistically be offline and selling from the same stock pool at the same time (which changes how much the sync-conflict handling needs to explain to whoever reviews it afterward).
