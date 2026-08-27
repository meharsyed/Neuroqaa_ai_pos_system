from django.db import migrations


def add_language_setting(apps, schema_editor):
    Setting = apps.get_model("config", "Setting")
    Setting.objects.get_or_create(
        key="language_preference",
        defaults={
            "value": "en",
            "label": "Language Preference",
            "description": "Default language for the POS interface: 'en' for English, 'ur' for Urdu",
        },
    )


def remove_language_setting(apps, schema_editor):
    Setting = apps.get_model("config", "Setting")
    Setting.objects.filter(key="language_preference").delete()


class Migration(migrations.Migration):

    dependencies = [("config", "0002_default_settings")]

    operations = [migrations.RunPython(add_language_setting, reverse_code=remove_language_setting)]