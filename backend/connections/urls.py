from django.urls import path

from . import views

urlpatterns = [
    path("requests/", views.ConnectionRequestListView.as_view(), name="request-list"),
]
