from django.urls import path
from . import views

app_name = "staff"

urlpatterns = [
    # Staff
    path("", views.staff_list, name="staff_list"),
    path("create/", views.staff_create, name="staff_create"),
    path("<int:pk>/", views.staff_detail, name="staff_detail"),
    path("<int:pk>/edit/", views.staff_update, name="staff_update"),
    path("<int:pk>/delete/", views.staff_delete, name="staff_delete"),

    # Roles
    path("roles/", views.role_list, name="role_list"),
    path("roles/create/", views.role_create, name="role_create"),
    path("roles/<int:pk>/edit/", views.role_update, name="role_update"),
    path("roles/<int:pk>/delete/", views.role_delete, name="role_delete"),
]
