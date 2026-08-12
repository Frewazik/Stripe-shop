from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.billing.models import Discount, Tax


@admin.register(Discount)
class DiscountAdmin(ModelAdmin):
    list_display = ("name", "kind", "value", "order")
    list_filter = ("kind",)
    autocomplete_fields = ("order",)


@admin.register(Tax)
class TaxAdmin(ModelAdmin):
    list_display = ("name", "rate_bps", "order")
    autocomplete_fields = ("order",)
