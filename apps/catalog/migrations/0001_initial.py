import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Item",
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
                ("description", models.TextField(blank=True, verbose_name="Описание")),
                (
                    "price",
                    models.PositiveIntegerField(
                        verbose_name="Цена (в минимальных единицах)"
                    ),
                ),
                (
                    "currency",
                    models.CharField(
                        choices=[("usd", "Доллар США"), ("eur", "Евро")],
                        max_length=3,
                        verbose_name="Валюта",
                    ),
                ),
            ],
            options={
                "verbose_name": "Товар",
                "verbose_name_plural": "Товары",
            },
        ),
        migrations.CreateModel(
            name="Order",
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
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Создан"),
                ),
                (
                    "currency",
                    models.CharField(
                        choices=[("usd", "Доллар США"), ("eur", "Евро")],
                        max_length=3,
                        verbose_name="Валюта",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Ожидает оплаты"),
                            ("paid", "Оплачен"),
                        ],
                        default="pending",
                        max_length=8,
                        verbose_name="Статус",
                    ),
                ),
                (
                    "paid_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Оплачен"
                    ),
                ),
                (
                    "stripe_payment_intent_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        max_length=255,
                        verbose_name="Stripe PaymentIntent ID",
                    ),
                ),
            ],
            options={
                "verbose_name": "Заказ",
                "verbose_name_plural": "Заказы",
            },
        ),
        migrations.CreateModel(
            name="OrderItem",
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
                (
                    "unit_price",
                    models.PositiveIntegerField(verbose_name="Цена за единицу"),
                ),
                (
                    "quantity",
                    models.PositiveIntegerField(default=1, verbose_name="Количество"),
                ),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="catalog.item",
                        verbose_name="Товар",
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="catalog.order",
                        verbose_name="Заказ",
                    ),
                ),
            ],
            options={
                "verbose_name": "Позиция заказа",
                "verbose_name_plural": "Позиции заказа",
            },
        ),
    ]
