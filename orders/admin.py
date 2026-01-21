# orders/admin.py

from django.contrib import admin
from .models import Order, OrderItem, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ["product"]
    readonly_fields = ("line_total",)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("paid_at",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_no",
        "customer",
        "source",
        "status",
        "grand_total",
        "paid_total",
        "due_total",
        "payment_status",
        "ordered_at",
    )
    list_filter = ("status", "source", "ordered_at")
    search_fields = ("order_no", "customer__name", "customer__phone")
    date_hierarchy = "ordered_at"
    inlines = [OrderItemInline, PaymentInline]

    readonly_fields = (
        "subtotal",
        "discount_amount",
        "grand_total",
        "paid_total",
        "due_total",
        "ordered_at",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Order Info", {
            "fields": ("order_no", "customer", "customer_address", "source", "status", "ordered_at")
        }),
        ("Pricing", {
            "fields": (
                "subtotal",
                "discount_type",
                "discount_value",
                "discount_amount",
                "tax_amount",
                "grand_total",
            )
        }),
        ("Payment Summary", {
            "fields": ("paid_total", "due_total")
        }),
        ("Notes", {
            "fields": ("notes",)
        }),
        ("System", {
            "fields": ("created_at", "updated_at")
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        Ensure totals are always recalculated if admin edits order.
        """
        super().save_model(request, obj, form, change)
        obj.recalc_totals()


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "qty", "unit_price", "line_total")
    search_fields = ("order__order_no", "product__name")
    autocomplete_fields = ["order", "product"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "payment_method", "amount", "paid_at")
    list_filter = ("payment_method",)
    search_fields = ("order__order_no", "payment_method__name")
    autocomplete_fields = ["order", "payment_method"]
