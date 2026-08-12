from typing import Any

from django.core.management.base import BaseCommand

from apps.billing.models import Discount, Tax
from apps.catalog.models import Currency, Item, Order, OrderItem


class Command(BaseCommand):
    help = "Создаёт демо-данные (товары, заказ со скидкой и налогом). Идемпотентно"

    def handle(self, *args: Any, **options: Any) -> None:
        catalog = [
            ("Кофе", "Пачка зернового кофе.", 1000),
            ("Книга", "Лысая книга.", 2500),
            ("Игрушка", "Бронеровання юла.", 5000),
        ]
        items: dict[str, Item] = {}
        for name, description, price in catalog:
            item, _ = Item.objects.get_or_create(
                name=name,
                defaults={
                    "description": description,
                    "price": price,
                    "currency": Currency.USD,
                },
            )
            items[name] = item

        # Заказ создаём один раз: сид гоняется на каждом деплое
        if not Order.objects.exists():
            order = Order.objects.create(currency=Currency.USD)
            OrderItem.objects.create(
                order=order, item=items["Кофе"], unit_price=items["Кофе"].price, quantity=2
            )
            OrderItem.objects.create(
                order=order,
                item=items["Книга"],
                unit_price=items["Книга"].price,
                quantity=1,
            )
            Discount.objects.create(
                order=order, name="Промо 10%", kind=Discount.Kind.PERCENT, value=1000
            )
            Tax.objects.create(order=order, name="НДС 20%", rate_bps=2000)
            self.stdout.write(f"seed_demo: заказ #{order.pk} создан")

        self.stdout.write("seed_demo: ok")
