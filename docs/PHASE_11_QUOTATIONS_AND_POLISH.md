# Quotations, the palette rule, and the fixes from your testing

**327 backend tests pass; `npm run lint` is green for the first time; `tsc` clean.**

---

## Run it

```powershell
cd "D:\Neuroqaa Stuff\POS System\pos-system-GT\backend"
.\venv311\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
python manage.py migrate      # quotations + a default letterhead
pytest -q                     # expect 327 passed
python manage.py runserver
```

```powershell
cd ..\frontend ; npm run dev
```

---

## Your three fixes

### 1. Product placeholders

`ProductModal` still suggested *Blue Ceramic Tile 30×30* and *TILE-001* from
the previous shop. Now *4MP IR Bullet Camera* / *BUL-4MP-IR*, with prices to
match. The same tile examples were also in the **receipt template previews** on
the Settings page (with "NEUROQAA SANITARY & TILES" as the shop name) and in
the Returns reason placeholder — all four replaced.

### 2. The gap in the checkout totals

Every totals row was `justify-between` across the whole cart pane, so on a wide
till screen the label sat at the far left and its number a thousand pixels away
at the right. The totals column is now capped and pushed right, which puts each
label beside its own number and mirrors how the same figures stack on the
printed bill. Label sizes and the number column were also a mix of `text-xs`
and `text-sm` — all one size now, so the column reads straight down.

### 3. The installation line on the invoice

You were right that it read as just another discount row. It now has its own
tinted band, a **+** to say it is added rather than deducted, the label in
bold teal, and the technician named underneath in small type. **Goods total**
above it is bolded with a rule, so the goods arithmetic visibly closes before
the labour line starts. Same treatment on the thermal slip and the web bill.

### A bug in the screenshots you sent

Look at the two receipts for sale **SALE-20260906-00045**:

- the A4 invoice says **Tax (21.5%)**
- the thermal slip says **Tax (22%)**

The slip formatted the rate with `:.0f`, which rounds. Two documents, one sale,
two different tax rates — on a bill headed TAX INVOICE. Fixed to match the
invoice, with a test that fails if either drifts again.

---

## Quotations

### Not a Sale with a flag

A quotation must not move stock, must not appear in revenue, must not take a
`SALE-` number, and must be able to list things the shop does not stock. Adding
a status to `Sale` would have meant auditing every query in the system for "and
not a quotation" — the same trap as folding installation into `total_paise`.
So: `Quotation`, `QuotationItem`, `BusinessProfile`, in their own module.

The first five tests are all negative, because those are the properties a
future refactor is most likely to break:

```
it does not move stock
it does not appear in revenue
it creates no sale
it never takes a sale number
it touches no customer balance
```

### The off-catalogue line

`QuotationItem.product` is **nullable on purpose**. A quotation routinely lists
work the shop does not stock — *"Cat-6 cable, 180m — supplied and laid,
Rs 36,000"* — and being unable to write that line is exactly what sends people
back to Word. The button says **Item not in stock**; type a description and a
price and it is a line like any other.

A catalogue line stores its **own** name, sku and price rather than reading
through to the product. A quotation is a document: it has to keep saying what
it said on the day it went out even if the product is later renamed or
repriced. There is a test that renames and reprices a product and asserts the
quotation is unmoved.

### Letterheads, not free text

You chose named business profiles, and the migration builds the first one from
your existing shop settings — so the first quotation prints properly without
anyone visiting Settings. Add a second identity (a separate entity for
corporate tenders, say) and pick it from the dropdown on each quotation. Only
owners and managers can edit a letterhead; anyone may quote under one.

### The parts that make it worth building

- **To till** — hands the quotation to the checkout with its lines, discount,
  tax rate and installation charge already filled in, and records which
  quotation the sale came from. That is what turns quoting into the front of
  a pipeline instead of a nicer Word.
  **Off-catalogue lines cannot come across** — there is no stock to deduct —
  so they are counted and named in a banner at the till rather than silently
  dropped. That was the one place this could have quietly lost money.
- **Revisions** — revising keeps the number and bumps to *rev 2*, so a
  negotiation is one document that moves rather than a pile of near-identical
  ones. The number the customer was given first still finds it.
- **Validity** — "Valid until 06 Oct 2026" is printed, which stops a customer
  returning in December holding you to a September price.
- A converted quotation cannot be revised.

### The printed quotation

Same typography and rules as the invoice so it plainly comes from the same
shop, but headed **QUOTATION**, carrying no invoice number, and with
*"Quotation — not a tax invoice"* at the foot of every page. Off-catalogue
lines are marked *"Supplied / arranged to order"*. I rendered a four-line
quotation with discount, tax, labour and notes and looked at it.

One thing that caught: `f"{Decimal('17.00'):g}"` gives **"17.00"**, not "17" —
`:g` trims trailing zeros on a float, not a Decimal. The quotation printed
*Tax (17.00%)* where the invoice for the same rate prints *Tax (17%)*. Fixed
and tested.

---

## The palette rule — and a correction

I have to correct what I told you twice.

I reported **219 raw palette classes across 17 files**. That number was
literally right and materially wrong. `tailwind.config.js` **redefines the
`green` and `teal` ramps to point at this project's brand CSS variables**, so
`text-teal-600` is already a design token here. 104 of the 219 were those two.
The genuinely raw ones — red, amber, orange, yellow, blue — were **112**.

Worse, I said swapping them for `text-warning` and `bg-success-bg` would fix
dark mode. **It would not have.** The semantic tokens had no dark values
either: `--success`, `--warning`, `--destructive`, `--info` and the whole
`--n-*` neutral ramp were defined once, in light mode. So every status panel in
the app — the credit-limit warning, the low-stock badge, the drawer variance —
kept its 94%-lightness background and rendered as a near-white box floating in
a dark interface. Converting a raw class to a token changed which near-white
box it was.

**So the actual fix was in `src/index.css`, not in 17 component files:** dark
values for the semantic ramp and an inverted neutral ramp. That fixes every
place already using tokens, including everything I converted in Phase 10.

Then, on top of that:

- **112 raw classes converted** to tokens. Zero remain.
- **The rule now covers the colours that matter** and deliberately does *not*
  list green and teal, with a comment explaining why. It also catches the same
  string built in a template literal, which the old selector missed.
- **`--chrome-*` is pinned to literal values** instead of `var(--green-900)`.
  The sidebar is meant to be dark green in both themes; pointing it at the
  brand ramp meant the day anyone gave that ramp dark-mode values, the sidebar
  would invert with it.

**`npm run lint` now exits 0**, which it has not done in this project before —
it runs with `--max-warnings 0` and there were 10 errors and 2 warnings. The
remaining `any` types in `data-table`, `toast` and `ShiftsPage` are typed, and
the dead `src/hooks/useTranslation.ts` (a diverging duplicate nothing imported)
is deleted.

### Still open on dark mode

The **brand ramp itself** — `teal-300…900`, `green-300…950` — still has one set
of values. `text-teal-600` is 31% lightness, which is right on a white card and
thin on a dark one, and it appears 26 times. I have not guessed at replacements
because that is a judgement to make looking at a real screen, and the browser
pane could not reach your dev server to let me do it. **Worth 20 minutes with
the dark-mode toggle on** once you are next in the app.

---

## AuditPage hooks bug

`useQuery` sat *below* an early `return` for the access check, so the component
ran a different number of hooks depending on who was signed in. That is React's
one hard rule, and it would have crashed with *"rendered more hooks than during
the previous render"* the moment a role changed while the page was mounted.
The check is a value now, and the guarded view is returned from the JSX after
every hook has run.

While there: the stat-card accent map referenced `danger-500`, `danger-50` and
`border-l-danger-500`, **none of which this project's Tailwind config defines**.
Those cards had no accent at all and nobody had noticed. The accents are named
by meaning now — `info`, `success`, `warning`, `destructive` — so a card cannot
end up green in light mode and invisible in dark.

---

## On backups, since you asked

**I would not defer them to "after Postgres".** But I would not write a
SQLite backup command now either — you are right that it would be thrown away.
The middle path:

1. **Choose a managed Postgres**, not Postgres-on-a-VM. DigitalOcean, Neon,
   Railway, RDS — all take automated daily snapshots with point-in-time
   recovery as a checkbox. That is the backup, it costs a few dollars, and it
   is running before the first real bill. Postgres you install yourself has no
   backups until somebody writes a cron job, and that somebody is you at 11pm.
2. **Back up the SQLite file before you migrate.** The migration is itself the
   riskiest moment this project will have — one file, one command, keep three
   copies in three places. Do this whatever else you decide.
3. **Write `manage.py backup_db` after the move**, engine-aware (`pg_dump`, or
   the SQLite online backup API), for a copy the *client* controls — because a
   provider snapshot protects against hardware failure, not against the
   provider account lapsing or a dispute over the bill.
4. **Restore once, on purpose, before go-live.** An untested backup is not a
   backup, it is a belief. Restore into a scratch database and log in.

Sequenced that way you have never had an unprotected day, and none of the work
is thrown away. The thing I would push back on is going live on the server with
"backups to be set up shortly" — that is exactly the window these things get
lost in, and you have already sold them.

Also, now that it is definitely cloud: **`ROADMAP_AUDIT.md` §1.4 (login
throttling) is done**, but §0.4 and HTTPS/domain setup remain, and `DEBUG` must
be `False` in the deployed environment — `.env.example` still defaults it to
`True`, which is the single easiest way to expose a Django stack traceback with
your settings in it.

---

## What to test

**Quotations**

1. Quotations → **New quotation**. Search stock, add two items.
2. **Item not in stock** → type *"Cat-6 cable, 90m — supplied and laid"* and a
   price. It totals with everything else.
3. Set a discount, a tax %, and an installation charge → **Create**.
4. **Print** → the header says QUOTATION, shows *Valid until*, the off-catalogue
   line says *Supplied / arranged to order*, and the footer says
   *not a tax invoice*.
5. **Revise** → change a quantity → the number stays, it becomes **rev 2**.
6. **To till** → the checkout opens with the stock lines, the tax rate and the
   installation charge filled in, and a banner naming the quotation and how
   many lines could not come across.
7. Complete that sale → back on Quotations it shows **became a sale**.
8. Dashboard → the quotation itself never appeared in revenue; only the sale.

**The rest**

9. Products → New Product → the placeholders are cameras, not tiles.
10. Checkout → the totals column sits on the right with each label beside its
    number.
11. A bill with installation → check the A4: the labour line is a tinted band
    with the technician underneath.
12. A bill taxed at 21.5% → the A4 and the thermal slip must **both** say 21.5%.
13. **Dark mode toggle** → status panels are dark tinted, not white boxes.
    Look at Shifts (drawer over/short) and a credit-limit warning at checkout.

---

## Verification

- **327 backend tests**, 36 new for quotations.
- The quotation PDF rendered and inspected; two formatting bugs found by
  looking at it, not by assertions.
- `npm run lint` exits 0 with `--max-warnings 0`.
- `tsc --noEmit` clean.
- The dark-mode audit was done mechanically: every colour utility in use was
  cross-referenced against the CSS variables defined for each theme, which is
  how the missing semantic values were found.

---

## Still open

1. **Backups** — see above. Sequence it with the Postgres move.
2. **The brand ramp in dark mode** — 26 uses of `text-teal-600`/`700` that want
   a designer's eye on a real screen.
3. **i18n** — Urdu exists but only 3 of 13 pages call `t()`. Switching to Urdu
   leaves most of the app in English.
4. **Frontend tests** — Vitest is wired up with `passWithNoTests: true` and
   there is not one test file. `PaymentModal`'s tender arithmetic is the first
   thing I would cover.
5. **Serving the frontend from Django** so the shop runs one process, not two
   terminals. `ROADMAP_AUDIT.md` §1.1.

---

*Applied and verified against the working tree · 327 backend tests · lint and tsc clean · quotation rendered and inspected*
