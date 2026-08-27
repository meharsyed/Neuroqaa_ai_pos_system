from django.db import migrations

DEFAULTS = [
    (
        "default_receipt_template",
        "thermal",
        "Default Receipt Template",
        "Which receipt layout to pre-select when printing — match this to the printer actually set up at the till",
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

    dependencies = [("config", "0002_default_settings")]

    operations = [migrations.RunPython(seed, reverse_code=unseed)]
