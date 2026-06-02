import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0001_initial"),
        ("sales", "0002_shift_closing_fields"),
    ]
    operations = [
        migrations.AddField(
            model_name="sale",
            name="customer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sales",
                to="customers.customer",
            ),
        ),
    ]