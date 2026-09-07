"""
Backfill the split-payment columns.

Until now a sale had exactly one Payment, and that one tender settled the whole
bill — so every existing payment's `amount_paise` is its sale's total, and a
sale counts as paid unless that tender was credit.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    Payment = apps.get_model("sales", "Payment")
    Sale = apps.get_model("sales", "Sale")

    touched = 0
    for pay in Payment.objects.select_related("sale").iterator():
        if pay.sale_id is None:
            # Orphans predate the sale link; the tendered amount is all we know.
            pay.amount_paise = pay.amount_tendered_paise
        else:
            pay.amount_paise = pay.sale.total_paise
        pay.save(update_fields=["amount_paise"])
        touched += 1

    paid = 0
    for sale in Sale.objects.prefetch_related("payments").iterator(chunk_size=500):
        settled = sum(
            p.amount_paise for p in sale.payments.all() if p.method != "credit"
        )
        if settled != sale.amount_paid_paise:
            sale.amount_paid_paise = settled
            sale.save(update_fields=["amount_paid_paise"])
            paid += 1

    if touched or paid:
        print(f"  backfilled {touched} payment(s), {paid} sale total(s)")


def backwards(apps, schema_editor):
    # The columns are dropped by the schema migration; nothing to undo here.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0008_alter_payment_options_payment_amount_paise_and_more"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
