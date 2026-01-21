from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [

    # =============================
    # AJAX
    # =============================
    path(
        "ajax/product-price/",
        views.product_price,
        name="product_price"
    ),

    # =============================
    # PRODUCTS
    # =============================
    path(
        "",
        views.product_list,
        name="product_list"
    ),
    path(
        "create/",
        views.product_create,
        name="product_create"
    ),
    path(
        "<int:pk>/edit/",
        views.product_update,
        name="product_update"
    ),
    path(
        "<int:pk>/delete/",
        views.product_delete,
        name="product_delete"
    ),

    # =============================
    # CATEGORIES (Taxonomy)
    # =============================
    path(
        "categories/",
        views.category_list,
        name="category_list"
    ),
    path(
        "categories/create/",
        views.category_create,
        name="category_create"
    ),
    path(
        "categories/<int:pk>/edit/",
        views.category_update,
        name="category_update"
    ),
    path(
        "categories/<int:pk>/delete/",
        views.category_delete,
        name="category_delete"
    ),
]
