import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Discount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255, verbose_name="Название")),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("percent", "Процент"),
                            ("fixed", "Фиксированная"),
                        ],
                        max_length=8,
                        verbose_name="Тип",
                    ),
                ),
                ("value", models.PositiveIntegerField(verbose_name="Значение")),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discounts",
                        to="catalog.order",
                        verbose_name="Заказ",
                    ),
                ),
            ],
            options={
                "verbose_name": "Скидка",
                "verbose_name_plural": "Скидки",
            },
        ),
        migrations.CreateModel(
            name="Tax",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255, verbose_name="Название")),
                (
                    "rate_bps",
                    models.PositiveIntegerField(verbose_name="Ставка (basis points)"),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="taxes",
                        to="catalog.order",
                        verbose_name="Заказ",
                    ),
                ),
            ],
            options={
                "verbose_name": "Налог",
                "verbose_name_plural": "Налоги",
            },
        ),
    ]
