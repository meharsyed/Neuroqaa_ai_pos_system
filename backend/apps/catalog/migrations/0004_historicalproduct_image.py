from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_product_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalproduct",
            name="image",
            field=models.TextField(blank=True, null=True),
        ),
    ]