# Credit limits & sharing bills on WhatsApp

Applied to the working tree. **165 backend tests pass; `tsc --noEmit` clean.**

---

## 1. Credit limits

The khata ledger made every balance explainable. It did not stop one growing forever — any customer could keep taking goods on account. That is now closed.

### How a limit is decided

```
customer.credit_limit_paise is not None  →  use it   (0 means "no credit at all")
otherwise                                →  shop-wide default_credit_limit_paise
default is 0 or unset                    →  unlimited
```

An explicit `0` on the customer is honoured rather than falling through to the shop default — that is how you refuse credit to one individual while the rest of the shop keeps its normal ceiling. There is a test for exactly that, because it is the case a naive `if not limit:` gets wrong.

### Where it is enforced

Inside `post_credit_entry`, **after the customer row is locked**:

```python
locked = Customer.objects.select_for_update().get(pk=customer.pk)
if enforce_limit and delta_paise > 0:
    check_credit_limit(locked, delta_paise)
```

My first attempt checked before the lock, in `create_sale`. That is wrong: two concurrent credit sales could both read the old balance, both pass a check neither would pass alone, and land the customer over the limit. Doing it under the lock is the only version that actually holds.

A refused sale raises `ValueError`, the atomic block unwinds, and nothing survives — no sale, no stock movement, no ledger entry. Tested.

### What the cashier sees

`PaymentModal` no longer just displays the post-sale balance — it **blocks**. Choosing Khata when the sale would break the limit disables Complete Sale and explains why:

> **This sale would break the credit limit**
> Only Rs 1,500.00 of credit is left. Take a part payment in cash, collect against the khata first, or ask an owner to raise the limit.

The server enforces it regardless; the UI just refuses to submit something it already knows will be rejected.

### Setting a limit

In the khata detail dialog (the eye icon), there is now a credit-limit row showing the limit in force, how much is left, and whether it came from the shop default. Owners and managers get an inline **Edit**; leaving the box blank clears the per-customer limit and falls back to the default.

Changing a limit is role-gated in the serializer, so a cashier gets a clear 400 rather than a silent success. A cashier can still edit a customer's name and notes.

### Two things fixed in passing

- `PaymentModal` offered **UPI** — an Indian payment rail this shop does not use — while `bank_transfer`, which is a real `Payment.Method` and appears in your Bills list, was unreachable from the till. Swapped.
- The modal's raw `blue-*` / `green-*` classes (no dark-mode variants) are now tokens.

---

## 2. Sharing a bill on WhatsApp

### The constraint worth knowing first

**WhatsApp cannot be handed a file from a browser.** A `wa.me` link carries *text only* — there is no parameter for an attachment, and WhatsApp Web does not accept one. That is a WhatsApp limitation, not something to code around.

So there are exactly three honest options:

| Approach | Works? | Verdict |
|---|---|---|
| Attach the PDF to a `wa.me` link | ✗ Impossible | Not available in any browser |
| Send a **text summary + a link** to the bill | ✓ Always | **This is what I built** |
| `navigator.share({files})` — native share sheet | ✓ Phones/tablets only | Wired as a bonus where supported |

### What actually happens

Pressing **Share on WhatsApp** opens a small dialog showing the link, the message, and how long the link lasts. Pressing **Open WhatsApp** launches `wa.me/<number>` with the message pre-filled — which lands in WhatsApp Web if you are signed in there, or the desktop app, exactly as you described.

The message looks like:

```
*Speed Tech Solutions*

Bill: SALE-20260905-00041
Date: 05 Sep 2026
Total: Rs 36,691.20

View your bill:
http://192.168.1.14:8000/r/eyJzIjo0MX0:1v...

Thanks for your Purchase!
```

For a khata sale it also states the outstanding balance — which quietly turns every credit receipt into a payment reminder.

On a tablet or phone that supports it, an **Attach the PDF** button appears and uses the native share sheet, which *can* hand WhatsApp the actual file. It is hidden on desktop, where the browser cannot do it.

### The link

`GET /r/<token>/` renders the bill as a mobile-friendly web page, with no login. The token is a **signed, expiring** payload — a bill id cannot be guessed or incremented into. Three controls in Settings:

| Setting | Default | What it does |
|---|---|---|
| `receipt_share_enabled` | `true` | Turn sharing off; **existing links stop working immediately** |
| `receipt_link_days` | `30` | How long a link lasts |
| `public_base_url` | *(blank)* | The address customers use |

**On `public_base_url` — this is the one decision you need to make:**

- **Leave it blank** and the link uses whatever address the till is opened on. If you run the till at `http://192.168.1.14:5174`, a customer standing in your shop on your wifi can open it. Someone at home cannot. Fine for a walk-in handing over a phone; not for sending bills home.
- **Set it to a public address** (`https://bills.speedtech.solutions`) once the system is cloud-hosted, and links work anywhere.
- **Middle ground:** a Cloudflare Tunnel or similar in front of the desktop install gives a public HTTPS address without moving anything. Worth it only if the client actually wants customers reading bills from home.

The share dialog tells staff which situation they are in rather than silently producing a dead link.

Anyone holding a valid link can see that one bill — nothing else is reachable from it, and it expires. That is the trade-off, which is why it is switchable off.

### Where the button is

- **Checkout**, after a sale completes — for every receipt format, since what is sent is a link rather than the selected file.
- **Bills**, in the expanded row, so an old bill can be re-sent.

---

## 3. The customer-facing page — a bug worth reporting

Wiring the share link meant `receipts/html.py` finally ran for the first time. It had never been used, and it was broken:

- **The TOTAL was invisible** — white text on a pale background. The one number the customer cares about.
- Placeholder grey boxes reading "LOGO" and "QR" instead of the real assets.
- Header in a generic bright green, not the brand colour.
- A "Customer Signature" line, on a page nobody can sign.
- Fixed desktop layout squashed onto a phone: `SALE-20260905-00041` broke across lines, columns collided.

It is rewritten: mobile-first with the item table reflowing to labelled stacked rows on narrow screens, brand colours from the shared theme, the real logo inlined as a data URI, a real scannable QR, correct contrast on the total, and a print stylesheet. I rendered it at phone and desktop widths and looked at both.

That also means `GET /api/sales/{id}/receipt/html/` now exists — any office printer can produce a bill without ReportLab.

---

## 4. Run it

```powershell
cd "D:\Neuroqaa Stuff\POS System\pos-system-GT\backend"
.\venv311\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "config.settings.desktop"
python manage.py migrate        # two new migrations
pytest -q                       # expect 165 passed
python manage.py runserver
```

```powershell
cd ..\frontend ; npm run dev
```

### Test checklist

**Credit limits**

1. Khata → eye icon → **Edit** the credit limit, set Rs 5,000.
2. Checkout that customer for more than their remaining credit → choose Khata → the button is disabled with an explanation.
3. Reduce the cart under the limit → it completes.
4. Sign in as a cashier → editing a limit is refused with a clear message.
5. Settings → set `default_credit_limit_paise` → applies to customers with no limit of their own.

**Sharing**

6. Complete a sale → **Share on WhatsApp** → the dialog shows the link and message.
7. **Open WhatsApp** → WhatsApp Web/app opens with the message filled in.
8. Copy the link and open it in a private window — the bill renders with no login.
9. Open the same link on your phone (same wifi) — it should be readable without zooming.
10. Settings → `receipt_share_enabled` = `false` → the same link now shows "no longer available".
11. Bills → expand a row → Share works there too.

---

## 5. Verification

- **165 backend tests** pass — 35 new here.
- **Mutation-tested the limit**: disabling the check made exactly 4 tests fail. Restored.
- `tsc --noEmit` clean.
- Public receipt page rendered at 430px and 900px and inspected.
- Phone normalisation covered by a parametrised test: `03331122333`, `0333 112 2333`, `+92 333 1122333`, `00923331122333`, `3331122333` all → `923331122333`; short and empty input → no number.

---

## 6. Still open

1. **§2.8 — partial payment at checkout.** `Payment` is a `OneToOneField`, so a sale has exactly one method. "Pay 2000 now, rest on khata" still cannot be expressed — and the credit-limit message now actively suggests it ("take a part payment"), so this is the natural next step.
2. **The ESLint palette rule.** `PaymentModal` and `KhataPage` are clean now, but the rule still is not in place, so this keeps recurring.
3. **Serials at stock-in.** Captured only at sale, so you know what left the building but not what is in it.
4. **`Claude outputs/`** — a folder of sample PDFs your desktop app saved from this session sits in the repo root. Safe to delete.

---

*Applied and verified against the working tree · 165 backend tests · tsc clean · customer page rendered and inspected*
