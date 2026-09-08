"""
Give quotations a letterhead to start from.

Built from the shop's own details so the first quotation prints correctly
without anyone visiting Settings first. Extra identities — a separate entity
for corporate tenders, say — are added from the Quotations page.
"""

from django.db import migrations


def seed(apps, schema_editor):
    BusinessProfile = apps.get_model("sales", "BusinessProfile")
    if BusinessProfile.objects.exists():
        return

    Setting = apps.get_model("config", "Setting")
    values = dict(Setting.objects.values_list("key", "value"))

    BusinessProfile.objects.create(
        name=values.get("shop_name") or "Speed Tech Solutions",
        address=values.get("shop_address", ""),
        phone=values.get("shop_phone", ""),
        email=values.get("shop_email", ""),
        is_default=True,
    )


def unseed(apps, schema_editor):
    apps.get_model("sales", "BusinessProfile").objects.filter(is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0013_businessprofile_quotation_quotationitem"),
        ("config", "0009_roles_tax_and_warranty_settings"),
    ]

    operations = [migrations.RunPython(seed, reverse_code=unseed)]
