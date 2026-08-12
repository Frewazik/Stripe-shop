from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models


class Discount(models.Model):
    class Kind(models.TextChoices):
        PERCENT = "percent", "Процент"
        FIXED = "fixed", "Фиксированная"

    order = models.ForeignKey(
        "catalog.Order",
        verbose_name="Заказ",
        related_name="discounts",
        on_delete=models.CASCADE,
    )
    name = models.CharField("Название", max_length=255)
    kind = models.CharField("Тип", max_length=8, choices=Kind.choices)
    value = models.PositiveIntegerField("Значение")

    class Meta:
        verbose_name = "Скидка"
        verbose_name_plural = "Скидки"
        constraints = [
            models.UniqueConstraint(fields=["order"], name="uniq_discount_per_order")
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.kind}:{self.value})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        # сообщение в админке до удара в БД
        # get_total_amount учёл бы обе скидки, а в Stripe ушла бы одна
        # покупатель заплатил бы больше показанного.
        if self.order_id:
            clash = Discount.objects.filter(order_id=self.order_id).exclude(pk=self.pk)
            if clash.exists():
                raise ValidationError(
                    "К заказу можно привязать только одну скидку "
                    "(ограничение Stripe Checkout)."
                )

    def amount_for(self, base: int) -> int:
        if self.kind == self.Kind.FIXED:
            return min(self.value, base)
        # Ставка через Decimal + ROUND_HALF_UP: floor-деление
        # систематически срезало бы копейки на каждом заказе
        calculated = (Decimal(base) * Decimal(self.value) / Decimal("10000")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        return int(calculated)


class Tax(models.Model):
    order = models.ForeignKey(
        "catalog.Order",
        verbose_name="Заказ",
        related_name="taxes",
        on_delete=models.CASCADE,
    )
    name = models.CharField("Название", max_length=255)
    # Basis points держат ставку целой (825 = 8.25%), деньги только в целых
    rate_bps = models.PositiveIntegerField("Ставка (basis points)")

    class Meta:
        verbose_name = "Налог"
        verbose_name_plural = "Налоги"

    def __str__(self) -> str:
        return f"{self.name} ({self.rate_bps}bps)"

    def amount_for(self, base: int) -> int:
        calculated = (
            Decimal(base) * Decimal(self.rate_bps) / Decimal("10000")
        ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return int(calculated)
