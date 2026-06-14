import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0003_sale_customer"),
    ]
    operations = [
        migrations.AddField(
            model_name="sale",
            name="sale_type",
            field=models.CharField(
                choices=[("sale", "Sale"), ("return", "Return")],
                default="sale",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="return_of",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="returns",
                to="sales.sale",
            ),
        ),
    ]