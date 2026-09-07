"""
Shareable receipt links.

WhatsApp cannot be handed a file from a browser — `wa.me` only accepts text.
So sharing a bill means sending the customer a **link** they can open on their
phone. The link has to work without a login, which means it must be:

  * signed, so a bill id cannot simply be guessed or incremented;
  * time-limited, so an old link stops working;
  * switchable off entirely, via the `receipt_share_enabled` setting.

Anyone holding a valid link can see that one bill. That is the intended
trade-off — it is the customer's own receipt — but it is a real one, so the
shop can turn it off.
"""

from django.core import signing

from apps.config.utils import get_setting

SALT = "receipt-share-v1"


def sharing_enabled() -> bool:
    return str(get_setting("receipt_share_enabled", "true")).strip().lower() in (
        "1", "true", "yes", "on",
    )


def link_max_age_seconds() -> int:
    try:
        days = int(get_setting("receipt_link_days", "30") or 30)
    except (TypeError, ValueError):
        days = 30
    return max(1, days) * 86400


def make_receipt_token(sale) -> str:
    return signing.dumps({"s": sale.pk}, salt=SALT)


def resolve_receipt_token(token: str):
    """Return the Sale for a valid, unexpired token, else None."""
    from .models import Sale

    try:
        data = signing.loads(token, salt=SALT, max_age=link_max_age_seconds())
    except signing.SignatureExpired:
        return None
    except signing.BadSignature:
        return None

    try:
        return (
            Sale.objects.select_related("cashier", "customer")
            .prefetch_related("items__product", "items__serials", "payments")
            .get(pk=data["s"])
        )
    except (Sale.DoesNotExist, KeyError, TypeError):
        return None


def public_base_url(request=None) -> str:
    """
    Where the customer can reach this system.

    A configured `public_base_url` always wins. Otherwise fall back to whatever
    host the till itself was opened on — which works for phones on the same
    network, and is the honest default for an on-premise install.
    """
    configured = (get_setting("public_base_url", "") or "").strip().rstrip("/")
    if configured:
        return configured
    if request is not None:
        return request.build_absolute_uri("/").rstrip("/")
    return ""


def normalise_pk_phone(phone: str | None) -> str | None:
    """
    03331122333 -> 923331122333.

    Numbers are stored locally but wa.me needs international form.
    """
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 10:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0"):
        return "92" + digits[1:]
    if digits.startswith("92"):
        return digits
    if len(digits) == 10:  # 3331122333
        return "92" + digits
    return digits


def build_share_payload(sale, request=None) -> dict:
    """Everything the UI needs to share one bill."""
    from apps.config.utils import get_all_settings

    shop = get_all_settings()
    shop_name = shop.get("shop_name", "Speed Tech Solutions")

    enabled = sharing_enabled()
    url = ""
    if enabled:
        base = public_base_url(request)
        url = f"{base}/r/{make_receipt_token(sale)}/" if base else ""

    # What the customer owes, which includes any installation charge.
    total = sale.amount_due_paise / 100
    is_return = getattr(sale, "sale_type", "sale") == "return"
    heading = "Credit note" if is_return else "Bill"

    lines = [
        f"*{shop_name}*",
        "",
        f"{heading}: {sale.sale_number}",
        f"Date: {sale.created_at:%d %b %Y}",
        f"Total: Rs {abs(total):,.2f}",
    ]
    if getattr(sale, "installation_paise", 0):
        lines.append(f"(includes installation Rs {sale.installation_paise / 100:,.2f})")

    # A part-paid bill says so, so the customer sees what is still owed on it
    # as well as what they owe overall.
    try:
        credit = sale.credit_paise
        if credit > 0:
            if sale.amount_paid_paise > 0:
                lines.append(f"Paid now: Rs {sale.amount_paid_paise / 100:,.2f}")
            lines.append(f"On khata: Rs {credit / 100:,.2f}")
            if sale.customer:
                lines.append(
                    f"Outstanding balance: Rs {sale.customer.outstanding_paise / 100:,.2f}"
                )
    except Exception:
        pass

    if url:
        lines += ["", "View your bill:", url]
    lines += ["", shop.get("receipt_footer", "Thank you for your business!")]

    message = "\n".join(lines)
    phone = normalise_pk_phone(getattr(sale.customer, "phone", None) if sale.customer else None)

    from urllib.parse import quote

    wa = f"https://wa.me/{phone}?text={quote(message)}" if phone else \
         f"https://wa.me/?text={quote(message)}"

    return {
        "enabled": enabled,
        "public_url": url,
        "message": message,
        "whatsapp_url": wa,
        "customer_phone": phone,
        "expires_days": link_max_age_seconds() // 86400,
    }
