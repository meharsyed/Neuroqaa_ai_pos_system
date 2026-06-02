from django.db import migrations

DEFAULTS = [
    ("low_stock_threshold", "10", "Low Stock Threshold", "Default minimum qty before a low-stock warning is shown"),
    ("receipt_footer", "Thank you for your business!", "Receipt Footer", "Printed at the bottom of every receipt"),
    ("receipt_header", "", "Receipt Header", "Extra text printed above the item list"),
    ("receipt_width", "48", "Receipt Width (chars)", "Characters per line: 48 for 80 mm, 32 for 58 mm"),
    ("shop_address", "Quetta, Balochistan, Pakistan", "Shop Address", "Printed on receipts"),
    ("shop_email", "", "Shop Email", "Printed on receipts"),
    ("shop_name", "Neuroqaa Sanitary & Tiles", "Shop Name", "Printed on receipts"),
    ("shop_phone", "", "Shop Phone", "Printed on receipts"),
    ("tax_pct", "0", "Tax %", "Applied to every sale. Set to 0 to disable tax."),
    ("thermal_printer_ip", "", "Thermal Printer IP", "IP address of the network-connected ESC/POS printer"),
    ("thermal_printer_port", "9100", "Thermal Printer Port", "Default ESC/POS TCP port"),
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

    dependencies = [("config", "0001_initial")]

    operations = [migrations.RunPython(seed, reverse_code=unseed)]