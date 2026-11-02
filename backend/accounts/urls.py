from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf/", views.csrf, name="auth-csrf"),
]
