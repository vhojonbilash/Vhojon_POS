# orders/urls.py
from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    # Product search (AJAX)
    path("products/search/", views.product_search, name="product_search"),

    # Create POS Order page (if you use it)
    path("pos/", views.create_pos_order, name="create_pos_order"),

    # Orders
    path("", views.order_list, name="order_list"),
    path("create/", views.order_create, name="order_create"),
    path("<int:pk>/", views.order_detail, name="order_detail"),
    path("<int:pk>/update/", views.order_update, name="order_update"),
    path("<int:pk>/delete/", views.order_delete, name="order_delete"),

    # ✅ Print options page
    path("<int:pk>/print/", views.order_print_options, name="order_print_options"),

    # ✅ Print endpoints (AJAX)
    path("<int:pk>/print/chef/", views.order_print_chef, name="order_print_chef"),
    path("<int:pk>/print/customer/", views.order_print_customer, name="order_print_customer"),
]
