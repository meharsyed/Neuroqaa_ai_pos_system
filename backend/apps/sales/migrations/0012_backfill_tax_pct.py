"""
Give every existing bill the tax rate it was actually charged at.

Receipts printed the rate from the live shop setting, so the percentage on a
reprinted invoice changed whenever the shop changed its rate. Each bill now
carries its own — derived here from the bill's own numbers, which is more
truthful than the setting could ever be.
"""

from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations


def forwards(apps, schema_editor):
    Sale = apps.get_model("sales", "Sale")

    fixed = 0
    for sale in Sale.objects.filter(tax_paise__gt=0, tax_pct__isnull=True).iterator(
        chunk_size=500
    ):
        taxable = (sale.subtotal_paise or 0) - (sale.discount_paise or 0)
        if taxable <= 0:
            continue
        rate = (Decimal(sale.tax_paise) * 100 / Decimal(taxable)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if not (Decimal("0") < rate <= Decimal("100")):
            # Nothing sane to derive — leave it null so no percentage is printed
            # rather than printing a wrong one.
            continue
        sale.tax_pct = rate
        sale.save(update_fields=["tax_pct"])
        fixed += 1

    if fixed:
        print(f"  stamped the tax rate on {fixed} existing bill(s)")


def backwards(apps, schema_editor):
    # The column is dropped by the schema migration; nothing to undo here.
    pass


class Migration(migrations.Migration):

    dependencies = [("sales", "0011_sale_tax_pct")]

    operations = [migrations.RunPython(forwards, backwards)]
