"""
Verify — and optionally repair — the khata invariant:

    sum(CreditLedgerEntry.delta_paise) == Customer.outstanding_paise

Run it after any bulk data work, or whenever a balance looks wrong:

    python manage.py check_khata
    python manage.py check_khata --repair
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.db.models.functions import Coalesce

from apps.customers.models import CreditLedgerEntry, Customer


class Command(BaseCommand):
    help = "Check that every customer's balance matches their credit ledger."

    def add_arguments(self, parser):
        parser.add_argument(
            "--repair",
            action="store_true",
            help="Post a correcting adjustment entry for each drifted customer.",
        )

    def handle(self, *args, **options):
        repair = options["repair"]
        drifted = []

        customers = Customer.objects.annotate(
            ledger_total=Coalesce(Sum("ledger__delta_paise"), 0)
        )

        for c in customers:
            if c.ledger_total != c.outstanding_paise:
                drifted.append(c)

        if not drifted:
            self.stdout.write(self.style.SUCCESS(
                f"OK — {customers.count()} customer(s), every balance matches its ledger."
            ))
            return

        self.stdout.write(self.style.ERROR(f"{len(drifted)} customer(s) out of balance:"))
        for c in drifted:
            gap = c.outstanding_paise - c.ledger_total
            self.stdout.write(
                f"  #{c.pk} {c.display_name}: stored {c.outstanding_paise/100:,.2f}, "
                f"ledger {c.ledger_total/100:,.2f}, gap {gap/100:,.2f}"
            )

        if not repair:
            self.stdout.write(
                "\nRe-run with --repair to post a correcting entry for each. "
                "Nothing has been changed."
            )
            return

        # The ledger is the record of truth, so an adjustment is written to
        # explain the gap rather than silently overwriting the balance.
        from apps.customers.services import post_credit_entry

        for c in drifted:
            gap = c.outstanding_paise - c.ledger_total
            if gap == 0:
                continue
            c.outstanding_paise = c.ledger_total
            c.save(update_fields=["outstanding_paise"])
            post_credit_entry(
                customer=c,
                kind=CreditLedgerEntry.Kind.ADJUSTMENT,
                delta_paise=gap,
                note="Reconciliation: balance realigned to the ledger by check_khata --repair.",
            )
        self.stdout.write(self.style.SUCCESS(f"Repaired {len(drifted)} customer(s)."))
