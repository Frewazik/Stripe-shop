from typing import Any

from django.core.exceptions import ValidationError
from django.db import models


class Currency(models.TextChoices):
    USD = "usd", "Доллар США"
    EUR = "eur", "Евро"


class Item(models.Model):
    name = models.CharField("Название", max_length=255)
    description = models.TextField("Описание", blank=True)
    # Stripe работает с целыми числами, Decimal/Float дал бы дрейф округления при конвертации в API
    price = models.PositiveIntegerField("Цена (в минимальных единицах)")
    currency = models.CharField("Валюта", max_length=3, choices=Currency.choices)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self) -> str:
        return f"{self.name} — {self.price} {self.currency}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает оплаты"
        PAID = "paid", "Оплачен"

    created_at = models.DateTimeField("Создан", auto_now_add=True)
    currency = models.CharField("Валюта", max_length=3, choices=Currency.choices)
    status = models.CharField(
        "Статус", max_length=8, choices=Status.choices, default=Status.PENDING
    )
    paid_at = models.DateTimeField("Оплачен", null=True, blank=True)
    stripe_payment_intent_id = models.CharField(
        "Stripe PaymentIntent ID", max_length=255, blank=True, db_index=True
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    def __str__(self) -> str:
        return f"Order #{self.pk} ({self.currency})"

    def get_total_amount(self) -> int:
        subtotal = sum((line.subtotal for line in self.items.all()), 0)
        discount_total = sum((d.amount_for(subtotal) for d in self.discounts.all()), 0)
        # Налог считается с базы уже за вычетом скидок
        taxable = max(subtotal - discount_total, 0)
        tax_total = sum((t.amount_for(taxable) for t in self.taxes.all()), 0)
        return taxable + tax_total


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, verbose_name="Заказ", related_name="items", on_delete=models.CASCADE
    )
    item = models.ForeignKey(
        Item, verbose_name="Товар", related_name="+", on_delete=models.PROTECT
    )
    unit_price = models.PositiveIntegerField("Цена за единицу")
    quantity = models.PositiveIntegerField("Количество", default=1)

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self) -> str:
        return f"{self.item_id} x{self.quantity} @ {self.unit_price}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Прогоняем clean() и на программных сохранениях, не только в формах админки
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        # Смешение валют в одном заказе сложило бы центы разных валют в как попало
        if self.order_id and self.item_id and self.item.currency != self.order.currency:
            raise ValidationError(
                f"Валюта товара ({self.item.currency.upper()}) не совпадает "
                f"с валютой заказа ({self.order.currency.upper()})."
            )

    @property
    def subtotal(self) -> int:
        return self.unit_price * self.quantity
