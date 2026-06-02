from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("sales", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="shift",
            name="closing_cash_paise",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="shift",
            name="closing_notes",
            field=models.TextField(blank=True),
        ),
    ]