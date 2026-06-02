from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tenant_id", models.IntegerField(db_index=True, default=1)),
                ("name", models.CharField(blank=True, max_length=200)),
                ("phone", models.CharField(blank=True, max_length=20, null=True, unique=True)),
                ("gender", models.CharField(
                    choices=[("M", "Male"), ("F", "Female"), ("O", "Other / Unspecified")],
                    default="O", max_length=1,
                )),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]