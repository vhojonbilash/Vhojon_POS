# customers/urls.py
from django.urls import path
from . import views

app_name = "customers"

urlpatterns = [
    # CRUD pages
    path("", views.customer_list, name="customer_list"),
    path("<int:pk>/", views.customer_detail, name="customer_detail"),
    path("<int:pk>/edit/", views.customer_update, name="customer_update"),
    path("<int:pk>/delete/", views.customer_delete, name="customer_delete"),

    # AJAX
    path("ajax/phone-suggest/", views.phone_suggest, name="phone_suggest"),
    path("ajax/customer-by-phone/", views.customer_by_phone, name="customer_by_phone"),
]
