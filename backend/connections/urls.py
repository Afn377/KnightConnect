from django.urls import path

from . import views

urlpatterns = [
    path("requests/", views.ConnectionRequestListView.as_view(), name="request-list"),
    path("requests/<uuid:pk>/", views.ConnectionRequestDetailView.as_view(), name="request-detail"),
]
