# Speed Tech Solutions POS — UI/UX Revamp Specification

**Audience:** the coding agent working in this repository (Copilot / Claude in VS Code / Cursor).
**Repo:** `pos-system-GT`
**Status:** authoritative design brief. Supersedes `DASHBOARD_REDESIGN_PROPOSAL.md`, `KIDS_POSHAK_THEME_GUIDE.md`, and `THEME_COLOR_REFERENCE.md`.
**Read with:** `docs/PROJECT_CONTEXT.md` (architecture rules — do not violate them).

---

## 0. Rules of engagement — read before writing any code

**Do this:**

1. Work **phase by phase**. Do not start Phase N+1 until Phase N compiles, `npm run type-check` passes, and I have reviewed it. Stop and report at the end of each phase.
2. Every colour, radius, shadow, and font size must come from a **token**. If you find yourself typing `text-teal-400`, `bg-slate-950`, or `#1e3a8a` in a component, you are doing it wrong — add or use a token instead.
3. Preserve all existing behaviour: query keys, API paths, keyboard shortcuts (F2/F3/F9/F12), route names, and translation keys. This is a **visual and structural** refactor, not a functional rewrite.
4. When you replace a page's markup, keep the exact same TanStack Query hooks and mutation handlers. Only the JSX and classes change.
5. Prefer **deleting** clever CSS over adding more. The current `index.css` has ten one-off utility classes that each style exactly one element. Those go away.

**Do not do this:**

- Do not touch `backend/apps/sales/services.py` (`create_sale`), money handling, or the paise convention. Money is always integer paise. See `PROJECT_CONTEXT.md` §6.1.
- Do not change `StockMovement` (append-only, §6.2).
- Do not change `?export=csv` to `?format=csv` (§6.5).
- Do not add a component library (MUI, Chakra, Ant, Mantine). We stay on **Tailwind + Radix + CVA**, which is already installed.
- Do not add web-font `@import` or `<link>` to Google Fonts. This product must run **fully offline** on a desktop/Tauri build. Fonts must be either system fonts or self-hosted `.woff2` files in `frontend/public/fonts/`.
- Do not add animation libraries. `tailwindcss-animate` is installed and is enough.

---

## 1. Audit — what is actually wrong today

This is not opinion. These are defects I found in the source. Fix each one; they are referenced by phase later.

### 1.1 The theme layer is decorative, not structural

`frontend/src/index.css` defines a proper HSL token set (`--primary`, `--muted`, `--border`, …) and then **the pages ignore it**. `DashboardPage.tsx` hardcodes a `colorMap` of raw Tailwind palette classes (`border-teal-600`, `from-orange-50`, `text-cyan-500`). The result: changing the brand means editing every page.

**Live bug in that same map:** `to-cyan-25`, `to-red-25`, `to-teal-25`, `to-gray-25` are used in the stat-card gradients. **Tailwind has no `25` shade.** Those four classes do not exist, are dropped at build time, and the gradients silently render as a flat one-colour wash. That is why the dashboard cards look washed out and inconsistent with each other.

### 1.2 The sidebar uses light-theme tokens on a dark surface

`ProtectedLayout.tsx` renders the sidebar as `bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950`, then styles the nav items with `text-muted-foreground`, `hover:bg-muted`, `hover:text-foreground`, and separates sections with a bare `border-t`.

Every one of those tokens resolves to a **light-mode** value: `--muted-foreground` is `hsl(220 15% 40%)` and `--border` is `hsl(220 13% 91%)`. So:

- Inactive nav labels are dark grey on near-black — roughly **2.4:1 contrast**, well below the 4.5:1 minimum.
- `hover:bg-muted` paints a near-white block on hover — a jarring flash.
- The section dividers and the logout border are a light-grey line on black, so they read as scratches.
- "Powered by Neuroqaa.ai" at `text-muted-foreground/40` is effectively invisible.

This single mismatch is the biggest reason the sidebar looks unpolished in your screenshots.

### 1.3 There is no brand, only an emoji

`ProtectedLayout.tsx` line ~110 renders `<span className="text-xl font-black text-teal-400">⚔️</span>` as the logo. There are **no brand assets in the repo at all** — no `frontend/public/` directory, the favicon is still `/vite.svg`, and `index.html` still says `<title>Neuroqaa POS</title>`. For a security-and-surveillance client, a crossed-swords emoji is the single most damaging detail on the screen.

### 1.4 There is no app shell

Every page invents its own header. `DashboardPage` has a greeting + live clock strip; `ProductsPage` and `CheckoutPage` have no top bar at all, so their content starts flush against the viewport top; `BillsPage`, `AuditPage`, `ShiftsPage` each have a different icon-plus-title treatment with different sizes and spacing. In your screenshots the sidebar even appears to change width and corner radius between pages. There is no shared `<AppShell>` / `<PageHeader>`, so nothing is consistent by construction.

### 1.5 Missing primitives, so every page re-implements them

`components/ui/` contains only `badge, button, dialog, input, label, select, textarea`. There is **no Card, no Table, no Skeleton, no EmptyState, no Toast, no Tooltip, no Pagination, no ConfirmDialog**. Consequences visible in the screenshots:

- Tables are hand-rolled `div` + `divide-y` on every page with different column padding and different header casing.
- No loading state — pages pop from blank to full.
- No empty state beyond a centred icon and two lines of text, styled differently on Returns vs Bills.
- `@radix-ui/react-toast` is **installed but never imported**. Saving settings, voiding a sale, and stocking in give no feedback.

### 1.6 Dark mode is defined and dead

`index.css` has a full `.dark {}` token block and `tailwind.config.js` sets `darkMode: ["class"]`. Nothing ever adds the `dark` class. Either wire it up or delete it — right now it is 25 lines of code implying a feature that does not exist.

### 1.7 Data presentation problems

- Date filters on Bills and Audit are raw `<input type="date">` rendering as **`mm/dd/yyyy`** — US order for a Pakistani shop. Should be `dd/mm/yyyy` presentation.
- The dashboard's `Rs. 147,911.40` uses `.stat-value-gradient` (gradient-clipped text). Gradient text on financial figures reduces legibility and prints/screenshots badly.
- Money columns are right-aligned in Bills but centre-drifting elsewhere, and not all use `tabular-nums`, so digits jitter between rows.
- The Audit page shows five KPI cards each with a different accent colour (blue, teal, amber, green, emerald). Five accents on one row means none of them signals anything.
- `Rs. 8,500.00` for a whole-rupee price wastes width. Show decimals only when non-zero, or only in totals.
- Table rows have no hover affordance and no click target, though rows are conceptually clickable everywhere.

### 1.8 Receipt / invoice defects

In `backend/apps/sales/receipt_templates.py`:

- **Off-brand colour.** `ClassicTemplate` paints its rules and headings `#1e3a8a` — indigo. That is the blue/purple bar in your invoice screenshot. It matches neither the green logo nor the teal letterhead.
- **Wrong date, real bug.** Line ~197: `datetime.now().strftime(...)` is used for the invoice DATE. Reprinting a bill from last week stamps **today's** date on it. It must be `self.sale.created_at`.
- **Wrong invoice number, likely crash.** `f"INV-{self.sale.id:06d}"` — but `Sale.id` is a **UUID** (`PROJECT_CONTEXT.md` §9). Integer formatting on a UUID raises. Use `self.sale.sale_number`.
- **Divider hack.** `Table([["="*50]])` is used to draw a horizontal rule. Use `HRFlowable` (already imported and unused).
- **Totals block is wrong.** It recomputes `subtotal` from line items and shows only Subtotal / Tax / Total. It never shows **Discount**, even though `sale.discount_paise` exists and your screenshot shows a `- Rs. 2,580.00` bill discount. It also ignores `sale.subtotal_paise` and `sale.total_paise`, so the printed total can disagree with the stored total.
- **Stale tenant copy.** The subtitle is hardcoded `"Sanitary & Tiles • Professional POS System"` and the template previews in `ReceiptTemplateSelector.tsx` still say `NEUROQAA SANITARY & TILES`. Wrong client.
- **No logo, no letterhead.** The invoice is text-only on white.
- **Four templates, one job.** Classic / Modern / Itemized / Compact are 690 lines of near-duplicate ReportLab. Collapse to **two** (thermal + document) with a shared builder.
- **No `Rs` glyph safety.** Helvetica has no `₨`. Keep the ASCII `Rs.` prefix — do not "improve" it to a symbol.

### 1.9 Assorted

- `index.html` title, favicon, and `<meta name="theme-color">` are all default Vite.
- No focus-visible ring styling anywhere — keyboard users see the browser default or nothing.
- `LanguageToggle` is defined **twice**: once in `components/LanguageToggle.tsx` and again inline inside `ProtectedLayout.tsx`. Delete one.
- `lib/useTranslation.ts` and `hooks/useTranslation.ts` both exist. Consolidate.
- The floating beach-ball emoji at the bottom-right of every screenshot is not in this codebase — confirm it is a browser extension and not something shipped.

---

## 2. Design direction

**One sentence:** a calm, dense, high-contrast operator console — dark forest-green chrome from the logo, teal from the letterhead for everything interactive, and a quiet neutral canvas so the numbers are the loudest thing on screen.

**Principles, in priority order:**

1. **Legibility over decoration.** This is a till. A cashier reads it eight hours a day under fluorescent light. Contrast and alignment beat gradients and glow.
2. **One accent.** Teal means "interactive or affirmative". Amber means "attention". Red means "destructive or negative". Nothing else gets colour. Kill the five-colour KPI row.
3. **Density with rhythm.** Tight vertical spacing, generous horizontal padding, everything on a 4px grid.
4. **Chrome recedes, data advances.** The sidebar and headers are dark and matte. The content area is near-white and clean.
5. **Motion is feedback, never ornament.** 120–200ms, opacity and 2–4px transforms only. Remove every infinite loop animation (`animate-float`, `animate-glow-pulse`) from operational screens — a POS that pulses all day is exhausting. Keep them only on the login page.

---

## 3. PHASE 1 — Brand assets and the token layer

Nothing else starts until this is done and reviewed.

### 3.1 Brand assets

Create `frontend/public/brand/` and place:

| File | Source | Use |
|---|---|---|
| `logo-mark.svg` | Trace the ST shield from the logo, single flat colour, currentColor-driven | Sidebar, login, favicon |
| `logo-full.svg` | Shield + "SPEED TECH SOLUTIONS" wordmark, horizontal lockup | Login page, invoice header |
| `logo-mark-mono-light.svg` | White mark for dark backgrounds | Sidebar |
| `logo-invoice.png` | 600px wide, transparent, for ReportLab | A4 PDF invoice |
| `favicon.svg` + `favicon-32.png` | Shield mark | Browser tab |

> Ask me for the vector files. Do **not** trace the raster JPG into a lumpy SVG, and do **not** substitute a Lucide icon as a placeholder. If the vectors are not available yet, use the flat shield silhouette in a single token colour — never the emoji.

Then update `frontend/index.html`:

```html
<link rel="icon" type="image/svg+xml" href="/brand/favicon.svg" />
<meta name="theme-color" content="#1A3A28" />
<title>Speed Tech Solutions — POS</title>
```

### 3.2 The palette

Two brand families, one neutral ramp, four semantic colours. **These are the only colours in the product.**

**Green — chrome (from the logo).** Sidebar, top bar, invoice header band, primary buttons.

| Token | Hex | HSL |
|---|---|---|
| `green-950` | `#0C1A12` | `146 38% 8%` |
| `green-900` | `#12281C` | `146 38% 12%` |
| `green-800` | `#1A3A28` | `146 38% 16%` |
| `green-700` | `#234B34` | `146 37% 21%` |
| `green-600` | `#2E5F42` | `145 35% 28%` |
| `green-500` | `#3C7854` | `145 33% 35%` |
| `green-400` | `#5F9A75` | `144 24% 49%` |
| `green-300` | `#8FBBA0` | `143 24% 65%` |

**Teal — accent (from the letterhead).** Links, focus rings, active nav, selected rows, primary data emphasis, success.

| Token | Hex | HSL |
|---|---|---|
| `teal-900` | `#0B3B40` | `186 71% 15%` |
| `teal-800` | `#0E5257` | `184 71% 20%` |
| `teal-700` | `#0F6E70` | `181 76% 25%` |
| `teal-600` | `#12898A` | `180 77% 31%` |
| `teal-500` | `#17A8A3` | `178 76% 37%` |
| `teal-400` | `#3DC2BC` | `177 52% 50%` |
| `teal-300` | `#7FD8D4` | `177 52% 67%` |
| `teal-100` | `#D6F2F0` | `176 53% 89%` |
| `teal-50`  | `#EEFAF9` | `176 50% 96%` |

**Neutral — canvas.** Slightly cool, so it sits under both brand families without going muddy.

| Token | Hex | HSL |
|---|---|---|
| `n-0`   | `#FFFFFF` | `0 0% 100%` |
| `n-50`  | `#F7FAFA` | `180 20% 98%` |
| `n-100` | `#EFF3F4` | `190 14% 95%` |
| `n-200` | `#DFE6E8` | `193 15% 89%` |
| `n-300` | `#C3CDD1` | `197 13% 79%` |
| `n-400` | `#92A1A7` | `198 11% 61%` |
| `n-500` | `#64757D` | `200 10% 44%` |
| `n-600` | `#47585F` | `197 15% 33%` |
| `n-700` | `#2C3A41` | `200 19% 22%` |
| `n-800` | `#1D272C` | `198 21% 14%` |
| `n-900` | `#131B1F` | `200 22% 10%` |

**Semantic.**

| Role | Hex | HSL | Use |
|---|---|---|---|
| `success` | `#1F9D57` | `147 67% 37%` | Completed, in stock, positive variance |
| `warning` | `#B45309` | `26 90% 37%` | Low stock, pending, unreconciled |
| `danger`  | `#B42318` | `4 77% 40%` | Void, out of stock, negative variance |
| `info`    | `#12898A` | `180 77% 31%` | Neutral notices (= teal-600) |

Each semantic colour also gets a `-bg` (tint for badges) and `-border`:
`success-bg #E7F6EE` · `warning-bg #FDF3E7` · `danger-bg #FDECEA` · `info-bg #E4F4F4`

### 3.3 Rewrite `frontend/src/index.css`

Replace the entire `:root` block. **Keep the `hsl(var(--x))` convention** — Tailwind config depends on it. Add a raw-brand layer above the semantic layer:

```css
@layer base {
  :root {
    /* ── Brand ramps (raw) ─────────────────────────── */
    --green-950: 146 38%  8%;
    --green-900: 146 38% 12%;
    --green-800: 146 38% 16%;
    --green-700: 146 37% 21%;
    --green-600: 145 35% 28%;
    --green-500: 145 33% 35%;
    --green-400: 144 24% 49%;
    --green-300: 143 24% 65%;

    --teal-900:  186 71% 15%;
    --teal-800:  184 71% 20%;
    --teal-700:  181 76% 25%;
    --teal-600:  180 77% 31%;
    --teal-500:  178 76% 37%;
    --teal-400:  177 52% 50%;
    --teal-300:  177 52% 67%;
    --teal-100:  176 53% 89%;
    --teal-50:   176 50% 96%;

    --n-0:   0   0% 100%;
    --n-50:  180 20% 98%;
    --n-100: 190 14% 95%;
    --n-200: 193 15% 89%;
    --n-300: 197 13% 79%;
    --n-400: 198 11% 61%;
    --n-500: 200 10% 44%;
    --n-600: 197 15% 33%;
    --n-700: 200 19% 22%;
    --n-800: 198 21% 14%;
    --n-900: 200 22% 10%;

    /* ── Semantic (what components actually use) ────── */
    --background:            var(--n-50);
    --foreground:            var(--n-800);
    --card:                  var(--n-0);
    --card-foreground:       var(--n-800);
    --popover:               var(--n-0);
    --popover-foreground:    var(--n-800);

    --primary:               var(--green-600);
    --primary-foreground:    var(--n-0);
    --accent:                var(--teal-600);
    --accent-foreground:     var(--n-0);
    --accent-soft:           var(--teal-50);

    --secondary:             var(--n-100);
    --secondary-foreground:  var(--n-700);
    --muted:                 var(--n-100);
    --muted-foreground:      var(--n-500);

    --border:                var(--n-200);
    --border-strong:         var(--n-300);
    --input:                 var(--n-200);
    --ring:                  var(--teal-500);

    --success:     147 67% 37%;  --success-bg: 152 47% 94%;
    --warning:      26 90% 37%;  --warning-bg:  33 82% 95%;
    --destructive:   4 77% 40%;  --destructive-bg: 6 79% 96%;
    --destructive-foreground: var(--n-0);
    --info:        180 77% 31%;  --info-bg:    180 44% 93%;

    /* ── Dark chrome surfaces (sidebar / topbar) ───── */
    --chrome:               var(--green-900);
    --chrome-elevated:      var(--green-800);
    --chrome-foreground:      0 0% 100%;
    --chrome-muted-foreground: 143 18% 72%;   /* 4.9:1 on --chrome ✅ */
    --chrome-border:        146 30% 22%;
    --chrome-hover:         146 34% 19%;
    --chrome-active:        var(--teal-600);

    /* ── Shape & depth ─────────────────────────────── */
    --radius:    0.5rem;
    --radius-sm: 0.375rem;
    --radius-lg: 0.75rem;

    --shadow-xs: 0 1px 2px 0 hsl(200 20% 12% / 0.05);
    --shadow-sm: 0 1px 3px 0 hsl(200 20% 12% / 0.07), 0 1px 2px -1px hsl(200 20% 12% / 0.06);
    --shadow-md: 0 4px 10px -2px hsl(200 20% 12% / 0.08), 0 2px 4px -2px hsl(200 20% 12% / 0.05);
    --shadow-lg: 0 12px 28px -6px hsl(200 20% 12% / 0.12);
  }
}
```

**Delete these utilities entirely** from `index.css`: `.stat-card-gradient`, `.stat-value-gradient`, `.quick-action-navy`, `.quick-action-orange`, `.quick-action-teal`, `.quick-action-gray`, `.progress-bar-container`, `.progress-bar-fill`, `.stat-trend-up`, `.stat-trend-down`, `.low-stock-critical`, `.low-stock-warning`, `.sidebar-brand-header`. Every one of them becomes a component prop.

**Keep:** the scrollbar block (restyle to `--n-300`), the RTL Urdu font stack, `.bg-dot-grid`, `.glass`, and `.btn-shimmer` — the last three are login-page only.

**Add** a global focus ring in `@layer base`:

```css
:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}
```

### 3.4 Extend `tailwind.config.js`

Add to `theme.extend.colors` (keep the existing semantic entries, **delete the whole `speedtech` block**):

```js
green: { 950:"hsl(var(--green-950))", 900:"hsl(var(--green-900))", 800:"hsl(var(--green-800))",
         700:"hsl(var(--green-700))", 600:"hsl(var(--green-600))", 500:"hsl(var(--green-500))",
         400:"hsl(var(--green-400))", 300:"hsl(var(--green-300))" },
teal:  { 900:"hsl(var(--teal-900))", 800:"hsl(var(--teal-800))", 700:"hsl(var(--teal-700))",
         600:"hsl(var(--teal-600))", 500:"hsl(var(--teal-500))", 400:"hsl(var(--teal-400))",
         300:"hsl(var(--teal-300))", 100:"hsl(var(--teal-100))", 50:"hsl(var(--teal-50))" },
chrome: {
  DEFAULT:  "hsl(var(--chrome))",
  elevated: "hsl(var(--chrome-elevated))",
  foreground:"hsl(var(--chrome-foreground))",
  muted:    "hsl(var(--chrome-muted-foreground))",
  border:   "hsl(var(--chrome-border))",
  hover:    "hsl(var(--chrome-hover))",
},
success:     { DEFAULT:"hsl(var(--success))",     bg:"hsl(var(--success-bg))" },
warning:     { DEFAULT:"hsl(var(--warning))",     bg:"hsl(var(--warning-bg))" },
destructive: { DEFAULT:"hsl(var(--destructive))", bg:"hsl(var(--destructive-bg))",
               foreground:"hsl(var(--destructive-foreground))" },
info:        { DEFAULT:"hsl(var(--info))",        bg:"hsl(var(--info-bg))" },
```

Also add:

```js
boxShadow: { xs:"var(--shadow-xs)", sm:"var(--shadow-sm)", md:"var(--shadow-md)", lg:"var(--shadow-lg)" },
fontFamily: {
  sans: ['"Inter var"','Inter','"Segoe UI"','system-ui','-apple-system','sans-serif'],
  mono: ['"JetBrains Mono"','"Cascadia Mono"','Consolas','ui-monospace','monospace'],
},
fontSize: {
  "2xs": ["0.6875rem", { lineHeight: "1rem",     letterSpacing: "0.02em" }],
  xs:    ["0.75rem",   { lineHeight: "1.125rem" }],
  sm:    ["0.8125rem", { lineHeight: "1.25rem" }],
  base:  ["0.875rem",  { lineHeight: "1.375rem" }],
  lg:    ["1rem",      { lineHeight: "1.5rem" }],
  xl:    ["1.125rem",  { lineHeight: "1.625rem", letterSpacing: "-0.01em" }],
  "2xl": ["1.375rem",  { lineHeight: "1.875rem", letterSpacing: "-0.015em" }],
  "3xl": ["1.75rem",   { lineHeight: "2.125rem", letterSpacing: "-0.02em" }],
  "4xl": ["2.25rem",   { lineHeight: "2.5rem",   letterSpacing: "-0.025em" }],
},
```

**Typography rules.** Base body is **14px** (`text-base` above), not 16 — this is a dense operator tool. Page titles `text-2xl font-semibold`. Section titles `text-sm font-semibold uppercase tracking-wide text-muted-foreground`. Table headers `text-2xs font-semibold uppercase tracking-wider text-muted-foreground`. **Every numeric value gets `tabular-nums`** — no exceptions.

**Fonts, offline-safe.** Self-host Inter var and JetBrains Mono as `.woff2` in `frontend/public/fonts/`, declared with `@font-face` and `font-display: swap` in `index.css`. If we cannot ship the files, the system stack above already degrades cleanly — but never add a network `@import`.

**Motion.** Delete `float`, `float-slow`, `float-reverse`, `glow-pulse` from any file under `pages/` **except** `LoginPage.tsx`. Keep `fade-up`, `fade-in-scale`. Add:

```js
keyframes: {
  "slide-in-right": { from:{opacity:"0",transform:"translateX(8px)"}, to:{opacity:"1",transform:"translateX(0)"} },
  "shimmer": { "100%": { transform: "translateX(100%)" } },
},
animation: {
  "slide-in-right": "slide-in-right 180ms cubic-bezier(0.16,1,0.3,1) both",
  "shimmer": "shimmer 1.6s infinite",
}
```

Wrap all decorative motion in `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; } }`.

### 3.5 Phase 1 acceptance

- [ ] `npm run build` succeeds, `npm run type-check` clean.
- [ ] Grep the codebase: zero occurrences of `slate-`, `cyan-`, `indigo-`, `-25`, or a raw `#` hex outside `index.css` and `brand/`.
- [ ] The old `speedtech.*` colour namespace is gone from `tailwind.config.js` and no file references it.
- [ ] Favicon and title show Speed Tech branding.
- [ ] Changing `--primary` in `index.css` visibly re-themes buttons across every page. **This is the test that the token layer actually works.** If it doesn't, Phase 1 is not done.

---

## 4. PHASE 2 — The app shell

### 4.1 Structure

Create `frontend/src/layouts/components/`:

```
AppSidebar.tsx      Fixed dark-green rail, brand lockup, grouped nav, user footer
AppTopbar.tsx       Sticky 56px bar: breadcrumb/title slot, search, shift pill, user menu
PageHeader.tsx      Title + subtitle + actions slot, used by every page
PageContainer.tsx   max-w-[1600px] mx-auto px-6 py-5 space-y-5
```

`ProtectedLayout.tsx` becomes thin:

```tsx
<div className="flex h-screen bg-background text-foreground">
  <AppSidebar />
  <div className="flex flex-1 flex-col min-w-0">
    <AppTopbar />
    <main className="flex-1 overflow-y-auto"><Outlet /></main>
  </div>
</div>
```

Every page then renders `<PageContainer><PageHeader …/> …</PageContainer>`. **No page defines its own title bar again.**

### 4.2 Sidebar spec

- Width `w-60` expanded, `w-16` collapsed. Persist the collapsed flag in the existing Zustand store; collapse automatically below `lg`.
- Surface `bg-chrome`, right edge `border-r border-chrome-border`. **No gradient** — flat matte reads more premium than a three-stop gradient.
- **Brand block:** `logo-mark-mono-light.svg` at 28px + "SPEED TECH" (`text-sm font-semibold tracking-wide text-chrome-foreground`) over "SOLUTIONS" (`text-2xs font-medium tracking-[0.18em] text-teal-400`). Bottom border `border-chrome-border`. **Remove the ⚔️ emoji and the "Enterprise Security Solutions" italic line** — the tagline belongs on the login page, not on every screen.
- **Nav items:** `h-9 px-3 rounded-md gap-2.5 text-sm`.
  - Rest: `text-chrome-muted` (this token is contrast-checked at 4.9:1 — **use it, not `text-muted-foreground`**).
  - Hover: `bg-chrome-hover text-chrome-foreground`.
  - Active: `bg-teal-600/15 text-white font-medium`, plus a 3px teal left bar via `before:absolute before:left-0 before:h-5 before:w-[3px] before:rounded-r-full before:bg-teal-400`.
  - Icons `h-4 w-4`, `text-chrome-muted`, teal-400 when active.
- **Section labels:** `text-2xs font-semibold uppercase tracking-[0.14em] text-chrome-muted/70`, `px-3 pt-4 pb-1.5`. No `border-t` dividers — spacing does the separating.
- **Badges:** the low-stock count uses `bg-warning/20 text-warning-bg border border-warning/40` so it reads on dark. Never the light-mode Badge.
- **Footer:** user avatar (initials in a `bg-teal-600/20 text-teal-300` circle), name, role chip, and a sign-out icon button. "Powered by Neuroqaa.ai" moves here at `text-2xs text-chrome-muted/60` — legible, not ghostly.
- Language toggle moves to the **topbar**, not the sidebar. Delete the duplicate inline `LanguageToggle` in `ProtectedLayout.tsx` and import `components/LanguageToggle.tsx`.

### 4.3 Topbar spec

`h-14 sticky top-0 z-30 bg-card/85 backdrop-blur border-b border-border`, contents `px-6`:

- **Left:** sidebar collapse toggle, then breadcrumb (`Operations / Products`) in `text-sm text-muted-foreground` with the last crumb `text-foreground font-medium`.
- **Centre:** global search input, `max-w-md`, placeholder "Search products, bills, customers… `⌘K`". Opens a command palette (Phase 6 — for now it can focus the page's own search).
- **Right, in order:** shift status pill · language toggle · date/time · user menu.
  - **Shift pill** — this is the single most useful thing to add. `● Shift #5 · 4h 12m · Rs 47,300` when open (teal dot, `bg-teal-50 text-teal-800 border-teal-100`); `● No open shift` when closed (`bg-warning-bg text-warning`) and clicking it goes to `/shifts`. A cashier should never have to navigate to know this.
  - Move the greeting + live clock out of `DashboardPage` and into here so it appears everywhere.
- **Urdu/RTL:** the shell must mirror when `dir="rtl"`. Use logical properties (`ps-`/`pe-`/`ms-`/`me-`, `start-`/`end-`) throughout, never `pl-`/`pr-`.

### 4.4 PageHeader spec

```tsx
<PageHeader
  title="Products"
  subtitle="18 products · 7 low stock"
  badge={<Badge variant="warning">7 low stock</Badge>}
  actions={<><Button variant="outline"><Upload/>Import CSV</Button>
             <Button><Plus/>New Product</Button></>}
  tabs={[{id:"catalogue",label:"Catalogue"},{id:"inventory",label:"Inventory Value"}]}
/>
```

Title `text-2xl font-semibold tracking-tight`, subtitle `text-sm text-muted-foreground mt-0.5`, actions right-aligned and vertically centred with the title, tabs on the row below with a 2px teal underline on the active tab. **No page-level icon next to the title** — the current icon-plus-title treatment (Bills, Returns, Audit, Shifts) is inconsistent and adds nothing.

### 4.5 Phase 2 acceptance

- [ ] All 11 pages render inside the same shell; sidebar width and topbar height are pixel-identical on every route.
- [ ] Every sidebar nav label passes 4.5:1 against `--chrome`. Verify with DevTools, not by eye.
- [ ] No page contains its own `<h1>`-plus-icon header block.
- [ ] `dir="rtl"` mirrors the entire shell with no clipped or overlapping elements.
- [ ] Sidebar collapse persists across reloads.

---

## 5. PHASE 3 — Component primitives

Build these in `components/ui/` with CVA, matching the existing `button.tsx` style. Each is small; the payoff is that Phase 4 becomes mechanical.

| Component | API sketch | Notes |
|---|---|---|
| `card.tsx` | `Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter` | `bg-card border border-border rounded-lg shadow-xs`. **One** elevation level in content areas. |
| `stat-tile.tsx` | `{label, value, icon, delta?, deltaDirection?, hint?, tone?, href?}` | Replaces the dashboard `colorMap`. Default tone neutral; `tone` only for genuinely alarming values. Value `text-3xl font-semibold tabular-nums text-foreground` — **flat colour, no gradient text**. |
| `data-table.tsx` | `columns`, `rows`, `onRowClick`, `isLoading`, `emptyState`, `stickyHeader` | Real `<table>`. Header `bg-n-50 text-2xs uppercase tracking-wider`, `h-11` rows, `hover:bg-teal-50/50`, zebra off, `border-b border-border`. `align:"right"` columns get `text-right tabular-nums`. Renders skeleton rows when loading. |
| `empty-state.tsx` | `{icon, title, description, action?}` | One implementation for all eight current variants. |
| `skeleton.tsx` | `<Skeleton className="h-4 w-32" />` | `bg-muted` + `animate-shimmer` overlay. |
| `toast.tsx` + `use-toast.ts` | Radix Toast, already a dependency | Top-right, `success`/`error`/`info` variants, 4s. **Wire into every mutation:** sale complete, void, stock-in, settings save, shift open/close, return. |
| `confirm-dialog.tsx` | `useConfirm()` promise-based | For void sale, delete, close shift. Destructive confirms require typing the bill number. |
| `tooltip.tsx` | Radix | Truncated product names, icon-only buttons. |
| `pagination.tsx` | `{page, pageCount, onChange}` | Bills currently shows a bare "Page 1 of 3". |
| `money.tsx` | `<Money paise={147911_40} />` | Renders `Rs 147,911.40`, `tabular-nums`, optional `compact` for tiles (`Rs 147.9k`) and `sign` for deltas. **All money on screen goes through this.** |
| `date-display.tsx` | `<DateTime value={iso} format="short"|"long"|"relative" />` | Locks `en-PK`, `dd MMM yyyy`, forces `dd/mm` order. |
| `form-field.tsx` | label + control + hint + error | Consistent 13px label, error in `text-destructive text-xs`. |

**Update existing:**

- `button.tsx` — variants `primary` (green-600), `accent` (teal-600), `outline`, `ghost`, `subtle` (n-100), `destructive`; sizes `sm/md/lg/icon`; add `loading` prop with an inline spinner and `disabled` while loading. **Delete `btn-shimmer` from operational buttons.**
- `badge.tsx` — variants `neutral, success, warning, danger, info, outline`; each uses its `-bg` token with the solid colour as text. Add a `dot` prop for a leading status dot.
- `input.tsx` — `h-9`, `border-border`, `focus:ring-2 focus:ring-ring/40 focus:border-ring`, optional `leadingIcon`/`trailingIcon`, `invalid` state.
- `select.tsx` — match Input height and focus exactly. Currently they visibly disagree on the Products page.

### 5.1 Phase 3 acceptance

- [ ] Storybook not required, but add a temporary `/dev/kitchen-sink` route rendering every primitive in every variant and state. Screenshot it for review, then delete the route.
- [ ] `Money` and `DateTime` are used everywhere; grep for `toLocaleString` and `paiseToRupees(` in `pages/` returns nothing.

---

## 6. PHASE 4 — Page by page

Convert pages in this order. Each is a self-contained commit.

### 6.1 LoginPage

Keep the split layout. Left panel becomes `bg-chrome` with `bg-dot-grid` and a large low-opacity shield watermark; centred `logo-full.svg`, the tagline "A name of Trust, Reliability and Quality!" (pull from settings `receipt_header`), and the Quetta address + phone at the bottom in `text-chrome-muted`. This is the **only** page allowed float/glow animation. Right panel: form on `bg-card`, `max-w-sm`, `h-10` inputs, full-width primary button with loading state, error as an inline `bg-destructive-bg` alert (not a toast). Add a Caps-Lock hint and a show/hide password toggle.

### 6.2 DashboardPage

- Greeting and clock **move to the topbar** (Phase 2). Delete from here.
- Four `StatTile`s, all neutral by default. Only Low Stock takes `tone="warning"` and only when count > 0. Values flat, `tabular-nums`, `Money` with `compact`.
- **Kill the fake deltas.** `↑ 8% vs yesterday` on *Total Products* is meaningless and `↑ 3% vs yesterday` on a count of 1 transaction is absurd. Either compute the real day-over-day delta from `/api/reports/` or show nothing. Showing a fabricated trend on a financial dashboard destroys trust in every other number.
- Quick Actions: four cards, but drop the four saturated gradients (teal/orange/teal/navy). Use `bg-card border` with a teal icon chip; only "New Sale" gets `variant="primary"` fill as the obvious primary path. Add `⌘`/F-key hints.
- Recent Sales: use `DataTable`, rows clickable to the bill detail, status as a `Badge`, amount right-aligned. Cap at 6 rows plus "View all".
- Shift Status card: when closed, show the warning tint and a prominent "Open Shift"; when open, show elapsed time, expected cash, transaction count, and "Close Shift".
- Add a **Today's revenue sparkline** (hourly buckets) under the revenue tile — one small line, `stroke-teal-500`, no axes, no library. It turns a static number into a trend at a glance.
- Add a **Low Stock** panel listing the 5 most-depleted SKUs with a "+Stock" button inline. Right now the count is a dead end.

### 6.3 ProductsPage

- `PageHeader` with `tabs` for Catalogue / Inventory Value.
- Filter bar in a `Card`: search (leading icon, 300ms debounce — currently it queries on **every keystroke**, fix that), category select, stock filter as a segmented control (`All / In stock / Low / Out`), refresh icon button.
- `DataTable` columns: Image (36px rounded, `ProductImage`), Name + SKU stacked (name `font-medium`, SKU `text-2xs font-mono text-muted-foreground` — SKU does not need its own column), Category badge, Stock (right, `tabular-nums`, with a small bar showing level vs threshold), Price (right, `Money`), Status badge, Actions (icon buttons, revealed on row hover).
- Status: `Out` = danger, `Low` = warning, `OK` = success. Currently `0` and `1` both show the same amber "Low Stock" — zero stock must be visually distinct from low stock.
- Row click opens a product detail drawer (right slide-over) with stock history; keeps people out of full-page navigations.
- Bulk selection with checkboxes → bulk stock-in / export / deactivate.

### 6.4 CheckoutPage — the most important screen

This is where the cashier lives. Treat it as the flagship.

- Keep the fullscreen `CheckoutLayout` and every keybinding.
- **Left (cart) is the hero.** Empty state: large teal-tinted icon, "Scan a barcode or start typing", and the shortcut legend — right now that legend is buried in the right rail where it is least visible when the cart is empty.
- Cart rows: `h-14`, product name `font-medium` + SKU beneath, qty stepper (−/input/+, min 44px targets), unit price, discount % inline, line total right-aligned bold. Newly added line animates `slide-in-right` and briefly flashes `bg-teal-50`. Selected row gets a teal left border.
- **Totals panel:** promote to a `bg-n-100 border-t-2 border-teal-600` block. Rows: Subtotal · Item discounts · Bill discount · Tax · **TOTAL** at `text-3xl font-bold tabular-nums`. The current `Rs. 0.00` at `text-3xl` next to a washed-out gradient Pay button reads as disabled.
- **Fix the Pay button.** It currently uses a teal→purple gradient that appears in no other part of the product and looks disabled at zero total. Make it solid `bg-primary`, full-width, `h-12`, showing `Pay Now · Rs 147,911.40 (F12)`. Genuinely disable it when the cart is empty.
- Right rail: customer lookup (phone → name chip with purchase history count), barcode field autofocused with a scanning-active indicator, product search with keyboard-navigable results showing thumbnail, name, price, and **live stock** (grey out zero-stock results).
- **Add a held-carts strip.** Park a sale, serve the next customer, resume. Every real shop needs this and it is a small amount of state.
- Payment modal: large denomination quick-buttons (500 / 1000 / 5000 / exact), change shown at `text-4xl` in teal, split-payment support, Enter to confirm.
- Post-sale: a success overlay with the bill number, the change due at large size, and three actions — Print · PDF · New Sale (Enter) — auto-dismissing to a fresh cart after 5s.

### 6.5 BillsPage

`DataTable` with sticky header. Date filters use a proper `DateRangePicker` with presets (Today, Yesterday, This week, This month, Custom) instead of two raw `mm/dd/yyyy` inputs. Status filter as a segmented control. Row click opens a **bill detail slide-over** (items, payment, cashier, timeline) with Print / PDF / Void / Return actions — not a separate page. Voided rows get a `line-through text-muted-foreground` treatment plus a danger badge. Add a summary strip above the table: count · gross · discounts · net for the current filter.

### 6.6 ReturnsPage

Make the three steps a visible stepper: **Find bill → Select items → Confirm refund**. Step 1 gets a large centred search with recent-bills shortcuts. Show the found bill as a mini-receipt card. Add per-item quantity selectors capped at the already-returned amount, a running refund total, and a required reason field.

### 6.7 CustomersPage

Add sortable columns, a segment filter (all / repeat / lapsed), and a customer detail slide-over with purchase history, lifetime value, and last-seen. Total Spent right-aligned `tabular-nums`. Gender badge is noise on a wholesale customer list — drop it or move it into the detail panel.

### 6.8 AuditPage

- **Reduce to two accent colours.** Revenue and Gross Profit are the headline pair (teal); Transactions, COGS, and Margin are neutral supporting tiles. The current five-colour row communicates nothing.
- Add a **revenue vs COGS bar chart** by day and a **payment-method donut**. Build with inline SVG — do not add Recharts for two charts.
- Move Download to a `DropdownMenu` (CSV / PDF / Excel) instead of a split button.
- Add a period-comparison row ("vs previous 4 months") with real deltas.

### 6.9 ShiftsPage

Open-shift form goes in a `Card` with a proper currency input (Rs prefix, thousand separators as you type). When a shift is open, replace the form with a live shift panel: elapsed time, transaction count, cash sales, expected drawer, and a "Close Shift" button. Close flow becomes a modal showing expected vs counted with the variance computed live and colour-coded (green ≤ Rs 100, amber ≤ Rs 500, red beyond). Shift history as `DataTable` with a variance column.

### 6.10 ActivityPage

Filter chips become a proper segmented/multi-select control that shows counts. Event type gets a coloured icon, not just a badge. The `details` blob renders as key/value chips (it already does — keep that, it is one of the better bits of the current UI). Add user and date-range filters, plus infinite scroll or pagination.

### 6.11 SettingsPage

Two-column layout: sticky section nav on the left (Shop · Receipt · Tax · Printer · Users · System), forms on the right. Group into `Card`s with descriptions. Add a **live receipt preview panel** that re-renders as receipt settings change — this is the highest-value addition on this page. Add a logo upload for the invoice. Replace per-field save with a sticky "Unsaved changes — Save / Discard" bar. Disabled controls for non-owner roles must show a tooltip explaining why.

---

## 7. PHASE 5 — Receipts and invoices

### 7.1 Consolidate

Collapse the four templates in `receipt_templates.py` (690 lines) into **two**, sharing one data-preparation function:

```python
# backend/apps/sales/receipts/
#   __init__.py
#   context.py     build_receipt_context(sale, shop_settings) -> ReceiptContext
#   thermal.py     render_thermal_pdf(ctx, width_mm=80)   + render_escpos(ctx)
#   document.py    render_document_pdf(ctx, pagesize="a4"|"a5")
#   html.py        render_html_receipt(ctx) -> str
#   theme.py       BRAND colours, fonts, logo path
```

`build_receipt_context` returns a plain dataclass — bill number, ISO and formatted datetime, cashier, customer, list of line dicts, and **the stored** `subtotal_paise`, `item_discount_paise`, `bill_discount_paise`, `tax_paise`, `total_paise`, `tendered_paise`, `change_paise`. Every renderer consumes only this. That guarantees the thermal slip, the PDF, and the HTML view can never disagree.

Keep the `receipt_template` setting so the selector UI still works, but map values to `thermal` / `document`. Migrate existing values in a data migration.

### 7.2 Bugs to fix while you are in there

1. `datetime.now()` → `self.sale.created_at`, formatted in `Asia/Karachi`. **Reprints must show the original sale time.**
2. `INV-{self.sale.id:06d}` → `self.sale.sale_number`. `Sale.id` is a UUID.
3. Show **Discount** in the totals block, sourced from `sale.discount_paise`.
4. Use stored `sale.subtotal_paise` / `sale.total_paise` rather than recomputing.
5. Replace `Table([["="*50]])` with `HRFlowable`.
6. Delete the hardcoded `"Sanitary & Tiles • Professional POS System"` subtitle — pull from the `receipt_header` setting.
7. Update the ASCII previews in `ReceiptTemplateSelector.tsx`: they still say `NEUROQAA SANITARY & TILES`. Replace the emoji headers with real rendered thumbnails.
8. Keep `Rs.` as ASCII. Do not switch to `₨` — the PDF base-14 fonts do not have that glyph and it will print as a black box.

### 7.3 Brand theme for print

In `theme.py`:

```python
BRAND_GREEN      = colors.HexColor("#1A3A28")   # header band, total bar
BRAND_GREEN_DEEP = colors.HexColor("#12281C")
BRAND_TEAL       = colors.HexColor("#12898A")   # accent rules, labels
BRAND_TEAL_SOFT  = colors.HexColor("#EEFAF9")   # zebra rows, bill-to panel
INK              = colors.HexColor("#1D272C")
INK_MUTED        = colors.HexColor("#64757D")
RULE             = colors.HexColor("#DFE6E8")
```

**Delete every `#1e3a8a`.** That indigo is the single most off-brand thing in the product.

### 7.4 A4 / A5 document invoice — layout

Think of the letterhead, translated to a business document.

```
┌────────────────────────────────────────────────────────────┐
│ ██ 6mm solid green bar, full bleed                         │
├────────────────────────────────────────────────────────────┤
│  [LOGO 34mm]              SPEED TECH SOLUTIONS   (green,   │
│                           Agha Siraj Complex,     11pt bold)│
│                           Circular Road, Quetta   (muted 8) │
│                           +92 321 8131109                   │
│                                                             │
│  ───────────────────────── teal 0.8pt rule ──────────────── │
│                                                             │
│  BILL TO                              INVOICE               │
│  Walk-in Customer                     No.   SALE-...-00029  │
│  03001234567                          Date  02 Sep 2026     │
│                                       Time  15:02           │
│                                       Cashier  admin        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ #  DESCRIPTION            QTY   RATE  DISC    AMOUNT │  │ ← green header row,
│  ├──────────────────────────────────────────────────────┤  │   white 7.5pt caps
│  │ 1  2MP Fixed Dome Camera   10  8,500     —    85,000 │  │
│  │    DMC-2MP-001                                       │  │ ← SKU under name, muted
│  │ 2  4CH NVR (500GB)          2 22,000     —    44,000 │  │ ← teal-soft zebra
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  NOTES                          Subtotal      129,000.00    │
│  Thanks for your purchase!      Bill discount  −2,580.00    │
│                                 Tax (17%)      21,491.40    │
│                                ┌───────────────────────────┐│
│                                │ TOTAL      Rs 147,911.40 ││ ← solid green,
│                                └───────────────────────────┘│   white 13pt bold
│                                 Paid (Cash)   150,000.00    │
│                                 Change          2,088.60    │
│                                                             │
│  Amount in words: One hundred forty-seven thousand nine     │
│  hundred eleven rupees and forty paise only                 │
│                                                             │
│  ______________________          ______________________     │
│  Customer Signature              For Speed Tech Solutions   │
├────────────────────────────────────────────────────────────┤
│ A name of Trust, Reliability and Quality!   ██▓▒░ teal      │ ← footer band
│ speedtech.solutions · +92 321 8131109        Page 1 of 1    │   echoing letterhead
└────────────────────────────────────────────────────────────┘
```

**Typographic and alignment rules — these are what make it look professional:**

- Column widths, A4 (190mm usable): `#` 8mm · Description 74mm · Qty 14mm · Rate 26mm · Disc 22mm · Amount 30mm. Fixed, so multi-page invoices stay aligned.
- **Right-align every money column and use a monospaced-digit font** (`Helvetica` is fine; set `fontName` consistently). Money must line up on the decimal point down the whole column. This is the number-one thing missing from the current invoice.
- Amounts print without the currency prefix inside the table (`85,000.00`), with `Rs` shown once in the totals block. Repeating `Rs.` on every row is visual noise.
- Grouping separators always; two decimals always in the document invoice.
- Row height 7mm minimum, 2.5mm cell padding, name wraps to two lines max with ellipsis.
- Header row: green background, white 7.5pt bold caps, `letterSpacing 0.5`.
- Zebra: `BRAND_TEAL_SOFT` on even rows only — no grid lines inside the table. A single 0.5pt `RULE` line under each row is enough; full grids look like a spreadsheet, not an invoice.
- Totals block occupies the **right 70mm** and is right-aligned as a two-column table; labels muted, values ink. The TOTAL row is a filled green rectangle with white text and 3mm padding.
- Add **amount in words** — expected on invoices in Pakistan. Write a small `num_to_words_pkr()` helper (handles lakh/crore or plain international grouping; pick international to stay simple) with unit tests.
- Add a **QR code** in the bottom-right encoding the bill number, total, and date, so a bill can be looked up by scanning. `qrcode[pil]` is a small dependency; if you would rather not add it, encode a Code128 of the bill number with ReportLab's built-in `reportlab.graphics.barcode` — no new dependency.
- Page footer with `Page X of Y` via an `onPage` canvas callback.
- If `sale.status == "voided"`, draw a large rotated `VOID` watermark at 12% opacity across the page.
- Add a top-right `ORIGINAL` / `DUPLICATE` marker driven by a query param, so reprints are distinguishable.
- Fold the tax number / NTN into the header if the client has one (add a `shop_ntn` setting).

### 7.5 80mm thermal slip

Different medium, different rules — do not just shrink the A4.

```
        SPEED TECH SOLUTIONS          ← 11pt bold, centred
      Agha Siraj Complex, Quetta      ← 7pt
          +92 321 8131109
   A name of Trust, Reliability
          and Quality!
════════════════════════════════
 SALE-20260902-00029
 02 Sep 2026  15:02   admin
 Customer: Walk-in
────────────────────────────────
 2MP Fixed Dome Camera
   10 x 8,500.00        85,000.00   ← qty line indented under name
 4CH NVR (500GB)
    2 x 22,000.00       44,000.00
────────────────────────────────
 Subtotal              129,000.00
 Bill discount          -2,580.00
 Tax 17%                21,491.40
════════════════════════════════
 TOTAL              Rs 147,911.40   ← double height + bold via ESC/POS
════════════════════════════════
 Cash                  150,000.00
 Change                  2,088.60
────────────────────────────────
   Thank you for your business!
      Goods once sold are
    returnable within 7 days
        with this receipt
         [QR: bill no]
    Powered by Neuroqaa.ai
```

- 32 characters at Font A on 80mm; 42 at Font B. **Pick one and pad every line to it.** The current text receipt does not pad consistently, which is why columns wander.
- Item name on its own line, `qty x rate` and amount on the next — a 30-character product name cannot share a line with two numbers on 80mm.
- Use ESC/POS double-height/double-width **only** for the TOTAL line.
- Print the logo as a monochrome raster at the top if `python-escpos` is available (`printer.image()`); skip silently if not — keep the existing `ImportError` guard, per `PROJECT_CONTEXT.md` §17.5.
- Feed 4 lines and cut at the end.
- Add a `[QR: bill no]` block via `printer.qr()` guarded by a capability check.
- Keep the 58mm variant as the same renderer with `width_mm=58` and a 32→24 char switch — not a separate template class.

### 7.6 HTML print view (optional but cheap)

`GET /api/sales/{id}/receipt/html/` returns a standalone HTML document rendering the same `ReceiptContext`, with `@media print` rules and `@page { size: A4; margin: 12mm }`. Two reasons this is worth the hour: any office printer works without ReportLab, and the frontend can show a true **live preview** in an iframe on the Settings page and before payment. Add a "Print (browser)" button next to the existing PDF button on the post-sale overlay and in the bill detail slide-over. Inline all CSS; embed the logo as a data URI so it works offline.

### 7.7 Phase 5 acceptance

- [ ] Print a bill with 1 item, one with 25 items (multi-page), and one voided bill. Columns align, totals match `sale.total_paise` to the paise, page numbers correct.
- [ ] Reprint a bill from a previous day — the printed date is the **sale** date.
- [ ] No `#1e3a8a` anywhere in `backend/`.
- [ ] Thermal slip at 80mm and 58mm: no line exceeds the character width, nothing wraps mid-number.
- [ ] `Rs` renders as `Rs`, never a black box.
- [ ] Amount-in-words has unit tests covering 0, 1, 99.99, 100000, 14791140 paise.

---

## 8. PHASE 6 — Polish

- **Command palette** (`⌘K` / `Ctrl+K`): jump to any page, search a product, open a bill, start a sale. Build on Radix Dialog — no `cmdk` dependency needed.
- **Keyboard shortcut overlay** on `?`, listing every binding. Currently they are documented only in a corner of the checkout screen.
- **Dark mode:** either wire the existing `.dark` tokens to a topbar toggle persisted in Zustand, **or delete the block**. A half-built feature is worse than none. Recommendation: wire it — a POS often runs in a dim shop at night, and the token layer already supports it after Phase 1.
- **Offline/API-down banner:** a slim amber strip when the backend is unreachable, since desktop mode makes this a real state.
- **Optimistic UI + toasts** on every mutation.
- **Accessibility sweep:** focus-visible everywhere (Phase 1 gives you this free), `aria-label` on all icon-only buttons, `role="status"` live region announcing cart totals and sale completion, full keyboard operation of checkout without a mouse, 44px minimum touch targets (this will run on tablets).
- **Performance:** `React.lazy` + `Suspense` per route, debounce all searches at 300ms, virtualise the product list beyond 200 rows, memoise cart line components.
- **Empty, loading, and error states for every list.** Right now most pages have none.
- **Print stylesheet** so `Ctrl+P` on Audit/Bills produces something sane.

---

## 9. Copy-paste prompts for each phase

Give these to the agent one at a time. Do not paste more than one.

> **Phase 1 —** Read `docs/UI_UX_REVAMP_SPEC.md` sections 0, 2, and 3. Implement Phase 1 only: brand asset directory and `index.html` updates, the full rewrite of `frontend/src/index.css` token layer exactly as specified, the `tailwind.config.js` extension, deletion of the listed one-off utilities and the `speedtech` colour namespace, and the global focus-visible ring. Do not touch any file in `src/pages/`. When done, run `npm run type-check` and `npm run build`, then list every file you changed and every place that still references a deleted class so I can review before Phase 2.

> **Phase 2 —** Read `docs/UI_UX_REVAMP_SPEC.md` section 4. Implement the app shell: create `layouts/components/{AppSidebar,AppTopbar,PageHeader,PageContainer}.tsx`, reduce `ProtectedLayout.tsx` to the composition shown, and update all 11 pages to wrap their existing content in `PageContainer` + `PageHeader` while deleting their own header blocks. Do not change any query, mutation, or handler logic. Pay particular attention to §1.2 — the sidebar must use the `chrome-*` tokens, never the light-mode `muted`/`border` tokens. Report contrast ratios for the sidebar nav states.

> **Phase 3 —** Read `docs/UI_UX_REVAMP_SPEC.md` section 5. Build every listed primitive in `components/ui/` using CVA in the style of the existing `button.tsx`, and upgrade `button`, `badge`, `input`, and `select` as described. Add a temporary `/dev/kitchen-sink` route rendering all of them in every variant and state. Do not convert any page yet.

> **Phase 4 —** Read `docs/UI_UX_REVAMP_SPEC.md` section 6. Convert pages to the new primitives **one page per commit**, in the listed order, starting with LoginPage. After each page, run type-check and stop for my review. Preserve every keyboard shortcut, query key, and translation key exactly.

> **Phase 5 —** Read `docs/UI_UX_REVAMP_SPEC.md` section 7. Refactor `backend/apps/sales/receipt_templates.py` into the `receipts/` package described, fixing every bug in §7.2, applying the brand theme in §7.3, and implementing the A4/A5 document invoice (§7.4), the 80mm/58mm thermal renderer (§7.5), and the HTML print view (§7.6). Add pytest coverage for `build_receipt_context` and `num_to_words_pkr`. Generate sample PDFs for a 1-item, a 25-item, and a voided sale and save them to `backend/tmp/receipt_samples/` for review.

> **Phase 6 —** Read `docs/UI_UX_REVAMP_SPEC.md` section 8 and implement the polish items in the order listed, one commit each.

---

## 10. Definition of done

The revamp is finished when all of these are true:

1. Changing one hex value in `index.css` re-themes the entire application.
2. No component in `src/pages/` contains a raw colour class or hex value.
3. Every sidebar and chrome text element passes WCAG AA (4.5:1).
4. All 11 pages share one shell, one page header, one table, one card, one empty state.
5. Every mutation produces a toast; every list has loading, empty, and error states.
6. The printed A4 invoice, the 80mm slip, and the on-screen bill detail all report identical figures, sourced from the same `ReceiptContext`.
7. A reprint of an old bill shows the original sale date.
8. Checkout is fully operable by keyboard, start to finish, without a mouse.
9. `npm run build`, `npm run type-check`, `npm run test`, and `pytest` all pass.
10. The application looks like it was built for a security-systems company in Quetta — not like a template with the colours swapped.

---

*Prepared for Speed Tech Solutions POS · Neuroqaa.ai · September 2026*
