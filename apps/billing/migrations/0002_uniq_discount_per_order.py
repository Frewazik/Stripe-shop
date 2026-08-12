from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="discount",
            constraint=models.UniqueConstraint(
                fields=["order"], name="uniq_discount_per_order"
            ),
        ),
    ]
