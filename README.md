# Stripe Shop

Небольшой магазин на Django с оплатой через Stripe. В основе  тестовое задание
(страница товара с кнопкой Buy и оплата через Stripe), поверх которого закрыты все
бонусы: Docker, переменные окружения, админка, модели `Order`/`Discount`/`Tax`,
мультивалютность и отдельный вариант оплаты через Payment Intent.

Базовый сценарий сделан на Stripe **Checkout Session** с `redirectToCheckout` (как в
задании), а Payment Intent вынесен отдельным флоу на `/pi/...`.

## Демо

- Сайт: [stripe-shop-1cjw.onrender.com](https://stripe-shop-1cjw.onrender.com/admin/auth/user/)
- Админка: [stripe-shop-1cjw.onrender.com/admin/](https://stripe-shop-1cjw.onrender.com/admin/auth/user/)
- Логин: `admin`
- Пароль: `123789`

Оплата проходит тестовой картой Stripe: `4242 4242 4242 4242`, срок - любой будущий
(например `12/34`), CVC - любые три цифры.

На главной странице лежит каталог. У заказа `#1` уже настроены скидка и налог, удобно
посмотреть, как они попадают в форму Stripe отдельными строками.

Инстанс на бесплатном тарифе Render: после простоя первый запрос может открываться
30–50 секунд, пока сервис просыпается .

## Что под капотом

- Django 5.1, PostgreSQL 17
- Stripe: Checkout Session (основной флоу) + Payment Intent (бонус)
- `pydantic-settings` для конфигурации, `django-unfold` для админки
- Docker + docker-compose, gunicorn, WhiteNoise для статики
- `uv` для зависимостей, `ruff` и `mypy` (strict) для качества

## Запуск локально

Проще всего через Docker поднимает и приложение, и PostgreSQL:

```bash
cp .env.example .env   # вписать свои ключи Stripe
docker compose up --build
```

Миграции, сбор статики и демо-данные создаются автоматически при старте
(см. `entrypoint.sh`). Готово на http://localhost:8000.

Без Docker (нужен свой PostgreSQL):

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

## Переменные окружения

Полный список  в `.env.example`. Главное:

- `DATABASE_URL` - строка подключения к PostgreSQL.
- `STRIPE_KEYS`, `STRIPE_PUB_KEYS`, `STRIPE_WEBHOOK_SECRETS` - словари вида
  `{"usd": "..."}`, то есть «код валюты → ключ». Так сделана мультивалютность: под
  разные валюты можно подложить разные пары ключей Stripe.
- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` - для боевого домена.

## Эндпоинты

- `GET /item/{id}` - страница товара с кнопкой Buy.
- `GET /buy/{id}` - создаёт Checkout Session и отдаёт её id для `redirectToCheckout`.
- `GET /order/{id}`, `GET /order/{id}/buy` - то же для заказа из нескольких товаров,
  со скидкой и налогом.
- `/pi/...` - те же сценарии, но на Payment Intent + Stripe Elements.
- `POST /webhook/{currency}` - вебхук Stripe, подтверждает оплату.
- `/admin/` - админка.

Все базовые маршруты работают и со слэшем, и без (`/item/1` = `/item/1/`).

## Вебхук

Статус заказа «Оплачен» ставит только вебхук, а не редирект после оплаты, потому что
пользователь может закрыть вкладку раньше. Локально события удобно пробрасывать через
Stripe CLI:

```bash
stripe listen --forward-to localhost:8000/webhook/usd/
```

Выданный `whsec_...` кладётся в `STRIPE_WEBHOOK_SECRETS`.

## Что стоит пояснить по коду

Деньги везде хранятся целым числом в минимальных единицах (центах)  так же, как их
принимает Stripe, без `Decimal`/`Float` для сумм. Ставки скидок и налогов  в basis
points; промежуточные проценты считаются через `Decimal` с округлением half-up.

В Checkout-флоу скидка и налог уходят в Stripe нативными объектами (`Coupon` и
`TaxRate`), поэтому видны прямо в форме оплаты. В Payment-Intent-флоу итог считается
на бэкенде, и в Stripe уходит только финальная сумма.

Вебхук проверяет подпись, сверяет валюту и сумму с заказом и идемпотентен -
повторная доставка того же события не меняет ничего второй раз.
