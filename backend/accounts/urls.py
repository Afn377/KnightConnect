from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf/", views.csrf, name="auth-csrf"),
    path("auth/request-code/", views.RequestCodeView.as_view(), name="auth-request-code"),
]
