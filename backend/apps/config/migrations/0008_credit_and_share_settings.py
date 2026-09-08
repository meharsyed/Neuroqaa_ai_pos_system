from django.db import migrations

DEFAULTS = [
    (
        "default_credit_limit_paise",
        "0",
        "Default Credit Limit (paise)",
        "Shop-wide khata ceiling applied to customers with no limit of their own. "
        "0 means no shop-wide limit; set a per-customer limit to restrict an individual.",
    ),
    (
        "receipt_share_enabled",
        "true",
        "Allow Sharing Receipts by Link",
        "When on, staff can send a customer a link to view their own bill. "
        "Links are signed and expire; anyone holding one can see that single bill.",
    ),
    (
        "receipt_link_days",
        "30",
        "Receipt Link Validity (days)",
        "How long a shared receipt link keeps working before it expires.",
    ),
    (
        "public_base_url",
        "",
        "Public Base URL",
        "Address customers use to reach this system, e.g. https://bills.speedtech.solutions. "
        "Leave blank to use whatever address the till is opened on — that only works for "
        "phones on the same network.",
    ),
]


def seed(apps, schema_editor):
    Setting = apps.get_model("config", "Setting")
    for key, value, label, description in DEFAULTS:
        Setting.objects.get_or_create(
            key=key,
            defaults={"value": value, "label": label, "description": description},
        )


def unseed(apps, schema_editor):
    Setting = apps.get_model("config", "Setting")
    Setting.objects.filter(key__in=[row[0] for row in DEFAULTS]).delete()


class Migration(migrations.Migration):

    dependencies = [("config", "0007_show_serial_numbers_setting")]

    operations = [migrations.RunPython(seed, reverse_code=unseed)]
