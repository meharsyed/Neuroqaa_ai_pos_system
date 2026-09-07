# The quotation print bug, frontend tests, and Urdu

**328 backend tests · 28 frontend tests (new) · lint and tsc clean.**

---

## Run it

```powershell
cd "D:\Neuroqaa Stuff\POS System\pos-system-GT\frontend"
npm install          # one new devDependency — see §2
npm run test         # expect 28 passed
npm run dev
```

The backend is unchanged this round; no new migrations.

---

## 1. Why Print gave you a 401

The quotation Print button was a plain link:

```tsx
<a href="/api/quotations/1/pdf/" target="_blank">Print</a>
```

The access token lives in memory and is attached by an axios interceptor. A
browser navigation is not an axios request — it carries no `Authorization`
header — so DRF answered 401 and showed you its browsable-API error page
instead of the quotation. **My mistake**: the codebase already had the right
pattern in `openReceiptPdf`, and I did not follow it.

Fixed, and generalised into `lib/pdf.ts`:

- **`openApiPdf(url)`** — fetches the PDF through `apiClient` (so it is
  authenticated), opens it as a blob URL, and handles a blocked popup.
- **`blobErrorMessage(err)`** — a second bug found on the way. With
  `responseType: "blob"` the *error body is a Blob*, so the usual
  `err.response.data.detail` is `undefined` and the toast said *"Request
  failed with status code 401"*. It now reads the blob back as text, parses
  it, and turns 401/403 into something a cashier can act on
  ("Your session has expired. Sign in again and retry.").

That second bug was already live in `openReceiptPdf` and the khata statement —
both now go through the same helper.

**And a test so it cannot come back**: `api-links.test.ts` scans every source
file and fails on any `href` or `window.open` pointing at `/api/`. It is the
kind of mistake that looks completely correct in review, so it is pinned
rather than remembered.

### The rest of the quotation flow

I walked every endpoint the UI calls — create, list, detail, to-cart, status,
revise, search, filter, profiles, PDF, and the two error paths. All correct.
One thing I did not want to assume, now tested: **revising only the lines does
not wipe the tax rate, discount, installation charge or validity.** The revise
endpoint takes a partial payload, and had DRF applied the serializer's
declared defaults to absent fields, changing one quantity would have silently
blanked the rest of the quotation.

---

## 2. Frontend tests

There were none — Vitest was configured with `passWithNoTests: true`, so
`npm run test` reported green with zero test files, and CI ran that. **28 tests
now**, and `passWithNoTests` is off so an empty suite fails.

**`PaymentModal` — the tender arithmetic** (16 tests). This is the one piece
of frontend logic that decides how much money changes hands. Covered: change
on an overpayment, the cash cap (Rs 50,000 handed over on a Rs 10,000 bill
settles Rs 10,000, not Rs 50,000), part payments onto the khata, the block when
there is no customer to bill the rest to, the credit limit and the "collect at
least Rs X more" message, two tenders splitting one bill, the refusal to
overpay by card, installation charges, and a pure khata sale sending no
tenders at all.

**Mutation-tested.** Removing the cash cap failed 2 tests; removing the
credit-limit block failed 2; allowing a shortfall with no customer failed 1.

### Two real problems the tests exposed

- **`Blob.prototype.text()` does not exist in jsdom.** My error helper depended
  on it, so the test could only ever assert the fallback. It now uses
  `FileReader` when `.text` is missing — which also covers older browsers.
- **`@testing-library/dom` was never declared.** `@testing-library/react` v16
  made it a peer dependency. It happened to be present on a fresh install and
  absent on your machine's older one, so `npm run type-check` passed for me and
  failed for you depending on nothing but npm's mood. Now in `devDependencies`
  — **which is why you need `npm install`, not `npm ci`, this once.**

I ran these in a Linux container rather than asking you to, because this
machine's `node_modules` holds the Windows rollup binary. Worth knowing the
loop exists.

---

## 3. Urdu

### The guardrail first

`t()` falls back to the key when a translation is missing, so a gap renders the
literal string **`nav.khata`** on screen, in front of a customer. Nothing
catches that except a person switching language and reading every page.

`translations.test.ts` now fails if the two dictionaries diverge — missing
keys, extra keys, blank strings, or a `{placeholder}` present in one language
and not the other (a dropped `{pct}` leaves a sentence with a hole in it).
There is also a dev-only console warning on every miss.

**It found one immediately: `nav.khata` had no Urdu.** The sidebar has been
rendering the literal text `nav.khata` in Urdu mode. Fixed.

### What is translated

About 200 new keys covering **Products, Bills, Customers, Khata, Returns,
Shifts and Quotations** — the counter-facing screens — plus a shared `common`
set. Page headers and the main controls are wired up.

### What is deliberately not, and why

**Audit Reports, Activity Log, Settings and Staff stay in English.** These are
owner-only screens of accounting and administration terms — gross margin,
COGS, reconciliation, variance, throttling — and Pakistani business people
overwhelmingly read those in English. Translating them would make the app
worse, not better, and the shop owner who reads a P&L is the one who chose an
English POS.

That is now a **stated policy** rather than the arbitrary situation before
(three pages translated because they happened to get done first).

### What still needs a person

**The Urdu needs a native speaker's pass before it goes to the shop.** I am
reasonably confident in it, but "reasonably confident" is not what you want on
text a customer reads. It is one sitting with someone at Speed Tech and a
list of ~200 strings in one file.

There is also more depth available: table headers and sub-components inside
those pages are still English. Getting them means editing inside nested
components where `t` is not in scope — which is exactly where my first attempt
introduced six type errors before I backed it out and did it properly. Worth
doing, but as its own careful pass rather than bolted onto this one.

---

## What to test

1. **Quotations → Print.** It should open the PDF, not a DRF error page.
2. Sign out, then click Print from a stale tab → a readable *"Your session has
   expired"* message, not "Request failed with status code 401".
3. Khata → **Statement**, and Bills → a receipt PDF — same path, same fix.
4. Create a quotation with tax + installation, then **Revise** just a quantity
   → the tax and installation are still there.
5. Switch to **Urdu** in the sidebar → the counter pages read in Urdu, and
   nothing anywhere shows a raw key like `nav.khata`.
6. `npm run test` → 28 passed.

---

## Still open

1. **Backups** — sequence with the Postgres move (see Phase 11 §backups).
   Unchanged and still the largest risk.
2. **The brand ramp in dark mode** — `text-teal-600` at 31% lightness, 26 uses,
   thin on a dark card. Needs an eye on a real screen.
3. **Urdu inside page sub-components** — table headers, dialogs, empty states.
4. **A native Urdu review** of the ~200 strings now in `translations.ts`.
5. **Serving the frontend from Django** so the shop runs one process.

---

*Applied and verified · 328 backend tests · 28 frontend tests · three mutations introduced and caught · quotation flow walked endpoint by endpoint*
