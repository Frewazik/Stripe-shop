from django.urls import path

from apps.billing import views

app_name = "billing"

# ТЗ-примеры дергают URL без слэша (curl .../item/1), а APPEND_SLASH дал бы 301
# Поэтому каждый базовый маршрут регистрировал дважды: именованный вариант со слэшем
# (его и отдаёт reverse()/{% url %}) плюс безымянный дубль без слэша, только чтобы
# входящий запрос без слэша матчился напрямую, без редиректа
urlpatterns = [
    path("", views.index, name="index"),
    # Checkout Session - базовый сценарий ТЗ (redirectToCheckout, coupon/tax_rate)
    path("item/<int:pk>/", views.item_page, name="item_page"),
    path("item/<int:pk>", views.item_page),
    path("buy/<int:pk>/", views.buy_item, name="buy_item"),
    path("buy/<int:pk>", views.buy_item),
    path("order/<int:pk>/", views.order_page, name="order_page"),
    path("order/<int:pk>", views.order_page),
    path("order/<int:pk>/buy/", views.buy_order, name="buy_order"),
    path("order/<int:pk>/buy", views.buy_order),
    # Payment Intent - бонус, отдельный маршрут (тоже в двух вариантах слэша)
    path("pi/item/<int:pk>/", views.pi_item_page, name="pi_item_page"),
    path("pi/item/<int:pk>", views.pi_item_page),
    path("pi/buy/<int:pk>/", views.pi_buy_item, name="pi_buy_item"),
    path("pi/buy/<int:pk>", views.pi_buy_item),
    path("pi/order/<int:pk>/", views.pi_order_page, name="pi_order_page"),
    path("pi/order/<int:pk>", views.pi_order_page),
    path("pi/order/<int:pk>/buy/", views.pi_buy_order, name="pi_buy_order"),
    path("pi/order/<int:pk>/buy", views.pi_buy_order),
    path("return/", views.payment_return, name="payment_return"),
    path("webhook/<str:currency>/", views.stripe_webhook, name="stripe_webhook"),
]
