from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.billing.services import (
    PaymentIntentError,
    PaymentProcessor,
    StripeGateway,
    WebhookVerificationError,
)
from apps.catalog.models import Item, Order
from core.config import get_settings


@require_GET
def index(request: HttpRequest) -> HttpResponse:
    items = Item.objects.order_by("pk")
    return render(request, "billing/index.html", {"items": items})


def _abs(request: HttpRequest, name: str, *args: int) -> str:
    return request.build_absolute_uri(reverse(name, args=args))


def _success_url(request: HttpRequest) -> str:
    base = _abs(request, "billing:payment_return")
    return base + "?session_id={CHECKOUT_SESSION_ID}"


def _session_page(
    request: HttpRequest, *, title: str, currency: str, amount: int, buy_url: str
) -> HttpResponse:
    return render(
        request,
        "billing/session.html",
        {
            "title": title,
            "amount": amount,
            "currency": currency.upper(),
            "publishable_key": get_settings().stripe_pub_for(currency),
            "buy_url": buy_url,
        },
    )


@require_GET
def item_page(request: HttpRequest, pk: int) -> HttpResponse:
    item = get_object_or_404(Item, pk=pk)
    return _session_page(
        request,
        title=item.name,
        currency=item.currency,
        amount=item.price,
        buy_url=reverse("billing:buy_item", args=[item.pk]),
    )


@require_GET
def buy_item(request: HttpRequest, pk: int) -> JsonResponse:
    item = get_object_or_404(Item, pk=pk)
    cancel = _abs(request, "billing:item_page", item.pk)
    try:
        session_id = StripeGateway().create_session_for_item(
            item, success_url=_success_url(request), cancel_url=cancel
        )
    except PaymentIntentError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"id": session_id})


@require_GET
def order_page(request: HttpRequest, pk: int) -> HttpResponse:
    order = get_object_or_404(Order, pk=pk)
    return _session_page(
        request,
        title=f"Order #{order.pk}",
        currency=order.currency,
        amount=order.get_total_amount(),
        buy_url=reverse("billing:buy_order", args=[order.pk]),
    )


@require_GET
def buy_order(request: HttpRequest, pk: int) -> JsonResponse:
    order = get_object_or_404(Order, pk=pk)
    cancel = _abs(request, "billing:order_page", order.pk)
    try:
        session_id = StripeGateway().create_session_for_order(
            order, success_url=_success_url(request), cancel_url=cancel
        )
    except PaymentIntentError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"id": session_id})


# Payment Intent (бонус, отдельный маршрут /pi/...)

def _pi_page(
    request: HttpRequest, *, title: str, currency: str, amount: int, buy_url: str
) -> HttpResponse:
    # Страница только рендерит форму; сам PaymentIntent создаётся уже по кнопке
    # (fetch на buy_url), поэтому здесь нет ни похода в Stripe, ни второго интента
    return render(
        request,
        "billing/purchase.html",
        {
            "title": title,
            "amount": amount,
            "currency": currency.upper(),
            "publishable_key": get_settings().stripe_pub_for(currency),
            "buy_url": buy_url,
            "return_url": _abs(request, "billing:payment_return"),
        },
    )


@require_GET
def pi_item_page(request: HttpRequest, pk: int) -> HttpResponse:
    item = get_object_or_404(Item, pk=pk)
    return _pi_page(
        request,
        title=item.name,
        currency=item.currency,
        amount=item.price,
        buy_url=reverse("billing:pi_buy_item", args=[item.pk]),
    )


@require_GET
def pi_buy_item(request: HttpRequest, pk: int) -> JsonResponse:
    item = get_object_or_404(Item, pk=pk)
    try:
        intent = StripeGateway().create_for_item(item)
    except PaymentIntentError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"client_secret": intent.client_secret})


@require_GET
def pi_order_page(request: HttpRequest, pk: int) -> HttpResponse:
    order = get_object_or_404(Order, pk=pk)
    return _pi_page(
        request,
        title=f"Order #{order.pk}",
        currency=order.currency,
        amount=order.get_total_amount(),
        buy_url=reverse("billing:pi_buy_order", args=[order.pk]),
    )


@require_GET
def pi_buy_order(request: HttpRequest, pk: int) -> JsonResponse:
    order = get_object_or_404(Order, pk=pk)
    try:
        intent = StripeGateway().create_for_order(order)
    except PaymentIntentError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"client_secret": intent.client_secret})


def payment_return(request: HttpRequest) -> HttpResponse:
    # Только UI: страница НЕ трогает БД. Пользователь может закрыть вкладку до
    # редиректа, поэтому источник истины по оплате только вебхук
    return render(request, "billing/return.html")


@csrf_exempt
@require_POST
def stripe_webhook(request: HttpRequest, currency: str) -> HttpResponse:
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    processor = PaymentProcessor()
    try:
        # construct_event нужен сырой bytes-body; разобранный доступ сломал бы подпись
        event = processor.construct_event(
            payload=request.body, sig_header=sig_header, currency=currency
        )
    except WebhookVerificationError:
        return HttpResponseBadRequest("invalid signature")

    processor.handle_event(event)
    return HttpResponse(status=200)
