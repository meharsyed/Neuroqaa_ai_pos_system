from django.db import migrations


def add_receipt_page_format_setting(apps, schema_editor):
    Setting = apps.get_model("config", "Setting")
    Setting.objects.get_or_create(
        key="receipt_page_format",
        defaults={
            "value": "a4",
            "label": "Receipt Page Format",
            "description": "Page size for receipt PDF: thermal_80mm (80mm thermal printer), thermal_58mm (58mm thermal printer), a4 (210×297mm), or a5 (148×210mm)",
        },
    )


def remove_receipt_page_format_setting(apps, schema_editor):
    Setting = apps.get_model("config", "Setting")
    Setting.objects.filter(key="receipt_page_format").delete()


class Migration(migrations.Migration):

    dependencies = [("config", "0004_receipt_template_setting")]

    operations = [migrations.RunPython(add_receipt_page_format_setting, reverse_code=remove_receipt_page_format_setting)]