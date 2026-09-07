"""
Settings for the staff-permission ceiling, editable tax, and the warranty
clause the client asked to print on every bill.
"""

from django.db import migrations

WARRANTY_EN = (
    "Warranty is void if the device is damaged by electrical spark, power surge, "
    "lightning, water, fire, physical impact, or repair by anyone other than "
    "Speed Tech Solutions."
)

# Naskh Urdu. Rendered on the A4/A5 invoice and the shared web bill; the 80mm
# thermal printer has no Urdu characters in its ROM, so it stays English there.
WARRANTY_UR = (
    "بجلی کی چنگاری، وولٹیج کے اتار چڑھاؤ، آسمانی بجلی، پانی، آگ، جسمانی نقصان، "
    "یا اسپیڈ ٹیک سلوشنز کے علاوہ کسی اور سے مرمت کروانے کی صورت میں وارنٹی ختم "
    "تصور ہوگی۔"
)

DEFAULTS = [
    (
        "cashier_return_limit_paise",
        "500000",
        "Cashier Return Limit (paise)",
        "The most a cashier may hand back on one return. Anything larger needs an "
        "owner or manager. A return puts stock back and takes money off a bill, so "
        "it cannot be looser than voiding. 0 stops cashiers returning anything.",
    ),
    (
        "warranty_note_enabled",
        "true",
        "Print the Warranty Clause",
        "Prints the warranty conditions on the A4/A5 invoice, and on the till slip "
        "when the bill carries serial numbers.",
    ),
    (
        "warranty_note_language",
        "en",
        "Warranty Clause Language",
        "en, ur, or both. Applies to the A4/A5 invoice and the shared web bill. "
        "The 80mm thermal printer cannot print Urdu, so the till slip is always English.",
    ),
    ("warranty_note_en", WARRANTY_EN, "Warranty Clause (English)", "Shown on printed bills."),
    ("warranty_note_ur", WARRANTY_UR, "Warranty Clause (Urdu)", "Shown on printed bills."),
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

    dependencies = [("config", "0008_credit_and_share_settings")]

    operations = [migrations.RunPython(seed, reverse_code=unseed)]
