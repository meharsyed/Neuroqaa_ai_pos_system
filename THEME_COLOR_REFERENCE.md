# Kids Poshak Theme — Quick Color Reference

## Color Palette

### Primary Colors
```
┌─────────────────────────────────────────────────────┐
│ SOFT PURPLE (Primary)                               │
│ HSL: 270 70% 50%                                    │
│ HEX: #7c3aed                                        │
│ RGB: 124, 58, 237                                   │
│ Usage: Stat cards, buttons, headers, links          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ SOFT TEAL (Secondary)                               │
│ HSL: 190 75% 50%                                    │
│ HEX: #06b6d4                                        │
│ RGB: 6, 182, 212                                    │
│ Usage: Gradients, accents, complementary           │
└─────────────────────────────────────────────────────┘
```

### Accent Colors
```
┌─────────────────────────────────────────────────────┐
│ CORAL/ORANGE (Alert)                                │
│ HSL: 11 90% 60%                                     │
│ HEX: #ff6b35                                        │
│ RGB: 255, 107, 53                                   │
│ Usage: Low stock alert, warning, attention         │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ MINT GREEN (Success)                                │
│ HSL: 150 70% 60%                                    │
│ HEX: #10d981                                        │
│ RGB: 16, 217, 129                                   │
│ Usage: Completed sales, positive trends, success   │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ ACTION ORANGE (CTA)                                 │
│ HSL: 25 95% 55%                                     │
│ HEX: #f97316                                        │
│ RGB: 249, 115, 22                                   │
│ Usage: Call-to-action buttons, urgent actions      │
└─────────────────────────────────────────────────────┘
```

### Sidebar
```
┌─────────────────────────────────────────────────────┐
│ DARK SLATE (Sidebar Background)                     │
│ HSL: 220 30% 25%                                    │
│ HEX: #1e293b                                        │
│ RGB: 30, 41, 59                                     │
│ Usage: Sidebar background, dark areas              │
└─────────────────────────────────────────────────────┘
```

### Utility Colors
```
┌─────────────────────────────────────────────────────┐
│ EMERALD GREEN (Success/Complete)                    │
│ HSL: 160 84% 39%                                    │
│ HEX: #10b981                                        │
│ RGB: 16, 185, 129                                   │
│ Usage: Completed badges, checkmarks, success       │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ SLATE GRAY (Text/Neutral)                           │
│ HSL: 15 23% 26%                                     │
│ HEX: #1e293b                                        │
│ RGB: 30, 41, 59                                     │
│ Usage: Body text, muted foreground                 │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ WHITE (Background)                                  │
│ HEX: #ffffff                                        │
│ RGB: 255, 255, 255                                  │
│ Usage: Card backgrounds, main content area         │
└─────────────────────────────────────────────────────┘
```

---

## Component Color Mapping

### Stat Cards
```
┌────────────────────────────────────────────┐
│ CARD 1: Total Products                      │
├────────────────────────────────────────────┤
│ Accent:   SOFT PURPLE                       │
│ Border:   4px solid #7c3aed                │
│ Gradient: Purple → Teal                     │
│ Icon:     Purple                            │
│ Trend:    ↑ Green (if positive)            │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ CARD 2: Low Stock                           │
├────────────────────────────────────────────┤
│ Accent:   CORAL/ORANGE                      │
│ Border:   4px solid #ff6b35                │
│ Gradient: Coral → Red                       │
│ Icon:     Coral                             │
│ Trend:    None (or ↓ Red if alerts)        │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ CARD 3: Revenue Today                       │
├────────────────────────────────────────────┤
│ Accent:   MINT GREEN                        │
│ Border:   4px solid #10d981                │
│ Gradient: Mint → Cyan                       │
│ Icon:     Mint                              │
│ Trend:    ↑ Green (if positive)            │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ CARD 4: Transactions Today                  │
├────────────────────────────────────────────┤
│ Accent:   AMBER/YELLOW                      │
│ Border:   4px solid #f59e0b                │
│ Gradient: Amber → Orange                    │
│ Icon:     Amber                             │
│ Trend:    ↓ Coral (if negative)            │
└────────────────────────────────────────────┘
```

### Quick Action Buttons
```
┌──────────────────────────────────────────────────┐
│ 💳 CHECKOUT                                       │
│ Gradient: Purple → Deep Purple                    │
│ Background: #7c3aed → #6d28d9                   │
│ Text: White (#ffffff)                            │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ 📦 ADD STOCK                                      │
│ Gradient: Coral → Dark Coral                      │
│ Background: #ff6b35 → #dc2626                   │
│ Text: White (#ffffff)                            │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ 📊 REPORTS                                        │
│ Gradient: Mint → Dark Mint                        │
│ Background: #10d981 → #059669                   │
│ Text: White (#ffffff)                            │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ ⏱️ SHIFTS                                        │
│ Gradient: Orange → Dark Orange                    │
│ Background: #f97316 → #c2410c                   │
│ Text: White (#ffffff)                            │
└──────────────────────────────────────────────────┘
```

### Shift Widget
```
┌──────────────────────────────────────────────────┐
│ SHIFT WIDGET                                      │
├──────────────────────────────────────────────────┤
│ Background:    Light purple tint (#f5f3ff)      │
│ Header:        Purple gradient background        │
│ Status Dot:    Emerald green (when open)         │
│ Status Text:   Emerald (#10b981)                 │
│ Info Text:     Slate gray (#1e293b)              │
│ KPI Amount:    Purple (#7c3aed, bold)            │
│ KPI Progress:  Mint → Purple gradient            │
│ Button:        Purple → Teal gradient            │
│ Button Text:   White                             │
└──────────────────────────────────────────────────┘
```

### Recent Sales
```
┌──────────────────────────────────────────────────┐
│ RECENT SALES                                      │
├──────────────────────────────────────────────────┤
│ Header BG:     Purple gradient (#e9d5ff→dbeafe) │
│ Row Hover:     Light purple tint (#faf5ff)      │
│ Sale Number:   Purple bold (#7c3aed)             │
│ Status Icon:   Emerald (✓) or Orange (✗)        │
│ Status Badge:  Emerald or Destructive            │
│ Amount:        Purple bold (#7c3aed)             │
│ Discount:      Orange (#f97316)                  │
│ Text:          Slate gray                        │
└──────────────────────────────────────────────────┘
```

### Low Stock Alert
```
┌──────────────────────────────────────────────────┐
│ LOW STOCK ALERT                                   │
├──────────────────────────────────────────────────┤
│ Header BG:     Orange gradient                   │
│ Icon:          Orange pulsing                    │
│ Badge Count:   Orange                            │
│ Button:        Orange text/border                │
│                                                   │
│ CRITICAL ITEM:                                    │
│ ├─ Badge:      Orange "CRITICAL"                │
│ ├─ Border:     4px orange left border            │
│ ├─ Background: Light orange tint (#fed7aa)      │
│ ├─ Progress:   Orange/Red gradient (empty)       │
│ └─ Percent:    Orange bold                       │
│                                                   │
│ LOW ITEM:                                         │
│ ├─ Badge:      Emerald "LOW"                     │
│ ├─ Border:     4px emerald left border           │
│ ├─ Background: Light emerald tint (#ecfdf5)     │
│ ├─ Progress:   Mint/Emerald gradient (partial)   │
│ └─ Percent:    Emerald bold                      │
└──────────────────────────────────────────────────┘
```

---

## Dashboard Header

```
┌─────────────────────────────────────────────────────────────────┐
│                    DASHBOARD HEADER                              │
├─────────────────────────────────────────────────────────────────┤
│  LEFT                   CENTER                  RIGHT             │
│  ─────────────────────────────────────────────────────────────   │
│                                                                   │
│  Good Morning,          👕                     Aug 29, 2026      │
│  Mehar                                                            │
│  (Owner role)           Kids Poshak                              │
│                         Children's Fashion...                    │
│                         (Purple→Blue gradient text)              │
│                                                                   │
│  Background: Light purple/blue tint                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Sidebar

```
┌──────────────────────────────────┐
│  DARK SLATE SIDEBAR              │
├──────────────────────────────────┤
│  ◆ Neuroqaa.ai                   │
│    (Orange diamond accent)       │
│                                  │
│  Modern POS for Modern           │
│  Businesses                      │
│  (Gray italic text)              │
│                                  │
│  [EN] [اردو]  Language Toggle    │
│                                  │
├──────────────────────────────────┤
│  Dashboard (nav item)            │
│  Products (nav item)             │
│  Checkout (nav item, active)     │
│  Bills (nav item)                │
│  ... more nav items ...          │
│                                  │
├──────────────────────────────────┤
│  Sign Out                        │
│                                  │
│  Powered by Neuroqaa.ai          │
│  (Footer text)                   │
└──────────────────────────────────┘
```

---

## Dark Mode Adjustments

When dark mode is enabled:

```
┌─────────────────────────────────────────┐
│ Light Mode         →  Dark Mode         │
├─────────────────────────────────────────┤
│ Primary: 270 70% 50%  →  270 70% 60%   │
│ Teal:    190 75% 50%  →  190 75% 55%   │
│ Coral:   11 90% 60%   →  11 90% 65%    │
│ Mint:    150 70% 60%  →  150 70% 65%   │
│                                         │
│ (Colors become slightly brighter for   │
│  contrast against dark background)     │
└─────────────────────────────────────────┘
```

---

## Gradients Used

### Stat Card Values
```
Purple → Teal:     #7c3aed → #06b6d4
Purple → Blue:     #7c3aed → #0ea5e9
Coral → Red:       #ff6b35 → #dc2626
Mint → Cyan:       #10d981 → #06b6d4
Amber → Orange:    #f59e0b → #f97316
```

### Progress Bar
```
Mint → Purple:     #10d981 → #7c3aed
```

### Buttons
```
Purple → Purple:   #7c3aed → #6d28d9
Coral → Coral:     #ff6b35 → #dc2626
Mint → Mint:       #10d981 → #059669
Orange → Orange:   #f97316 → #c2410c
```

---

## CSS Variables Reference

See `frontend/src/index.css`:

```css
:root {
  --primary: 270 70% 50%;           /* Soft Purple */
  --primary-teal: 190 75% 50%;      /* Soft Teal */
  --accent-coral: 11 90% 60%;       /* Coral */
  --accent-mint: 150 70% 60%;       /* Mint */
  --accent-orange: 25 95% 55%;      /* Action Orange */
  --sidebar-dark: 220 30% 25%;      /* Dark Sidebar */
}

.dark {
  --primary: 270 70% 60%;           /* Lighter for contrast */
  --primary-teal: 190 75% 55%;
  --accent-coral: 11 90% 65%;
  --accent-mint: 150 70% 65%;
  /* ... etc */
}
```

---

## Quick Copy-Paste (Design Tools)

### Tailwind Classes
```
bg-purple-500       - Primary purple
bg-teal-500         - Secondary teal
bg-orange-400       - Coral accent
bg-emerald-500      - Mint/success
text-purple-600     - Primary text
bg-gradient-to-r from-purple-500 to-teal-500
```

### Hex Colors
```
Purple:   #7c3aed
Teal:     #06b6d4
Coral:    #ff6b35
Mint:     #10d981
Orange:   #f97316
Sidebar:  #1e293b
Emerald:  #10b981
```

---

## Validation

To verify colors are correct:

1. **Purple**: Should be vibrant but not too bright. Not pink, not blue.
2. **Teal**: Should be cool and fresh. Not green, not blue.
3. **Coral**: Should be warm and energetic. Not red, not orange.
4. **Mint**: Should be calming and gentle. Not green, not cyan.
5. **Dark Sidebar**: Should be professional. Not black, not blue.

All colors should work together harmoniously for a **professional yet playful** look.

---

**For the Kids Poshak brand, this palette creates a balance between:**
- ✅ Professional (dark sidebar, muted colors)
- ✅ Playful (purple, coral, mint accents)
- ✅ Modern (gradients, smooth transitions)
- ✅ Accessible (high contrast, readable)
