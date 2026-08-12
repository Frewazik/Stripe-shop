import logging
from dataclasses import dataclass
from typing import cast

import stripe
from django.db import models, transaction
from django.utils import timezone

from apps.billing.models import Discount, Tax
from apps.catalog.models import Item, Order
from core.config import get_settings

logger = logging.getLogger(__name__)

# Минимум транзакции Stripe в минимальных единицах.
STRIPE_MIN_AMOUNT = 50


class PaymentIntentError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PaymentIntentDTO:
    id: str
    client_secret: str
    publishable_key: str
    amount: int
    currency: str


class StripeGateway:
    """Единственная граница со Stripe. Модели не знают про сеть; маршрутизация
    ключей по валюте делегирована Settings, поэтому `if currency ==` здесь нет."""

    def __init__(self) -> None:
        self._settings = get_settings()

    # Payment Intent (бонус, отдельный маршрут /pi/...).

    def _create(
        self, *, amount: int, currency: str, metadata: dict[str, str]
    ) -> PaymentIntentDTO:
        if amount < STRIPE_MIN_AMOUNT:
            raise PaymentIntentError("Сумма ниже минимального лимита Stripe.")
        secret = self._settings.stripe_secret_for(currency)
        try:
            intent = stripe.PaymentIntent.create(
                api_key=secret,
                amount=amount,
                currency=currency,
                metadata=metadata,
                automatic_payment_methods={"enabled": True},
            )
        except stripe.StripeError as exc:
            raise PaymentIntentError(str(exc)) from exc
        client_secret = intent.client_secret
        if client_secret is None:
            raise PaymentIntentError(f"Stripe не вернул client_secret для {intent.id}")
        return PaymentIntentDTO(
            id=intent.id,
            client_secret=client_secret,
            publishable_key=self._settings.stripe_pub_for(currency),
            amount=amount,
            currency=currency,
        )

    def create_for_item(self, item: Item) -> PaymentIntentDTO:
        return self._create(
            amount=item.price,
            currency=item.currency,
            metadata={"item_id": str(item.pk)},
        )

    def create_for_order(self, order: Order) -> PaymentIntentDTO:
        # В PaymentIntent уходит только итоговая сумма; вся математика Discount/Tax
        # решается на бэке в Order.get_total_amount до обращения к Stripe
        dto = self._create(
            amount=order.get_total_amount(),
            currency=order.currency,
            metadata={"order_id": str(order.pk)},
        )
        order.stripe_payment_intent_id = dto.id
        order.save(update_fields=["stripe_payment_intent_id"])
        return dto

    # базовый сценарий ТЗ: coupon/tax_rate + redirectToCheckout

    def _coupon_id(self, discount: Discount, *, currency: str, api_key: str) -> str:
        # Discount.value - basis points для PERCENT (825 = 8.25%), центы для FIXED;
        # Stripe Coupon ждёт percent_off в процентах / amount_off в центах.
        if discount.kind == Discount.Kind.PERCENT:
            coupon = stripe.Coupon.create(
                api_key=api_key,
                name=discount.name,
                percent_off=discount.value / 100,
                duration="once",
            )
        else:
            coupon = stripe.Coupon.create(
                api_key=api_key,
                name=discount.name,
                amount_off=discount.value,
                currency=currency,
                duration="once",
            )
        return coupon.id

    def _tax_rate_id(self, tax: Tax, *, api_key: str) -> str:
        rate = stripe.TaxRate.create(
            api_key=api_key,
            display_name=tax.name,
            percentage=tax.rate_bps / 100,
            inclusive=False,
        )
        return rate.id

    def create_session_for_item(
        self, item: Item, *, success_url: str, cancel_url: str
    ) -> str:
        if item.price < STRIPE_MIN_AMOUNT:
            raise PaymentIntentError("Сумма ниже минимального лимита Stripe.")
        api_key = self._settings.stripe_secret_for(item.currency)
        try:
            session = stripe.checkout.Session.create(
                api_key=api_key,
                mode="payment",
                line_items=[
                    {
                        "price_data": {
                            "currency": item.currency,
                            "unit_amount": item.price,
                            "product_data": {"name": item.name},
                        },
                        "quantity": 1,
                    }
                ],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"item_id": str(item.pk)},
            )
        except stripe.StripeError as exc:
            raise PaymentIntentError(str(exc)) from exc
        return session.id

    def create_session_for_order(
        self, order: Order, *, success_url: str, cancel_url: str
    ) -> str:
        if order.get_total_amount() < STRIPE_MIN_AMOUNT:
            raise PaymentIntentError("Сумма ниже минимального лимита Stripe.")
        api_key = self._settings.stripe_secret_for(order.currency)
        try:
            # Налоги привязаны ко всему заказу, поэтому один и тот же набор
            # TaxRate вешаем на каждую позицию.
            tax_rate_ids = [
                self._tax_rate_id(tax, api_key=api_key) for tax in order.taxes.all()
            ]
            line_items = []
            for line in order.items.select_related("item"):
                item_params: dict[str, object] = {
                    "price_data": {
                        "currency": order.currency,
                        "unit_amount": line.unit_price,
                        "product_data": {"name": line.item.name},
                    },
                    "quantity": line.quantity,
                }
                if tax_rate_ids:
                    item_params["tax_rates"] = tax_rate_ids
                line_items.append(item_params)

            # Checkout принимает не более одного купона; больше одной скидки на
            # заказ запрещает Discount.clean(). order_by, чтобы выбор был
            # детерминированным, а не какую строку вернёт планировщик
            discount = order.discounts.order_by("pk").first()
            discounts = (
                [
                    {
                        "coupon": self._coupon_id(
                            discount, currency=order.currency, api_key=api_key
                        )
                    }
                ]
                if discount is not None
                else None
            )

            # line_items/discounts - TypedDict-параметры Stripe, а мы строим их
            # динамически обычными словарями, поэтому соответствие утверждаем тут
            session = stripe.checkout.Session.create(
                api_key=api_key,
                mode="payment",
                line_items=line_items,  # type: ignore[arg-type]
                discounts=discounts,  # type: ignore[arg-type]
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"order_id": str(order.pk)},
            )
        except stripe.StripeError as exc:
            raise PaymentIntentError(str(exc)) from exc
        return session.id


class WebhookVerificationError(RuntimeError):
    pass


class PaymentProcessor:
    """Обрабатывает проверенные события Stripe. Валидация подписи остаётся во вью;
    этот класс владеет переходами статусов и не ходит в сеть."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def construct_event(
        self, *, payload: bytes, sig_header: str, currency: str
    ) -> stripe.Event:
        secret = self._settings.stripe_webhook_secret_for(currency)
        try:
            return cast(
                stripe.Event,
                stripe.Webhook.construct_event(payload, sig_header, secret),
            )
        except (ValueError, stripe.SignatureVerificationError) as exc:
            raise WebhookVerificationError(str(exc)) from exc

    def handle_event(self, event: stripe.Event) -> None:
        # Доступ к полям только через `[]`: у StripeObject точечный .get резолвится
        # как поле API, а не метод словаря, и падает
        obj = event.data.object
        if event.type == "checkout.session.completed":
            if obj["payment_status"] != "paid":
                return  # отложенные методы: completed приходит со статусом unpaid
            self._settle(
                obj["metadata"], str(obj["currency"]), int(obj["amount_total"])
            )
        elif event.type == "payment_intent.succeeded":
            # Симметрично сессии: сумму тоже сверяем, а заказ ищем по metadata,
            # а не по stripe_payment_intent_id, который перезаписывается на каждом
            # клике /pi/order/{id}/buy (иначе оплата старого интента не нашла бы заказ)
            self._settle(
                obj["metadata"], str(obj["currency"]), int(obj["amount_received"])
            )

    def _settle(self, metadata: dict[str, str], currency: str, amount: int) -> None:
        if "order_id" not in metadata:
            return  
        order = Order.objects.filter(pk=int(metadata["order_id"])).first()
        if order is None:
            return
        # Подпись доказывает отправителя, но не валюту/сумму -сверяем сами
        if currency != order.currency:
            logger.warning(
                "webhook: валюта не совпала order=%s stripe=%s", order.pk, currency
            )
            return
        expected = order.get_total_amount()
        if abs(amount - expected) > order.items.count():
            logger.warning(
                "webhook: сумма не совпала order=%s stripe=%s ожидали=%s",
                order.pk,
                amount,
                expected,
            )
            return
        self._mark_order_paid_by_id(order.pk)

    @transaction.atomic
    def _mark_order_paid_by_id(self, order_id: int) -> None:
        self._transition(Order.objects.filter(pk=order_id))

    @staticmethod
    def _transition(queryset: "models.QuerySet[Order]") -> None:
        # Идемпотентность by design: повторная доставка обновит 0 строк, т.к.
        # уже оплаченные заказы исключены фильтром.
        queryset.exclude(status=Order.Status.PAID).update(
            status=Order.Status.PAID, paid_at=timezone.now()
        )
