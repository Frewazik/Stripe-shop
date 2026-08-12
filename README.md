# Stripe Shop (Django + Stripe Checkout Session)

Django-бэкенд с интеграцией Stripe. Базовый флоу — **Checkout Session** с нативными
`coupon`/`tax_rate` и `redirectToCheckout`; **Payment Intent + Elements** реализован
как бонус на отдельном маршруте `/pi/...`. Плюс мультивалютный роутинг ключей,
доменные модели `Order`/`Discount`/`Tax`, идемпотентные вебхуки с проверкой суммы и
админка на Django Unfold.

## Демо

- Боевая ссылка: `https://<заполнить-после-деплоя>`
- Админка: `https://<заполнить-после-деплоя>/admin/`
- Тестовый логин/пароль админки: `<заполнить>` / `<заполнить>`
- Тестовая карта: `4242 4242 4242 4242`, любой будущий срок, любой CVC.

## Стек

- Django 5.1, PostgreSQL 17
- `pydantic-settings` — валидация конфигурации из окружения
- `uv` — управление зависимостями, Ruff + Mypy (strict) — качество кода
- Docker / docker-compose, gunicorn + WhiteNoise
- Django Unfold — админка

## Эндпоинты

Checkout Session — базовый сценарий ТЗ:

- `GET /item/{id}` — HTML-страница с товаром и кнопкой **Buy**.
- `GET /buy/{id}` — создаёт Stripe **Checkout Session** и возвращает `{"id": "cs_..."}`;
  фронт делает `stripe.redirectToCheckout({ sessionId })`.
- `GET /order/{id}` / `GET /order/{id}/buy` — то же для `Order`: `line_items` из позиций,
  `Discount` → Stripe **Coupon** (`discounts`), `Tax` → Stripe **TaxRate** (`line_items[].tax_rates`),
  скидки и налоги отображаются нативно в форме Checkout.

Payment Intent — бонусный флоу (отдельный маршрут):

- `GET /pi/item/{id}/` — HTML со Stripe Elements.
- `GET /pi/buy/{id}/` — возвращает `{"client_secret": "..."}`.
- `GET /pi/order/{id}/` / `GET /pi/order/{id}/buy/` — то же для `Order`; итог считается
  на бэке (`Order.get_total_amount()`) и в PI уходит только `amount`.

Прочее:

- `POST /webhook/{currency}/` — вебхук Stripe. Проверяет подпись, а для
  `checkout.session.completed` дополнительно сверяет `payment_status == paid`,
  `currency` и `amount_total` с заказом (подпись доказывает отправителя, но не сумму).
  Единственный источник истины для статуса «оплачен», идемпотентен к повтору.
- `admin/` — админка Django Unfold.

Базовые маршруты доступны и со слэшем, и без — включая `/pi/...`.

## Архитектурные решения

- **Деньги хранятся в целых копейках/центах (minor units).** Ставки
  (`Tax.rate_bps`, процентный `Discount`) — в basis points; промежуточная
  математика ставок идёт через `Decimal` с `ROUND_HALF_UP` и возвращает строгий `int`.
- **Два платёжных флоу.** Checkout Session (базовый) отдаёт `Discount`/`Tax` в Stripe
  нативными `coupon`/`tax_rate`, создаваемыми на лету. Payment Intent (бонус) считает
  скидки/налоги на бэке и передаёт только итоговый `amount`.
- **Одна скидка на заказ.** Stripe Checkout принимает максимум один купон, поэтому
  вторую скидку на `Order` блокирует `Discount.clean()` — иначе `get_total_amount`
  учёл бы обе, а в Stripe ушла бы одна, и покупатель заплатил бы больше показанного.
- **Одиночный `Item` через Session — прямой платёж без `Order`** (как в базовом ТЗ):
  строки заказа не создаётся, в БД он не фиксируется. Чтобы платёж был привязан к
  заказу и подтверждался вебхуком, оформляйте его через `Order`.
- **Мультивалютность:** `STRIPE_KEYS` / `STRIPE_PUB_KEYS` / `STRIPE_WEBHOOK_SECRETS`
  маппят код валюты на токен. Роутинг живёт в `Settings`; в бизнес-логике нет
  `if currency ==`. Валидатор при старте требует паритета валют во всех трёх словарях.
- **`OrderItem.unit_price`** замораживается при добавлении, чтобы правка цены `Item`
  не переписывала старые чеки.

## Конфигурация

Создайте `.env` в корне проекта (шаблон — `.env.example`):

```dotenv
SECRET_KEY=change-me
DEBUG=false
DATABASE_URL=postgresql://shop:shop@db:5432/shop
ALLOWED_HOSTS=["localhost","127.0.0.1"]
CSRF_TRUSTED_ORIGINS=[]
STRIPE_KEYS={"usd":"sk_test_usd","eur":"sk_test_eur"}
STRIPE_PUB_KEYS={"usd":"pk_test_usd","eur":"pk_test_eur"}
STRIPE_WEBHOOK_SECRETS={"usd":"whsec_usd","eur":"whsec_eur"}
```

Словарные и списочные поля парсятся как JSON. Две пары ключей Stripe (по одной на
валюту) закрывают бонус про мультивалютность. На боевом домене обязательно задайте
`ALLOWED_HOSTS=["ваш-домен"]` и `CSRF_TRUSTED_ORIGINS=["https://ваш-домен"]` — иначе
`DisallowedHost` и 403 CSRF на форме входа в админку. При `DEBUG=false` включается
`SECURE_PROXY_SSL_HEADER`, чтобы за HTTPS-прокси `success_url` собирался с `https://`.

## Запуск через Docker

```bash
docker compose up --build
```

`entrypoint.sh` выполняет `migrate` и `collectstatic`, затем стартует gunicorn.
После подъёма стека создайте администратора:

```bash
docker compose exec web python manage.py createsuperuser
```

Откройте `http://localhost:8000/admin/`, добавьте `Item`, затем перейдите на
`http://localhost:8000/item/1/`.

## Локальный запуск (без Docker)

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

## Тестирование оплаты

Тестовые карты Stripe (например `4242 4242 4242 4242`, любой будущий срок и CVC).

Форвард вебхуков локально через Stripe CLI:

```bash
stripe listen --forward-to localhost:8000/webhook/usd/
```

Выведенный `whsec_...` подставьте в `STRIPE_WEBHOOK_SECRETS` для нужной валюты.

## Качество кода

```bash
uv run ruff check .
uv run mypy .
```

## Структура проекта

```
.
├── apps
│   ├── billing
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── migrations/
│   │   ├── models.py          # Discount, Tax
│   │   ├── services.py        # StripeGateway, PaymentProcessor
│   │   ├── templates/billing/ # index, session, purchase, return .html
│   │   ├── urls.py
│   │   └── views.py
│   └── catalog
│       ├── admin.py
│       ├── apps.py
│       ├── migrations/
│       └── models.py          # Item, Order, OrderItem
├── core
│   ├── config.py              # pydantic-settings, роутер ключей
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── manage.py
├── pyproject.toml
├── .env.example
└── README.md
```
