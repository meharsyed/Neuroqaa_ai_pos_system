"""
Give every existing balance a ledger entry.

Before this, credit sales only incremented Customer.outstanding_paise, so there
is no history to reconstruct. Rather than invent one, each customer carrying a
balance gets a single opening entry equal to that balance. From here on, every
movement is recorded, and sum(ledger) == outstanding_paise holds.
"""

from django.db import migrations


def open_balances(apps, schema_editor):
    Customer = apps.get_model("customers", "Customer")
    CreditLedgerEntry = apps.get_model("customers", "CreditLedgerEntry")

    made = 0
    for c in Customer.objects.exclude(outstanding_paise=0):
        if CreditLedgerEntry.objects.filter(customer_id=c.pk).exists():
            continue
        CreditLedgerEntry.objects.create(
            customer_id=c.pk,
            kind="opening",
            delta_paise=c.outstanding_paise,
            balance_after_paise=c.outstanding_paise,
            note="Opening balance carried over from before the credit ledger existed.",
            tenant_id=getattr(c, "tenant_id", 1),
        )
        made += 1
    if made:
        print(f"  opened {made} customer balance(s)")


def drop_openings(apps, schema_editor):
    CreditLedgerEntry = apps.get_model("customers", "CreditLedgerEntry")
    CreditLedgerEntry.objects.filter(kind="opening").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0003_creditledgerentry"),
    ]

    operations = [
        migrations.RunPython(open_balances, drop_openings),
    ]
