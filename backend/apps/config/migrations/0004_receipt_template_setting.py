from django.db import migrations


def add_receipt_template_setting(apps, schema_editor):
    Setting = apps.get_model("config", "Setting")
    Setting.objects.get_or_create(
        key="receipt_template_type",
        defaults={
            "value": "classic",
            "label": "Receipt Template Type",
            "description": "Choose receipt design: classic, modern, itemized, or compact. Options: classic (traditional), modern (clean contemporary), itemized (detailed with borders), compact (thermal printer optimized)",
        },
    )


def remove_receipt_template_setting(apps, schema_editor):
    Setting = apps.get_model("config", "Setting")
    Setting.objects.filter(key="receipt_template_type").delete()


class Migration(migrations.Migration):

    dependencies = [("config", "0003_language_setting")]

    operations = [migrations.RunPython(add_receipt_template_setting, reverse_code=remove_receipt_template_setting)]