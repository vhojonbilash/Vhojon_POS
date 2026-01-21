# customers/admin.py
from django.contrib import admin
from .models import Customer, CustomerAddress


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "created_at")
    search_fields = ("name", "phone")
    ordering = ("-created_at",)


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "is_primary", "created_at")
    search_fields = ("customer__name", "customer__phone", "address_line")
    list_filter = ("is_primary",)
    ordering = ("-created_at",)
