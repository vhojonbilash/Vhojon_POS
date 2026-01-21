from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.admin_login, name="login"),
    path("logout/", views.admin_logout, name="logout"),
    path("", views.home, name="home"),
    path("clock/", views.server_clock, name="server_clock"),
]
