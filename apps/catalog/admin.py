from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.catalog.models import Item, Order, OrderItem


@admin.register(Item)
class ItemAdmin(ModelAdmin):
    list_display = ("name", "price", "currency")
    list_filter = ("currency",)
    search_fields = ("name",)


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ("item",)


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ("pk", "currency", "status", "created_at", "paid_at")
    list_filter = ("status", "currency")
    # Нужно, потому что в admin Discount/Tax объявлены autocomplete_fields=("order",)
    search_fields = ("stripe_payment_intent_id",)
    date_hierarchy = "created_at"
    inlines = (OrderItemInline,)
    readonly_fields = ("stripe_payment_intent_id", "paid_at", "created_at")
