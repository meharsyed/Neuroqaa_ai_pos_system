from django.db import migrations


def add_show_serial_numbers_setting(apps, schema_editor):
    Setting = apps.get_model("config", "Setting")
    Setting.objects.get_or_create(
        key="show_serial_numbers_on_receipt",
        defaults={
            "value": "true",
            "label": "Show Serial Numbers on Receipt",
            "description": "Display serial numbers and warranty information on printed receipts and invoices (true/false)",
        },
    )


def remove_show_serial_numbers_setting(apps, schema_editor):
    Setting = apps.get_model("config", "Setting")
    Setting.objects.filter(key="show_serial_numbers_on_receipt").delete()


class Migration(migrations.Migration):

    dependencies = [("config", "0006_merge_20260825_2254")]

    operations = [migrations.RunPython(add_show_serial_numbers_setting, reverse_code=remove_show_serial_numbers_setting)]