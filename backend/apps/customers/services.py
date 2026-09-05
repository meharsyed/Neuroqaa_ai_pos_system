"""
Khata (customer credit) posting service.

Every change to a customer's balance goes through `post_credit_entry`. That
guarantees three things the previous code could not:

  * an append-only audit trail — you can always answer "why is this balance
    what it is", and repair it if it drifts;
  * the row is locked while it is read-modify-written, so two concurrent
    credit sales can no longer lose one charge;
  * `sum(ledger.delta_paise) == customer.outstanding_paise`, an invariant a
    management command can verify.
"""

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce

from .models import CreditLedgerEntry, Customer


@transaction.atomic
def post_credit_entry(
    *,
    customer: Customer,
    kind: str,
    delta_paise: int,
    sale=None,
    payment=None,
    note: str = "",
    created_by=None,
    enforce_limit: bool = False,
) -> CreditLedgerEntry:
    """
    Append one ledger entry and move the customer's balance by `delta_paise`.

    delta_paise is positive when the customer owes more (a credit sale) and
    negative when they owe less (a payment, a void, a return).
    """
    if delta_paise == 0:
        raise ValueError("A ledger entry must move the balance.")

    # Lock the row for the read-modify-write. No-op on SQLite, real on Postgres.
    locked = Customer.objects.select_for_update().get(pk=customer.pk)

    # Checked here, against the locked row, so two concurrent credit sales
    # cannot both slip under the limit.
    if enforce_limit and delta_paise > 0:
        check_credit_limit(locked, delta_paise)

    new_balance = locked.outstanding_paise + delta_paise

    entry = CreditLedgerEntry.objects.create(
        customer=locked,
        kind=kind,
        delta_paise=delta_paise,
        balance_after_paise=new_balance,
        sale=sale,
        payment=payment,
        note=note,
        created_by=created_by,
    )

    locked.outstanding_paise = new_balance
    locked.save(update_fields=["outstanding_paise", "updated_at"])

    # Keep the caller's in-memory instance in step with the database.
    customer.outstanding_paise = new_balance
    return entry


def ledger_balance(customer: Customer) -> int:
    """Balance derived from the ledger itself, for verification."""
    return CreditLedgerEntry.objects.filter(customer=customer).aggregate(
        total=Coalesce(Sum("delta_paise"), 0)
    )["total"]


def customer_credit_summary(customer: Customer) -> dict:
    """Everything the khata detail panel needs, in one pass over the ledger."""
    entries = CreditLedgerEntry.objects.filter(customer=customer)

    charged = entries.filter(delta_paise__gt=0).aggregate(
        t=Coalesce(Sum("delta_paise"), 0)
    )["t"]
    credited = entries.filter(delta_paise__lt=0).aggregate(
        t=Coalesce(Sum("delta_paise"), 0)
    )["t"]

    paid = -(
        entries.filter(kind=CreditLedgerEntry.Kind.PAYMENT).aggregate(
            t=Coalesce(Sum("delta_paise"), 0)
        )["t"]
    )
    reversed_ = -(
        entries.filter(
            kind__in=[CreditLedgerEntry.Kind.VOID, CreditLedgerEntry.Kind.RETURN]
        ).aggregate(t=Coalesce(Sum("delta_paise"), 0))["t"]
    )

    first_unpaid = (
        entries.filter(kind=CreditLedgerEntry.Kind.SALE).order_by("created_at").first()
    )
    last_payment = (
        entries.filter(kind=CreditLedgerEntry.Kind.PAYMENT)
        .order_by("-created_at")
        .first()
    )

    return {
        "outstanding_paise": customer.outstanding_paise,
        "ledger_balance_paise": charged + credited,
        "total_charged_paise": charged,
        "total_paid_paise": paid,
        "total_reversed_paise": reversed_,
        "credit_sale_count": entries.filter(kind=CreditLedgerEntry.Kind.SALE).count(),
        "payment_count": entries.filter(kind=CreditLedgerEntry.Kind.PAYMENT).count(),
        "first_credit_at": first_unpaid.created_at if first_unpaid else None,
        "last_payment_at": last_payment.created_at if last_payment else None,
        "last_payment_paise": -last_payment.delta_paise if last_payment else 0,
        "is_reconciled": (charged + credited) == customer.outstanding_paise,
    }


# ── Credit limits ───────────────────────────────────────────────────────────


def effective_credit_limit(customer: Customer) -> int | None:
    """
    The limit that actually applies to this customer.

    A per-customer value always wins, including an explicit 0 ("no credit").
    Otherwise the shop-wide default applies. None means unlimited.
    """
    if customer.credit_limit_paise is not None:
        return customer.credit_limit_paise

    from apps.config.utils import get_setting

    try:
        default = int(get_setting("default_credit_limit_paise", "0") or 0)
    except (TypeError, ValueError):
        return None
    # 0 as the shop-wide default means "no limit configured", not "no credit" —
    # a shop that wants to refuse credit outright sets it per customer.
    return default if default > 0 else None


def available_credit(customer: Customer) -> int | None:
    """How much more this customer may take on. None means unlimited."""
    limit = effective_credit_limit(customer)
    if limit is None:
        return None
    return max(0, limit - customer.outstanding_paise)


def check_credit_limit(customer: Customer, amount_paise: int) -> None:
    """Raise ValueError if `amount_paise` would push the customer over."""
    limit = effective_credit_limit(customer)
    if limit is None:
        return
    projected = customer.outstanding_paise + amount_paise
    if projected > limit:
        name = customer.name or customer.phone or f"Customer #{customer.pk}"
        raise ValueError(
            f"Credit limit exceeded for {name}. "
            f"Limit Rs {limit / 100:,.2f}, already owed Rs {customer.outstanding_paise / 100:,.2f}, "
            f"this sale Rs {amount_paise / 100:,.2f}. "
            f"Take a part payment or raise the limit."
        )
